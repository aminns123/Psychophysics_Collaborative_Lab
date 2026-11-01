"""Test the generic record/compare engine, never researcher-written pytest."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from psychophysics_lab import experiment_reference as refs
from psychophysics_lab import development
from psychophysics_lab.experiments._internal import registry


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    root = tmp_path / "USER_env"
    run = root / "synthetic-run"
    run.mkdir(parents=True)
    for name in refs.SCIENCE_FILES:
        (run / name).write_text("science:" + name + "\n", encoding="utf-8")
    report_file = root / "software_test_reports" / "demo__task.json"
    report_file.parent.mkdir()
    report = {
        "schema_version": 1, "experiment_id": "demo__task",
        "result": "pass", "source_digest": "a" * 64,
        "selected_values": {"contrast": .25, "trials": 4},
        "synthetic_seed": 123,
        "synthetic_run": {
            "passed": True, "status": "completed",
            "accepted_trials": 4, "run_directory": str(run),
        },
    }
    report_file.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(development, "user_data_root", lambda repo: root)
    monkeypatch.setattr(registry, "get_experiment", lambda identity: SimpleNamespace(id=identity))
    monkeypatch.setattr(refs, "source_digest", lambda repo, spec: "a" * 64)
    return root, run, report_file, report


def test_save_then_compare_same_science_without_writing_tests(synthetic, tmp_path):
    root, run, report_file, report = synthetic
    source = refs.save_reference(tmp_path, "demo__task")
    assert source.is_file()
    saved = json.loads(source.read_text())
    assert saved["scientific_validation"] == "researcher_review_required"
    assert saved["synthetic_seed"] == 123
    assert saved["synthetic_accepted_trials"] == 4
    result = refs.compare_latest_reference(tmp_path, "demo__task")
    assert result["same_scientific_behaviour"] is True
    assert result["source_changed_since_reference"] is False


def test_compare_flags_changes_in_trial_events_and_settings(synthetic, tmp_path):
    root, run, report_file, report = synthetic
    refs.save_reference(tmp_path, "demo__task")
    (run / "trial_actions.json").write_text("different event order", encoding="utf-8")
    report["selected_values"]["contrast"] = .4
    report_file.write_text(json.dumps(report), encoding="utf-8")
    result = refs.compare_latest_reference(tmp_path, "demo__task")
    assert result["same_scientific_behaviour"] is False
    assert "Saved synthetic trial_actions.json changed." in result["differences"]
    assert "Selected scientific settings changed." in result["differences"]


def test_reference_requires_success_current_source_and_safe_run_folder(synthetic, tmp_path, monkeypatch):
    root, run, report_file, report = synthetic
    monkeypatch.setattr(refs, "source_digest", lambda repo, spec: "b" * 64)
    with pytest.raises(ValueError, match="changed since Test"):
        refs.save_reference(tmp_path, "demo__task")
    monkeypatch.setattr(refs, "source_digest", lambda repo, spec: "a" * 64)
    report["synthetic_run"]["status"] = "max_trials_reached"
    report_file.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        refs.save_reference(tmp_path, "demo__task")
    report["synthetic_run"]["status"] = "completed"
    report["synthetic_run"]["run_directory"] = str(tmp_path)
    report_file.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="outside USER_env_data"):
        refs.save_reference(tmp_path, "demo__task")


def test_scientific_source_revision_is_reported_separately_from_behaviour(synthetic, tmp_path, monkeypatch):
    root, run, report_file, report = synthetic
    refs.save_reference(tmp_path, "demo__task")
    report["source_digest"] = "b" * 64
    report_file.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(refs, "source_digest", lambda repo, spec: "b" * 64)
    result = refs.compare_latest_reference(tmp_path, "demo__task")
    assert result["same_scientific_behaviour"]
    assert result["source_changed_since_reference"]
