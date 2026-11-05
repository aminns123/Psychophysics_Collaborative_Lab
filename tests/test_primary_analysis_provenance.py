"""Derived primary reports must preserve the context of their source data."""
import csv
import hashlib
import json

import pytest

from psychophysics_lab.analysis.thresholds import analyse_thresholds


def archive(tmp_path, kind, status, boundary=False):
    run = tmp_path / "data" / "archive"
    run.mkdir(parents=True)
    manifest = {"status": status, "data_kind": kind, "run_uuid": "source-001",
                "participant_id": "audit", "experiment_id": "independent_archive",
                "simulation": {"seed": 1729} if kind == "synthetic" else None,
                "calibration": {"status": "manual_unverified"},
                "runtime_display": {"timing_status": "unverified"},
                "software": {"git": {"commit": "archived-source"}}}
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rule = {"version": 1, "value_column": "presented_display_contrast", "retained_reversals": 2,
            "within_staircase": "median", "across_staircases": "arithmetic_mean",
            "units": "digital_increment", "strength_bounds": {"1": [0., .4]}}
    expected = {"near": [1]}
    if status != "completed":
        expected["far"] = [2]  # This condition has no accepted response.
    (run / "resolved_experiment.json").write_text(json.dumps({
        "primary_estimator": rule, "expected_staircases": expected}), encoding="utf-8")
    fields = ("staircase_id", "stimulus_condition", "reversal", "presented_display_contrast",
              "next_display_contrast", "staircase_complete")
    with (run / "trials.tsv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(fields)
        writer.writerows([(1, "near", 1, .1, .2, 0), (1, "near", 1, .3, .4 if boundary else .2, 1)])
    return run


@pytest.mark.parametrize("kind", ["synthetic", "uncalibrated_presentation_test", "human"])
@pytest.mark.parametrize("status", ["completed", "max_trials_reached", "aborted_by_user"])
def test_primary_export_preserves_origin_quality_and_inputs(tmp_path, monkeypatch, kind, status):
    from psychophysics_lab.analysis import thresholds
    run = archive(tmp_path, kind, status, boundary=True)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}
    plotted = []
    monkeypatch.setattr(thresholds, "_plot", lambda *args, **kw: plotted.append(kw) or None)
    result = analyse_thresholds(data_root=tmp_path / "data", run_directory=run)
    saved = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert saved["data_kind"] == kind
    assert saved["simulation"] == ({"seed": 1729} if kind == "synthetic" else None)
    assert saved["source_run_uuid"] == "source-001"
    assert saved["source_run_relative"] == "archive"
    assert saved["source_software"]["git"]["commit"] == "archived-source"
    assert saved["input_sha256"] == before
    flags = saved["quality_flags"]
    assert flags["source_status"] == status
    assert flags["incomplete_run"] == (status != "completed")
    assert flags["missing_staircase_estimates"] == ([] if status == "completed" else ["2"])
    assert flags["boundary_affected_staircases"] == ["1"]
    assert flags["calibration_status"] == "manual_unverified"
    assert flags["timing_status"] == "unverified"
    assert flags["photon_timing_verified"] is False
    warning = plotted[0]["warning"]
    assert saved["scientific_warning"] == warning
    assert ("SYNTHETIC" in warning) == (kind == "synthetic")
    assert ("UNCALIBRATED PRESENTATION TEST" in warning) == (kind == "uncalibrated_presentation_test")
    assert ("INCOMPLETE/CENSORED" in warning) == (status != "completed")
    assert "BOUNDARY" in warning and "digital" in warning.lower()
    assert saved["condition_thresholds"] == {"near": {"threshold": .2, "sensitivity": 5.}}
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}


def test_old_primary_archive_has_explicit_unknown_origin_and_no_false_qualification(tmp_path):
    run = archive(tmp_path, "human", "completed")
    (run / "manifest.json").write_text('{"status":"completed"}', encoding="utf-8")
    result = analyse_thresholds(data_root=tmp_path / "data", run_directory=run, create_plot=False)
    saved = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert saved["data_kind"] == "unknown"
    assert saved["quality_flags"]["calibration_status"] == "unverified"
    assert saved["quality_flags"]["photon_timing_verified"] is False
    assert "UNKNOWN DATA ORIGIN" in saved["scientific_warning"]


def test_real_aborted_run_exports_only_completed_conditions_with_warning(tmp_path, monkeypatch):
    from pathlib import Path
    from psychophysics_lab.researcher import RunContext
    from simulations.run import simulate
    from simulations.registry import TeachingObserver
    original = RunContext.trial

    def abort_after_one_complete(self, *args, **kwargs):
        path = self.run_directory / "trials.tsv"
        if path.exists():
            with path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter="\t"))
            if any(row["staircase_complete"] == "1" for row in rows):
                self.abort("Release audit: stop after the first completed condition")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(RunContext, "trial", abort_after_one_complete)
    artifact, _ = simulate(repo_root=Path(__file__).resolve().parents[1], data_root=tmp_path / "data",
        experiment_id="contrast_sensitivity", seed=1729, observer=TeachingObserver(.65), analyse=False,
        values={"frequencies_cpd": "2,5", "staircases_per_condition": 1, "n_down": 2,
                "reversal_termination": 4, "threshold_reversals": 2, "max_trials": 512})
    assert artifact.status == "aborted_by_user"
    from scripts.validate_run import validate_run
    assert all(check.passed for check in validate_run(artifact.run_directory))
    result = analyse_thresholds(data_root=tmp_path / "data", run_directory=artifact.run_directory, create_plot=False)
    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert len(summary["condition_thresholds"]) == 1
    assert len(summary["excluded_staircases"]) == 1
    assert summary["quality_flags"]["incomplete_run"] is True
    assert "SYNTHETIC" in summary["scientific_warning"]
    assert "INCOMPLETE/CENSORED" in summary["scientific_warning"]
