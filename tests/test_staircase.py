import unittest

from Events.staircase import AdaptiveRun, ResponseStreak, StaircaseConfig, Step


class ResponseRuleTests(unittest.TestCase):
    def sequence(self, responses, down, up):
        state = ResponseStreak()
        return [state.respond(r, down, up) for r in responses]

    def test_one_down_one_up(self):
        self.assertEqual(self.sequence([True, False, True, False], 1, 1),
                         [Step.DOWN, Step.UP, Step.DOWN, Step.UP])

    def test_two_down_one_up_no_overlapping_windows(self):
        self.assertEqual(self.sequence([True] * 6, 2, 1),
                         [Step.HOLD, Step.DOWN] * 3)

    def test_four_down_one_up(self):
        self.assertEqual(self.sequence([True] * 8, 4, 1),
                         [Step.HOLD] * 3 + [Step.DOWN] + [Step.HOLD] * 3 + [Step.DOWN])

    def test_three_down_one_up(self):
        self.assertEqual(self.sequence([True] * 6, 3, 1),
                         [Step.HOLD, Step.HOLD, Step.DOWN] * 2)

    def test_incorrect_clears_correct_streak(self):
        self.assertEqual(self.sequence([True, False, True, True], 2, 1),
                         [Step.HOLD, Step.UP, Step.HOLD, Step.DOWN])

    def test_correct_clears_incorrect_streak(self):
        self.assertEqual(self.sequence([False, True, False, False], 1, 2),
                         [Step.HOLD, Step.DOWN, Step.HOLD, Step.UP])

    def test_up_streak_resets_after_step(self):
        self.assertEqual(self.sequence([False] * 6, 4, 2),
                         [Step.HOLD, Step.UP] * 3)

    def test_no_step_before_full_streak(self):
        state = ResponseStreak()
        for _ in range(3):
            self.assertEqual(state.respond(True, 4, 2), Step.HOLD)
        self.assertEqual(state.correct, 3)
        self.assertEqual(state.respond(True, 4, 2), Step.DOWN)
        self.assertEqual(state.correct, 0)
        self.assertEqual(state.respond(True, 4, 2), Step.HOLD)
        self.assertEqual(state.correct, 1)

    def test_validation(self):
        for value in [0, -1, True, 1.5]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                StaircaseConfig(value, 1, 10)
        with self.assertRaises(TypeError):
            ResponseStreak().respond(1, 2, 1)


