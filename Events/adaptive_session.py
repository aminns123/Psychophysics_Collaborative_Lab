"""Legacy CSF file/event adapter; not a universal experiment interface.

Pure staircase mechanics live in staircase.py. This adapter owns the existing
CSF correctness mapping and files until the broader experiment API is migrated.
It also writes PsyCoLab's append-only canonical ``trials.tsv`` record while the
legacy six-column response file is retained for backwards compatibility.
"""

import json
import os
from pathlib import Path

from Events.adaptiveMethods import record_event
from Events.display_contrast import normalized_display_contrast
from Events.staircase import AdaptiveRun, StaircaseConfig
import Functions.functionsForUse as funcs
from psychophysics_lab.data.trials import TrialLog


_LEFT_KEYS = {"LSHIFT", "LEFT", "DOWN"}
_RIGHT_KEYS = {"RSHIFT", "RIGHT", "UP"}


def _response_value(key):
    text = str(key).upper()
    if text in _LEFT_KEYS:
        return 0
    if text in _RIGHT_KEYS:
        return 1
    raise ValueError(f"Unrecognised response key: {key}")


class LegacyStaircaseSession:
    def __init__(self, conditions_path, parameters_path, response_path, max_trials):
        conditions = funcs.read_JSON(conditions_path)
        self.parameters = funcs.read_JSON(parameters_path)
        self.metadata_path = Path(response_path).with_suffix('.session.json')
        self.conditions_path = conditions_path
        self.trial_log = TrialLog(Path(response_path).parent / 'trials.tsv')
        self.run = AdaptiveRun({
            identity: StaircaseConfig(
                n_down=self.parameters['n_dw'],
                n_up=self.parameters['n_up'],
                reversal_limit=conditions['reversal_termination'][identity])
            for identity in conditions['staircase_Identities']
        }, max_trials)
        self.save()

    def attach(self, trial):
        trial.adaptive_run = self.run
        return trial

    def save(self, status=None, error=None):
        metadata = self.run.snapshot()
        metadata.update({
            'schema_version': 2,
            'legacy_parameters': self.parameters,
            'reversal_basis': 'recorded_post_update_screen_intensity; flats ignored; no placeholder row',
            'canonical_trial_log': str(self.trial_log.path),
            'canonical_trial_semantics': (
                'presented_* is the stimulus state used for the accepted response; '
                'next_* is the post-response staircase state for a subsequent presentation'
            ),
        })
        if status is not None:
            metadata['status'] = status
        if error is not None:
            metadata['error'] = str(error)
        temporary = self.metadata_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(metadata, indent=4), encoding='utf-8')
        os.replace(temporary, self.metadata_path)

    def _capture_pre_response(self, event, trial, args):
        if event != 'KEY' or trial is None or trial.name != 'response':
            return None
        if len(args) < 2 or args[1] not in trial.keys:
            return None
        if getattr(trial, 'response_recorded', False):
            return None

        conditions = funcs.read_JSON(self.conditions_path)
        staircase_id = int(conditions['staircase_Identity_active'][0])
        presented_intensity = float(conditions['staircase_intensity_active'][staircase_id])
        presented_contrast = normalized_display_contrast(
            presented_intensity,
            background_intensity=float(self.parameters['background_intensity']),
            maximum_intensity=float(self.parameters['max_intensity']),
        )
        state = self.run.states[staircase_id]
        response = _response_value(args[0])
        target = int(conditions['probe_Alternative_Choice'][staircase_id])
        config = self.run.configurations[staircase_id]
        if target == response:
            expected_step = 'down' if state.streak.correct + 1 == config.n_down else 'hold'
        else:
            expected_step = 'up' if state.streak.incorrect + 1 == config.n_up else 'hold'

        return {
            'staircase_id': staircase_id,
            'staircase_trial_before': state.trial_count,
            'reversal_before': state.reversal_count,
            'expected_step': expected_step,
            'stimulus_condition': conditions['condition_list'][staircase_id],
            'stimulus_position_px': conditions.get('stimulus_choice_active', [''])[0],
            'target_alternative': target,
            'participant_response': response,
            'response_key': str(args[0]),
            'correct': target == response,
            'presented_display_contrast': presented_contrast,
            'presented_screen_intensity': presented_intensity,
        }

    def _append_canonical_trial(self, before, event_time):
        staircase_id = before['staircase_id']
        conditions = funcs.read_JSON(self.conditions_path)
        next_intensity = float(conditions['staircase_intensity_active'][staircase_id])
        next_contrast = normalized_display_contrast(
            next_intensity,
            background_intensity=float(self.parameters['background_intensity']),
            maximum_intensity=float(self.parameters['max_intensity']),
        )
        state = self.run.states[staircase_id]

        self.trial_log.append({
            'trial_index': self.run.total_trials,
            'event_time_s': event_time,
            'staircase_id': staircase_id,
            'staircase_trial_index': state.trial_count,
            'stimulus_condition': before['stimulus_condition'],
            'stimulus_position_px': before['stimulus_position_px'],
            'target_alternative': before['target_alternative'],
            'participant_response': before['participant_response'],
            'response_key': before['response_key'],
            'correct': int(before['correct']),
            'presented_display_contrast': before['presented_display_contrast'],
            'presented_screen_intensity': before['presented_screen_intensity'],
            'step': before['expected_step'],
            'reversal': int(state.reversal_count > before['reversal_before']),
            'reversal_count': state.reversal_count,
            'next_display_contrast': next_contrast,
            'next_screen_intensity': next_intensity,
            'staircase_complete': int(state.complete),
            'run_status': self.run.status,
        })

    def logger(self, window):
        def log(event, time, trial, args):
            previous_count = self.run.total_trials
            before = self._capture_pre_response(event, trial, args)
            try:
                record_event(event, time, trial, args)
                if self.run.total_trials != previous_count:
                    if before is None:
                        raise RuntimeError(
                            'Adaptive response count changed without a canonical pre-response snapshot.'
                        )
                    self._append_canonical_trial(before, time)
                    self.save()
                    if self.run.status != 'running':
                        window.trials.clear()
                        window.exit()
            except Exception as exc:
                # The legacy engine catches logger errors and otherwise advances.
                # Stop this experiment instead of continuing with partial state.
                try:
                    self.save(status='error', error=exc)
                finally:
                    window.trials.clear()
                    window.exit()
                raise
        return log

    def finish(self):
        # Preserve an error recorded by the logger. Escape/close is not success.
        if self.metadata_path.exists():
            if json.loads(self.metadata_path.read_text(encoding='utf-8'))['status'] == 'error':
                return
        self.save(status='aborted' if self.run.status == 'running' else self.run.status)
