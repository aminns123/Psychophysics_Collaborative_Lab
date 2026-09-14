import csv
from pathlib import Path
import tempfile

from psychophysics_lab.data.trials import TRIAL_COLUMNS, TrialLog


def test_trial_log_is_append_only_with_explicit_presented_and_next_values():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "trials.tsv"
        log = TrialLog(path)
        log.append(
            {
                "trial_index": 1,
                "staircase_id": 0,
                "staircase_trial_index": 1,
                "stimulus_condition": 63,
                "stimulus_position_px": 100,
                "target_alternative": 0,
                "participant_response": 0,
                "response_key": "LEFT",
                "correct": 1,
                "presented_display_contrast": 1.0,
                "presented_screen_intensity": 1.0,
                "step": "down",
                "reversal": 0,
                "reversal_count": 0,
                "next_display_contrast": 0.8,
                "next_screen_intensity": 0.9,
                "staircase_complete": 0,
                "run_status": "running",
            }
        )
        log.append(
            {
                "trial_index": 2,
                "staircase_id": 0,
                "staircase_trial_index": 2,
                "stimulus_condition": 63,
                "stimulus_position_px": 200,
                "target_alternative": 1,
                "participant_response": 0,
                "response_key": "LEFT",
                "correct": 0,
                "presented_display_contrast": 0.8,
                "presented_screen_intensity": 0.9,
                "step": "up",
                "reversal": 1,
                "reversal_count": 1,
                "next_display_contrast": 0.95,
                "next_screen_intensity": 0.975,
                "staircase_complete": 0,
                "run_status": "running",
            }
        )

        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))

        assert tuple(rows[0].keys()) == TRIAL_COLUMNS
        assert len(rows) == 2
        assert rows[0]["presented_screen_intensity"] == "1.0"
        assert rows[0]["next_screen_intensity"] == "0.9"
        assert rows[1]["reversal"] == "1"