class LifecycleTests(unittest.TestCase):
    def make_run(self, limits=(1, 2), max_trials=30):
        return AdaptiveRun({i: StaircaseConfig(2, 1, limit)
                            for i, limit in enumerate(limits)}, max_trials)

    def value(self, run, identity, value, correct=True):
        return run.respond(identity, correct, lambda step: value)

    def test_interleaved_streaks(self):
        run = self.make_run()
        results = [run.respond(i, True, lambda step: 1)[0] for i in [0, 1, 0, 1, 0]]
        self.assertEqual(results, [Step.HOLD, Step.HOLD, Step.DOWN, Step.DOWN, Step.HOLD])
        self.assertEqual([s.trial_count for s in run.states.values()], [3, 2])
        self.assertEqual([s.streak.correct for s in run.states.values()], [1, 0])

    def test_early_finisher_does_not_end_other(self):
        run = self.make_run()
        for value in [3, 2, 3]:
            self.value(run, 0, value)
        self.assertEqual(run.active_ids, (1,))
        self.assertEqual(run.status, 'running')
        self.assertEqual(run.states[1].trial_count, 0)
        for value in [5, 4, 5, 4]:
            self.value(run, 1, value)
        self.assertEqual(run.status, 'completed')
        self.assertEqual(run.total_trials, 7)
        self.assertEqual(run.active_ids, ())

    def test_completed_ids_cannot_be_selected_or_updated(self):
        run = self.make_run()
        for value in [3, 2, 3]:
            self.value(run, 0, value)
        self.assertEqual(run.select(lambda ids: ids[0]), 1)
        with self.assertRaises(ValueError):
            run.select(lambda ids: 0)
        with self.assertRaises(ValueError):
            self.value(run, 0, 2)
        self.assertEqual(run.states[0].trial_count, 3)

    def test_three_staircases_finish_at_different_times(self):
        run = self.make_run((1, 2, 3))
        for i in [0, 1, 2]:
            self.value(run, i, 3)
            self.value(run, i, 2)
        for i in [0, 1, 2]:
            self.value(run, i, 3)
        self.assertEqual(run.active_ids, (1, 2))
        for i in [1, 2]:
            self.value(run, i, 2)
        self.assertEqual(run.active_ids, (2,))
        self.value(run, 2, 3)
        self.assertEqual(run.status, 'completed')
        self.assertEqual([s.reversal_count for s in run.states.values()], [1, 2, 3])

    def test_interleaved_reversals_are_independent(self):
        run = self.make_run((3, 3))
        for a, b in zip([3, 2, 3, 2], [10, 9, 8, 7]):
            self.value(run, 0, a)
            self.value(run, 1, b)
        self.assertEqual([s.reversal_count for s in run.states.values()], [2, 0])

    def test_flats_do_not_count_as_reversals(self):
        run = self.make_run((10,))
        for value in [3, 3, 2, 2, 3, 3, 2]:
            self.value(run, 0, value)
        self.assertEqual(run.states[0].reversal_count, 2)

    def test_reversals_match_existing_detector_on_recorded_values(self):
        from Events.adaptiveMethods import count_reversals_HighLow
        for values in ([1], [1, 1, 1], [3, 2, 2, 3, 3, 2], [1, 1, 2, 3, 2, 1, 2]):
            with self.subTest(values=values):
                run = self.make_run((100,))
                for value in values:
                    self.value(run, 0, value)
                self.assertEqual(run.states[0].reversal_count, count_reversals_HighLow(values)[0])

    def test_ceiling_records_complete_and_unfinished(self):
        run = self.make_run(max_trials=4)
        for value in [3, 2, 3]:
            self.value(run, 0, value)
        self.value(run, 1, 5)
        snapshot = run.snapshot()
        self.assertEqual(snapshot['status'], 'max_trials_reached')
        self.assertEqual(snapshot['completed_staircase_ids'], [0])
        self.assertEqual(snapshot['active_staircase_ids'], [1])
        self.assertEqual(snapshot['staircases']['1']['trial_count'], 1)
        self.assertEqual(snapshot['staircases']['1']['reversal_count'], 0)
        with self.assertRaises(RuntimeError):
            run.select(lambda ids: ids[0])
        with self.assertRaises(RuntimeError):
            self.value(run, 1, 4)

    def test_completion_on_last_budget_response_is_success(self):
        run = self.make_run((1,), 3)
        for value in [3, 2, 3]:
            self.value(run, 0, value)
        self.assertEqual(run.status, 'completed')
        with self.assertRaises(RuntimeError):
            run.select(lambda ids: ids[0])

    def test_failed_numeric_update_does_not_consume_response(self):
        run = self.make_run()
        with self.assertRaises(ValueError):
            self.value(run, 0, float('nan'))
        self.assertEqual(run.total_trials, 0)
        self.assertEqual(run.states[0].streak.correct, 0)

    def test_distinct_rules_per_staircase(self):
        run = AdaptiveRun({'a': StaircaseConfig(4, 1, 5),
                           'b': StaircaseConfig(1, 2, 7)}, 20)
        self.assertEqual(run.respond('a', True, lambda s: 1)[0], Step.HOLD)
        self.assertEqual(run.respond('b', True, lambda s: 1)[0], Step.DOWN)

    def test_run_configuration_validation(self):
        with self.assertRaises(ValueError):
            AdaptiveRun({}, 30)
        with self.assertRaises(ValueError):
            self.make_run(max_trials=0)


if __name__ == '__main__':
    unittest.main()
