"""Issue #81: read old-shape records without modifying scientific evidence.

Fixtures are intentionally synthetic and non-identifying. In addition to
these tests, tests/test_public_run_reader.py exercises actual generated runs.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from psychophysics_lab.config.monitor import _profile_from_dict
from psychophysics_lab.config.models import LuminanceCalibrationPoint
from psychophysics_lab.config.calibration_dataset import (
    active_directory, load_active, summary,
)
from psychophysics_lab.data.reader import load_run
from psychophysics_lab.data.session import read_json_records
from psychophysics_lab.data.workspace import (
    load_workspace_state, request_from_workspace_state,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "compatibility"


def _bytes_under(path):
    """Exact raw bytes of all files underneath a fixture or run directory."""
    return {
        item.relative_to(path).as_posix(): (
            hashlib.sha256(item.read_bytes()).hexdigest(),
            item.stat().st_mtime_ns,
        )
        for item in path.rglob("*") if item.is_file()
    }


def test_older_monitor_profile_without_revision_is_read_only():
    original = FIXTURES / "older_shape_monitor_profile.json"
    before = original.read_bytes()
    profile = _profile_from_dict(json.loads(before.decode("utf-8")))
    assert profile.id == "compatibility_reference_example"
    assert profile.revision == 0  # omitted historical metadata, not a schema
    assert profile.origin == "reference"
    assert not profile.luminance_calibration
    assert profile.calibration_status == "unverified"
    assert original.read_bytes() == before


def test_older_workspace_does_not_reactivate_override_or_machine_path(tmp_path):
    source = FIXTURES / "older_shape_workspace.json"
    root = tmp_path / "data"
    root.mkdir()
    shutil.copyfile(source, root / "psycolab_data_config.json")
    before = _bytes_under(root)
    state = load_workspace_state(root)
    request = request_from_workspace_state(state)
    assert request.participant_id == "TEST_ONLY"
    assert request.show_response_instructions is True  # older optional UI flag
    assert request.researcher_override is None  # NEVER restore human override
    assert request.data_root is None  # don't restore obsolete machine path
    assert _bytes_under(root) == before


def test_legacy_monitor_means_are_summary_only_and_loading_never_saves(tmp_path):
    source = json.loads((FIXTURES / "older_shape_monitor_profile.json").read_text(encoding="utf-8"))
    old = _profile_from_dict(source)
    profile = replace(
        old, id="old_mean_mapping", origin="local",
        luminance_calibration=(
            LuminanceCalibrationPoint(0.0, 0.5),
            LuminanceCalibrationPoint(0.8, 80.0),
        ),
    )
    dataset = load_active(tmp_path, profile)
    assert dataset["schema_version"] == 1
    assert dataset["version"] == 0
    assert len(dataset["observations"]) == 2
    assert all(r["source"] == "legacy_summary_only" for r in dataset["observations"])
    groups = summary(dataset)
    assert len(groups) == 2
    assert all(row["summary_only"] is True and row["n"] is None
               for row in groups)
    assert not list(tmp_path.rglob("*"))  # no profile or measurement writes


@pytest.mark.parametrize("schema", [2, 999, "1", None])
def test_unknown_or_corrupt_active_luminance_schema_does_not_touch_disk(
    tmp_path, schema,
):
    source = json.loads((FIXTURES / "older_shape_monitor_profile.json").read_text(encoding="utf-8"))
    profile = replace(_profile_from_dict(source), id="old_measurement_root", origin="local")
    active = active_directory(tmp_path, profile) / "luminance.json"
    active.parent.mkdir(parents=True)
    active.write_text(json.dumps({
        "monitor_profile_id": profile.id,
        "schema_version": schema,
        "observations": [],
    }), encoding="utf-8")
    original = _bytes_under(tmp_path)
    with pytest.raises(ValueError, match="identity/schema"):
        load_active(tmp_path, profile)
    assert _bytes_under(tmp_path) == original


def test_unversioned_named_trial_table_is_exposed_without_adding_columns(tmp_path):
    run = tmp_path / "P001" / "run_001"
    run.mkdir(parents=True)
    shutil.copyfile(
        FIXTURES / "unversioned_trial_table.tsv", run / "trials.tsv"
    )
    before = _bytes_under(tmp_path)
    loaded = load_run(run)
    assert loaded["manifest"] == {}
    assert set(loaded["trials"]) == {"trial_index", "correct", "stimulus_condition"}
    assert loaded["trials"]["correct"].tolist() == ["1", "0"]
    assert "presented_screen_intensity" not in loaded["trials"]
    assert _bytes_under(tmp_path) == before
    assert load_run(run / "trials.tsv")["trials"]["trial_index"].tolist() == ["1", "2"]


@pytest.mark.parametrize("value", [4, 999, -1, True, "3"])
def test_unknown_future_or_ambiguous_manifest_rejected_without_write(tmp_path, value):
    run = tmp_path / "run_001"
    run.mkdir()
    shutil.copyfile(
        FIXTURES / "unversioned_trial_table.tsv", run / "trials.tsv"
    )
    (run / "manifest.json").write_text(
        json.dumps({"schema_version": value, "trial_schema_version": 1}),
        encoding="utf-8",
    )
    before = _bytes_under(run)
    with pytest.raises(ValueError, match="Unsupported manifest schema_version"):
        load_run(run)
    assert _bytes_under(run) == before


def test_known_archived_manifest_read_as_opaque_metadata_not_migrated(tmp_path):
    run = tmp_path / "run_001"
    run.mkdir()
    shutil.copyfile(FIXTURES / "unversioned_trial_table.tsv", run / "trials.tsv")
    (run / "manifest.json").write_text(
        json.dumps({"schema_version": 2, "trial_schema_version": 1,
                    "experiment_id": "old_example"}), encoding="utf-8"
    )
    before = _bytes_under(run)
    result = load_run(run)
    assert result["manifest"]["schema_version"] == 2
    assert result["manifest"]["experiment_id"] == "old_example"
    assert _bytes_under(run) == before


def test_truncated_event_journal_is_detected_without_removing_complete_rows(tmp_path):
    journal = tmp_path / "trial_events.jsonl"
    journal.write_bytes(b'{"trial_index": 1}\n{"trial_index": 2}')
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="Incomplete final journal record"):
        list(read_json_records(journal))
    assert journal.read_bytes() == before
