import csv
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from Events.adaptiveMethods import Trials_read_write_staircase_conditions, _check_responses_history
from Events.adaptive_session import LegacyStaircaseSession
import Functions.functionsForUse as funcs


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.conditions = root / 'conditions.json'
        self.params = root / 'params.json'
        self.responses = root / '1_experiment.txt'
        funcs.create_JSON(self.conditions, {
            'condition_list': [63, 252], 'staircase_Identities': [0, 1],
            'staircase_intensity_active': [1., 1.], 'reversal_termination': [1, 2],
            'probe_Alternative_Choice': [0, 0], 'staircase_Identity_active': [0],
            'weber_contrast_active': [1., 1.], 'stimulus_choice_active': [10],
            'terminate_bool': [0], 'total_Reversals': [0, 0], '2AFC_choice': [10, 20],
        })
        funcs.create_JSON(self.params, {
            'n_dw': 1, 'n_up': 1, 'logUNIT_UP': .1, 'logUNIT_DW': .1,
            'background_intensity': .5, 'max_intensity': 1.,
        })
        funcs.create_Text_columns(self.responses, list(range(6)))
        self.session = LegacyStaircaseSession(self.conditions, self.params, self.responses, 30)
        self.window = SimpleNamespace(trials=['unused phase'] * 100, exit=lambda: None)
        self.exits = []
        self.window.exit = lambda: self.exits.append(True)
        self.log = self.session.logger(self.window)
        beep = patch('Events.adaptiveMethods._beep')
        beep.start()
        self.addCleanup(beep.stop)

    def trial(self, name):
        return self.session.attach(Trials_read_write_staircase_conditions(
            name, [], 250, [10, 0], self.conditions, self.params, self.responses,
            keys=['LEFT', 'RIGHT']))

    def respond(self, identity, correct, duplicate=False):
        with patch('random.choice', return_value=identity):
            self.log('TRIAL', 0, self.trial('new_condition'), [])
        response = self.trial('response')
        self.log('TRIAL', 0, response, [])
        key = 'LEFT' if correct else 'RIGHT'
        self.log('KEY', 0, response, [key, key])
        if duplicate:
            self.log('KEY', 0, response, [key, key])

    def test_response_recorded_once_and_legacy_columns_preserved(self):
        self.respond(0, True, duplicate=True)
        rows = funcs.readText_toList(self.responses)
        self.assertEqual(len(rows), 6)
        self.assertEqual([len(c) for c in rows], [2] * 6)  # sentinel + one response
        self.assertEqual([c[-1] for c in rows[:4]], [63, 0, 0, 0])
        self.assertAlmostEqual(rows[4][-1], 10 ** -.1)
        self.assertAlmostEqual(rows[5][-1], .5 + .5 * 10 ** -.1)
        self.assertEqual(self.session.run.total_trials, 1)

        # The canonical record explicitly separates what was shown from the
        # post-response value intended for the next presentation.
        with self.session.trial_log.path.open(newline='', encoding='utf-8') as handle:
            canonical = list(csv.DictReader(handle, delimiter='\t'))
        self.assertEqual(len(canonical), 1)
        self.assertEqual(canonical[0]['step'], 'down')
        self.assertAlmostEqual(float(canonical[0]['presented_screen_intensity']), 1.0)
        self.assertAlmostEqual(
            float(canonical[0]['next_screen_intensity']),
            .5 + .5 * 10 ** -.1,
        )
        self.assertAlmostEqual(float(canonical[0]['presented_display_contrast']), 1.0)
        self.assertAlmostEqual(float(canonical[0]['next_display_contrast']), 10 ** -.1)

    def test_success_clears_queue_and_exits_immediately(self):
        for correct in [True, False, True]:
            self.respond(0, correct)
        self.assertEqual(self.exits, [])
        self.assertEqual(self.session.run.active_ids, (1,))
        for correct in [True, False, True, False]:
            self.respond(1, correct)
        self.assertEqual(self.window.trials, [])
        self.assertEqual(self.exits, [True])
        metadata = json.loads(self.session.metadata_path.read_text())
        self.assertEqual(metadata['status'], 'completed')
        self.assertEqual(metadata['total_trials'], 7)
        state = funcs.read_JSON(self.conditions)
        self.assertEqual(state['condition_list'], [63, 252])
        self.assertEqual(state['staircase_Identities'], [0, 1])
        self.assertEqual(state['active_staircase_ids'], [])
        self.assertEqual(state['terminate_bool'], [1])
        self.assertEqual(state['total_Reversals'], [1, 2])

    def test_trial_ceiling_exits_and_records_unfinished(self):
        self.session = LegacyStaircaseSession(self.conditions, self.params, self.responses, 1)
        self.log = self.session.logger(self.window)
        self.respond(1, True)
        self.assertEqual(self.exits, [True])
        metadata = json.loads(self.session.metadata_path.read_text())
        self.assertEqual(metadata['status'], 'max_trials_reached')
        self.assertEqual(metadata['completed_staircase_ids'], [])
        self.assertEqual(metadata['staircases']['0']['trial_count'], 0)
        self.assertEqual(metadata['staircases']['1']['trial_count'], 1)

    def test_non_response_events_do_not_consume_response(self):
        response = self.trial('response')
        for event, args in [('TRIAL', []), ('KEY', ['UP', 'UP']), ('MOUSE', [1, 2])]:
            self.log(event, 0, response, args)
        self.assertEqual(self.session.run.total_trials, 0)

    def test_new_condition_keys_do_not_reselect(self):
        with patch('random.choice', return_value=0) as choose:
            trial = self.trial('new_condition')
            self.log('TRIAL', 0, trial, [])
            self.log('KEY', 0, trial, ['LEFT', 'LEFT'])
            choose.assert_called_once()

    def test_reused_response_trial_resets_on_entry_only(self):
        response = self.trial('response')
        for _ in range(2):
            self.log('TRIAL', 0, response, [])
            self.log('KEY', 0, response, ['LEFT', 'LEFT'])
            self.log('KEY', 0, response, ['LEFT', 'LEFT'])
        self.assertEqual(self.session.run.total_trials, 2)

    def test_aborted_run_not_reported_as_completed(self):
        self.session.finish()
        self.assertEqual(json.loads(self.session.metadata_path.read_text())['status'], 'aborted')

    def test_recording_failure_stops_queue_with_error(self):
        with patch('Events.adaptiveMethods.funcs.write_toText', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.respond(0, True)
        self.assertEqual(self.window.trials, [])
        self.assertEqual(self.exits, [True])
        self.session.finish()
        self.assertEqual(json.loads(self.session.metadata_path.read_text())['status'], 'error')

    def test_compatibility_helper_has_no_function_object_comparison(self):
        self.assertEqual(_check_responses_history([0, 0], [0, 0], 0, 2, 1), 0)
        self.assertEqual(_check_responses_history([0, 0, 0], [0, 0, 0], 0, 2, 1), 2)
        self.assertEqual(_check_responses_history([], [], 0, 2, 1), 2)


if __name__ == '__main__':
    unittest.main()
