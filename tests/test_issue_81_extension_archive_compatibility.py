"""Issue #81: archive/source portability and explicit workspace schema guards.

Every fixture is disposable, anonymous and synthetic. No real laboratory
records, actual calibration datasets or human acquisition paths are used.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from psychophysics_lab.data.reader import load_run
from psychophysics_lab.data.workspace import (
    load_workspace_state, request_from_workspace_state,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "compatibility" / "unversioned_trial_table.tsv"


def _files(root):
    return {
        path.relative_to(root).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns
        )
        for path in root.rglob("*") if path.is_file()
    }


def _v1_provenance():
    """Structure emitted by Issue #80; hashes here are illustrative, not verified."""
    return {
        "schema_version": 1,
        "origin": "laboratory",
        "namespace": "demolab",
        "experiment_identity": {"namespace": "demolab", "id": "demolab__left_right"},
        "components": [
            {"kind": "experiment", "id": "demolab__left_right",
             "namespace": "demolab", "software_status": "draft"},
            {"kind": "stimulus", "id": "demolab__line",
             "namespace": "demolab", "software_status": "ready"},
        ],
        "source_sha256": {
            "stimulus_library.py": "a" * 64,
            "experiments/demolab__left_right.py": "b" * 64,
        },
        "fingerprint": "c" * 64,
    }


def _archive(tmp_path, provenance):
    folder = tmp_path / "old_machine" / "SYNTHETIC_ONLY" / "run_001"
    folder.mkdir(parents=True)
    shutil.copyfile(FIXTURE, folder / "trials.tsv")
    manifest = {
        "schema_version": 3,
        "trial_schema_version": 1,
        "experiment_id": "demolab__left_right",
        # A stale old installation path is inert metadata.
        "data_root": r"C:\\retired_machine\\lab_data",
        "laboratory_extensions": provenance,
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return folder


def test_archive_with_missing_extension_is_readable_after_relocation(tmp_path):
    original = _archive(tmp_path, _v1_provenance())
    moved = tmp_path / "new_machine" / "moved_archive" / "run_001"
    moved.parent.mkdir(parents=True)
    shutil.copytree(original, moved)
    before = _files(moved)
    loaded = load_run(moved)
    assert loaded["run_directory"] == moved
    assert loaded["trials"]["stimulus_condition"].tolist() == ["left", "right"]
    assert loaded["manifest"]["experiment_id"] == "demolab__left_right"
    assert loaded["manifest"]["laboratory_extensions"] == _v1_provenance()
    assert "demolab__left_right" == loaded["manifest"]["laboratory_extensions"]["experiment_identity"]["id"]
    assert _files(moved) == before
    # No PsyCoLab_Extensions directory was ever installed in this test.
    assert not (tmp_path / "PsyCoLab_Extensions").exists()


@pytest.mark.parametrize("bad", [
    "future_version", "missing_version", "string_version", "null_metadata",
    "bad_origin", "missing_identity", "empty_components", "bad_fingerprint",
    "missing_hashes", "bad_hash", "absolute_source", "path_traversal",
])
def test_corrupt_or_unknown_extension_provenance_is_not_silently_accepted(
    tmp_path, bad,
):
    provenance = copy.deepcopy(_v1_provenance())
    if bad == "future_version":
        provenance["schema_version"] = 2
    elif bad == "missing_version":
        del provenance["schema_version"]
    elif bad == "string_version":
        provenance["schema_version"] = "1"
    elif bad == "null_metadata":
        provenance = None
    elif bad == "bad_origin":
        provenance["origin"] = "official"
    elif bad == "missing_identity":
        provenance["experiment_identity"] = {}
    elif bad == "empty_components":
        provenance["components"] = []
    elif bad == "bad_fingerprint":
        provenance["fingerprint"] = "not-a-hash"
    elif bad == "missing_hashes":
        provenance["source_sha256"] = {}
    elif bad == "bad_hash":
        provenance["source_sha256"]["stimulus_library.py"] = "abcd"
    elif bad == "absolute_source":
        provenance["source_sha256"] = {r"C:\\user\\private.py": "a" * 64}
    elif bad == "path_traversal":
        provenance["source_sha256"] = {"../outside.py": "a" * 64}
    run = _archive(tmp_path, provenance)
    before = _files(run)
    with pytest.raises(ValueError, match="laboratory_extensions"):
        load_run(run)
    assert _files(run) == before


@pytest.mark.parametrize("marker", [4, 999, 0, -1, "3", True, None])
def test_future_or_corrupt_workspace_versions_are_never_loaded_or_rewritten(
    tmp_path, marker,
):
    root = tmp_path / "archive"
    root.mkdir()
    state = {
        "schema_version": marker,
        "last_request": {
            "participant_id": "SYNTHETIC_ONLY", "session_mode": "new",
            "experiment_id": "old_experiment",
            "monitor_profile_id": "legacy_reference_display",
            "experiment_values": {"trial_count": 3},
        },
    }
    path = root / "psycolab_data_config.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    before = _files(root)
    with pytest.raises(ValueError, match="Unsupported workspace schema_version"):
        load_workspace_state(root)
    with pytest.raises(ValueError, match="Unsupported workspace schema_version"):
        request_from_workspace_state(state)
    assert _files(root) == before


@pytest.mark.parametrize("marker", [2, 999, "1", False, None])
def test_unknown_layout_versions_are_rejected_without_guessing_paths(
    tmp_path, marker,
):
    root = tmp_path / "archive"
    root.mkdir()
    state = {
        "schema_version": 3,
        "data_layout_schema_version": marker,
        "last_request": {
            "participant_id": "SYNTHETIC_ONLY", "session_mode": "new",
            "experiment_id": "old_experiment",
            "monitor_profile_id": "legacy_reference_display",
            "experiment_values": {},
        },
    }
    path = root / "psycolab_data_config.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    before = _files(root)
    with pytest.raises(ValueError, match="Unsupported data_layout_schema_version"):
        load_workspace_state(root)
    assert _files(root) == before


@pytest.mark.parametrize("schema", [None, 1, 2, 3])
def test_known_legacy_workspace_shapes_read_without_restore_of_override(
    tmp_path, schema,
):
    root = tmp_path / "archived_data"
    root.mkdir()
    state = {
        "last_request": {
            "participant_id": "SYNTHETIC_ONLY",
            "session_mode": "new",
            "experiment_id": "legacy_experiment",
            "monitor_profile_id": "legacy_reference_display",
            "experiment_values": {"trial_count": 3},
            "data_root": r"C:\\obsolete\\personal_path",
            "researcher_override": {"confirmed_utc": "old"},
        },
    }
    if schema is not None:
        state["schema_version"] = schema
    path = root / "psycolab_data_config.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    before = _files(root)
    loaded = load_workspace_state(root)
    request = request_from_workspace_state(loaded)
    assert request.participant_id == "SYNTHETIC_ONLY"
    assert request.data_root is None
    assert request.researcher_override is None
    assert _files(root) == before


def test_old_manifest_without_extension_field_remains_readable(tmp_path):
    run = _archive(tmp_path, _v1_provenance())
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["laboratory_extensions"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = _files(run)
    assert load_run(run)["manifest"]["experiment_id"] == "demolab__left_right"
    assert _files(run) == before
