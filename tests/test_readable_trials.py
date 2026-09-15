import csv
from pathlib import Path
import tempfile

from psychophysics_lab.data.trials import (
    READABLE_TRIALS_FILENAME,
    TRIAL_COLUMNS,
    TrialLog,
    write_readable_trial_table,
)


def _row(index: int, response_key: str, contrast: float):
    return {
        "trial_index": index,
        "event_time_s": 123.456 + index,
        "staircase_id": 0,
        "staircase_trial_index": index,
        "stimulus_condition": 63.0,
        "stimulus_position_px": 987,
        "target_alternative": 1,
        "participant_response": 1,
        "response_key": response_key,
        "correct": 1,
        "presented_display_contrast": contrast,
        "presented_screen_intensity": 1.0,
        "step": "hold",
        "reversal": 0,
        "reversal_count": 0,
        "next_display_contrast": contrast,
        "next_screen_intensity": 1.0,
        "staircase_complete": 0,
        "run_status": "running",
    }


def test_readable_trial_table_aligns_columns_without_changing_tsv():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        tsv = root / "trials.tsv"
        log = TrialLog(tsv)
        log.append(_row(1, "R", 1.0))
        log.append(_row(2, "RIGHT", 0.6425693407676499))

        before = tsv.read_bytes()
        readable = write_readable_trial_table(tsv)

        assert readable.name == READABLE_TRIALS_FILENAME
        assert tsv.read_bytes() == before  # canonical data are untouched

        lines = readable.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 4  # header + separator + 2 data rows

        # Every canonical header begins at the same character position in the
        # header and the separator spans the measured width for that column.
        header = lines[0]
        assert header.startswith("trial_index")
        assert "recorded_utc" in header
        assert "presented_display_contrast" in header

        # Longer values make only their own column wider; rows remain aligned.
        response_key_pos = header.index("response_key")
        assert lines[2][response_key_pos : response_key_pos + 1] == "R"
        assert lines[3][response_key_pos : response_key_pos + 5] == "RIGHT"


def test_readable_writer_rejects_noncanonical_header():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        tsv = root / "trials.tsv"
        tsv.write_text("wrong\tcolumns\n1\t2\n", encoding="utf-8")

        try:
            write_readable_trial_table(tsv)
        except ValueError as exc:
            assert "do not match" in str(exc)
        else:
            raise AssertionError("Expected ValueError for a noncanonical TSV header.")
