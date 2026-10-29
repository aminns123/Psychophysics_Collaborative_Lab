"""Teaching scenarios validate the selected analysis without inventing thresholds."""
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from simulations.run import simulate
from simulations.scenarios import SimulationScenario, get_scenario, run_scenario
from simulations.scenarios.run import ScenarioRun


ROOT = Path(__file__).resolve().parents[1]
ADAPTIVE_EXPERIMENTS = (
    "contrast_sensitivity", "contrast_sensitivity_windowed",
    "line_position_baseline", "line_position_flanker",
    "ellipse_centre", "ellipse_major_axis",
)
# Explicit synthetic study choices from the frozen event-first baseline;
# required researcher inputs must not silently become application defaults.
STUDY_CHOICES = {
    "line_position_baseline": {"probe_vertical_offset_deg": 0.4},
    "line_position_flanker": {"probe_vertical_offset_deg": 0.4, "flanker_cpd": 2.0},
    "ellipse_centre": {"ring_increment": 0.03},
    "ellipse_major_axis": {"ring_increment": 0.03},
}


def analysis_checks(result):
    checks = [item for item in result.checks if item["name"].startswith("experiment-specific analysis expectation")]
    assert len(checks) == len(result.runs)
    return checks


def test_completed_csf_teaching_analysis_passes_and_preserves_scientific_trials(tmp_path):
    reference, reference_analysis = simulate(data_root=tmp_path / "reference", repo_root=ROOT)
    result = run_scenario(experiment_id="contrast_sensitivity", scenario_id="teaching_demo",
                          data_root=tmp_path / "scenario", repo_root=ROOT)
    assert reference_analysis is not None and result.runs[0].analysis is not None
    assert result.runs[0].artifacts.status == "completed"
    assert result.passed, result.checks
    assert all(item["passed"] for item in analysis_checks(result))
    assert result.runs[0].artifacts.trial_log_file.read_bytes() == reference.trial_log_file.read_bytes()
    report = json.loads(result.report_file.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["experiment_evaluation"]["checks"]


@pytest.mark.parametrize("experiment_id", ADAPTIVE_EXPERIMENTS)
def test_short_adaptive_teaching_requires_recorded_unavailability(tmp_path, experiment_id):
    result = run_scenario(experiment_id=experiment_id, scenario_id="teaching_demo", repo_root=ROOT,
                          data_root=tmp_path / "synthetic",
                          experiment_values=STUDY_CHOICES.get(experiment_id, {}) | {"max_trials": 1})
    record = result.runs[0]
    assert record.artifacts.status == "max_trials_reached"
    assert record.analysis is None
    assert (record.artifacts.run_directory / "analysis" / "threshold_unavailable.json").is_file()
    assert result.passed, result.checks
    assert all(item["passed"] for item in analysis_checks(result))


@pytest.mark.parametrize("experiment_id", ADAPTIVE_EXPERIMENTS)
def test_fixed_level_teaching_has_no_staircase_threshold(tmp_path, experiment_id):
    result = run_scenario(experiment_id=experiment_id, scenario_id="teaching_demo", repo_root=ROOT,
                          data_root=tmp_path / "synthetic", experiment_values=STUDY_CHOICES.get(experiment_id, {}) | {
                              "contrast_method": "constant_stimuli", "fixed_contrasts": "0.1",
                              "fixed_repetitions": 1,
                          })
    assert result.runs[0].analysis is None
    assert result.passed, result.checks
    assert all(item["passed"] for item in analysis_checks(result))


@pytest.mark.parametrize("experiment_id", (
    "example_experiment", "probe_above_below", "orientation_task", "orientation_adaptive",
))
def test_teaching_without_analyser_requires_no_analysis(tmp_path, experiment_id):
    result = run_scenario(experiment_id=experiment_id, scenario_id="teaching_demo", repo_root=ROOT,
                          data_root=tmp_path / "synthetic")
    assert result.runs[0].analysis is None
    assert result.passed, result.checks
    assert all(item["passed"] for item in analysis_checks(result))


@pytest.mark.parametrize("status,payload", (
    ("max_trials_reached", None),
    ("max_trials_reached", "broken JSON"),
    ("max_trials_reached", []),
    ("max_trials_reached", {"data_kind": "human", "reason": "Primary thresholds unavailable"}),
    ("max_trials_reached", {"data_kind": "synthetic", "reason": "unexpected analyser failure"}),
    ("max_trials_reached", {"data_kind": "synthetic", "reason": 1}),
    ("completed", {"data_kind": "synthetic", "reason": "Primary thresholds unavailable"}),
))
def test_missing_or_invalid_analysis_cannot_pass_teaching_check(tmp_path, status, payload):
    (tmp_path / "experiment_config.json").write_text(json.dumps({
        "normalised_experiment_values": {"contrast_method": "adaptive"},
    }), encoding="utf-8")
    if payload is not None:
        (tmp_path / "analysis").mkdir()
        path = tmp_path / "analysis" / "threshold_unavailable.json"
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    record = ScenarioRun(123, SimpleNamespace(run_directory=tmp_path, status=status), None)
    evaluation = get_scenario("contrast_sensitivity", "teaching_demo").evaluate(None, (record,))
    assert evaluation["checks"][0]["passed"] is False


@pytest.mark.parametrize("experiment_id,method", (
    ("example_experiment", "original"), ("contrast_sensitivity", "constant_stimuli"),
))
def test_unexpected_analysis_cannot_pass_teaching_check(tmp_path, experiment_id, method):
    (tmp_path / "experiment_config.json").write_text(json.dumps({
        "normalised_experiment_values": {"contrast_method": method},
    }), encoding="utf-8")
    record = ScenarioRun(123, SimpleNamespace(run_directory=tmp_path, status="completed"), object())
    evaluation = get_scenario(experiment_id, "teaching_demo").evaluate(None, (record,))
    assert evaluation["checks"][0]["passed"] is False


def test_explicit_custom_scenario_analysis_expectation_remains_strict(tmp_path, monkeypatch):
    runner = importlib.import_module("simulations.scenarios.run")
    monkeypatch.setattr(runner, "get_scenario", lambda *args: SimulationScenario(
        "strict_analysis", "contrast_sensitivity", "Requires a threshold", expect_analysis=True,
    ))
    result = run_scenario(experiment_id="contrast_sensitivity", scenario_id="strict_analysis", repo_root=ROOT,
                          data_root=tmp_path / "synthetic", experiment_values={"max_trials": 1})
    assert result.runs[0].analysis is None
    assert not result.passed
    assert analysis_checks(result)[0]["passed"] is False
