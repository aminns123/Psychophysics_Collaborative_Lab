import csv
from pathlib import Path
import tempfile

from psychophysics_lab.data.index import RUN_INDEX_FIELDS, upsert_run_index


def _row(status="configuring", trials=""):
    return {
        "run_uuid": "abc-123",
        "participant_id": "S001",
        "experiment_id": "contrast_sensitivity",
        "monitor_profile_id": "legacy_reference_display",
        "condition_path": "max_500cdm2/background_49cdm2_unverified",
        "date": "2026-09-15",
        "run_number": 1,
        "status": status,
        "accepted_trials": trials,
        "relative_path": (
            "S001/contrast_sensitivity/legacy_reference_display/"
            "max_500cdm2/background_49cdm2_unverified/2026-09-15/run_001"
        ),
        "started_utc": "2026-09-15T09:00:00+00:00",
        "finished_utc": "",
    }


def test_runs_index_upserts_one_human_readable_row_per_run():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        path = upsert_run_index(root, _row())
        upsert_run_index(root, _row(status="completed", trials=42))

        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == list(RUN_INDEX_FIELDS)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["run_uuid"] == "abc-123"
        assert rows[0]["status"] == "completed"
        assert rows[0]["accepted_trials"] == "42"
        assert rows[0]["relative_path"].endswith("run_001")
