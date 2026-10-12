"""Experiment-specific simulation acceptance tests; no graphics or real participants."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from simulations.__main__ import main
from simulations.csf import CSFObserver
from simulations.registry import SimulationSpec, get_simulation, register_simulation
from simulations.scenarios import (
    SimulationScenario, get_scenario, list_scenarios, register_scenario, run_scenario
)
from simulations.scenarios.csf import evaluate_csf
from simulations.scenarios.run import ScenarioRun
from simulations.scaffold import scaffold_simulation
from psychophysics_lab.data.workspace import save_workspace_state
from psychophysics_lab.config.models import SetupRequest

ROOT = Path(__file__).resolve().parents[1]


def test_scenario_registry_lists_independent_experiment_cases(capsys):
    ids = {scenario.id for scenario in list_scenarios("contrast_sensitivity")}
    assert {"csf_baseline", "csf_short_censored", "csf_shifted_preference"} <= ids
    assert get_scenario("contrast_sensitivity", "csf_short_censored").expect_analysis is False
    assert main(["--list-scenarios"]) == 0
    assert "csf_baseline" in capsys.readouterr().out
    assert not list_scenarios("unknown_experiment")
    with pytest.raises(ValueError, match="No scenario"):
        get_scenario("unknown_experiment", "csf_baseline")


def test_scenario_definitions_fail_loudly_if_invalid():
    with pytest.raises(ValueError, match="nonnegative integer seed"):
        SimulationScenario("test", "contrast_sensitivity", "Test", seeds=(-1,))
    with pytest.raises(ValueError, match="Duplicate random seeds"):
        SimulationScenario("test", "contrast_sensitivity", "Test", seeds=(1, 1))
    with pytest.raises(ValueError, match="description"):
        SimulationScenario("test", "contrast_sensitivity", "")
    with pytest.raises(TypeError, match="evaluator"):
        SimulationScenario("test", "contrast_sensitivity", "Test", evaluate="not callable")


def test_other_experiments_can_register_other_observers_and_evaluators(monkeypatch):
    from simulations import registry as simulations_registry
    from simulations.scenarios import registry as scenarios_registry
    monkeypatch.setattr(simulations_registry, "_REGISTRY", dict(simulations_registry._REGISTRY))
    monkeypatch.setattr(scenarios_registry, "_REGISTRY", dict(scenarios_registry._REGISTRY))
    monkeypatch.setattr(scenarios_registry, "_loaded", True)

    class IntervalObserver:
        def simulation_parameters(self):
            return {"threshold_ms": 20}

    def event_adapter(*args):
        return lambda *runtime_args: None

    independent = SimulationSpec("interval_task", IntervalObserver, event_adapter, {}, analysis_factory=None)
    register_simulation(independent)
    assert get_simulation("interval_task") is independent
    checks = lambda observer, runs: {"model": "temporal-order", "threshold_ms": observer.simulation_parameters()["threshold_ms"]}
    case = SimulationScenario("interval_latency", "interval_task", "Temporal judgement test",
                              observer_parameters={}, seeds=(0,), evaluate=checks)
    register_scenario(case)
    assert get_scenario("interval_task", "interval_latency").evaluate(IntervalObserver(), ())["threshold_ms"] == 20
    assert independent.analysis_factory is None  # Never force CSF analysis on interval tasks.
    with pytest.raises(ValueError, match="Duplicate"):
        register_scenario(case)
    with pytest.raises(ValueError, match="Duplicate"):
        register_simulation(independent)


def test_csf_model_comparison_reports_bias_without_fake_pass_criteria():
    observer = CSFObserver(threshold=.1, preferred_condition=63, tuning_width_octaves=2)
    fake_analysis = SimpleNamespace(condition_thresholds=(
        SimpleNamespace(condition="63", threshold=.12),
        SimpleNamespace(condition="252", threshold=.22),
    ))
    observations = (
        ScenarioRun(3, SimpleNamespace(status="completed", accepted_trials=100), fake_analysis),
    )
    evaluation = evaluate_csf(observer, observations)
    result = evaluation["runs"][0]
    assert result["conditions"][0]["model_midpoint_contrast"] == pytest.approx(.1)
    assert result["conditions"][1]["model_midpoint_contrast"] > .1
    assert result["sampled_preference_direction_matches"] is True
    assert "not a strict numerical recovery guarantee" in evaluation["comparison_interpretation"]


def test_full_named_scenario_uses_shared_data_root_and_generates_report(tmp_path, monkeypatch):
    import builtins
    original = builtins.__import__
    def no_hardware(name, *args, **kwargs):
        if name.split(".")[0] in {"pyglet", "winsound", "libC"}:
            raise AssertionError("Hardware imported during headless scenario: " + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_hardware)

    root = tmp_path / "local_psychophysics_data"
    root.mkdir()
    human = root / "H001"
    human.mkdir()
    human_file = human / "keep.tsv"
    human_file.write_bytes(b"human response: preserve")
    request = SetupRequest("H001", "new", "contrast_sensitivity", "legacy_reference_display", {})
    save_workspace_state(root, request, status="completed")
    original_prefs = (root / "psycolab_data_config.json").read_bytes()

    report = run_scenario(experiment_id="contrast_sensitivity", scenario_id="csf_baseline",
                          data_root=root, repo_root=ROOT)
    assert report.passed, [entry for entry in report.checks if not entry["passed"]]
    assert report.report_file.is_relative_to(root / "simulation_reports")
    saved = json.loads(report.report_file.read_text())
    assert saved["data_kind"] == "synthetic"
    assert saved["passed"] is True
    assert saved["experiment_id"] == "contrast_sensitivity"
    assert saved["experiment_evaluation"]["runs"][0]["conditions"]
    assert saved["runs"][0]["relative_run_directory"].startswith("synthetic_123/")
    assert len(report.runs) == 1
    assert report.runs[0].analysis is not None
    assert human_file.read_bytes() == b"human response: preserve"
    assert (root / "psycolab_data_config.json").read_bytes() == original_prefs


def test_censored_case_is_not_given_an_invented_threshold(tmp_path):
    result = run_scenario(experiment_id="contrast_sensitivity", scenario_id="csf_short_censored",
                          data_root=tmp_path / "local_psychophysics_data", repo_root=ROOT)
    assert result.passed
    assert len(result.runs) == 1
    assert result.runs[0].analysis is None
    assert result.runs[0].artifacts.accepted_trials == 1
    report = json.loads(result.report_file.read_text())
    assert report["runs"][0]["relative_analysis_summary"] is None
    assert report["experiment_evaluation"]["runs"][0]["conditions"] == []


def test_simulation_scaffold_is_only_two_files_and_never_overwrites(tmp_path):
    (tmp_path / "simulations" / "scenarios").mkdir(parents=True)
    paths = scaffold_simulation(tmp_path, "new_spatial_task")
    before = [path.read_bytes() for path in paths]
    assert len(paths) == 2
    assert paths[0].name == paths[1].name == "new_spatial_task.py"
    for path in paths:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    with pytest.raises(ValueError, match="new source files"):
        scaffold_simulation(tmp_path, "new_spatial_task")
    assert [path.read_bytes() for path in paths] == before
    for name in ("../escape", "class", "SomeName", "invalid-name", "", "a/b"):
        with pytest.raises(ValueError):
            scaffold_simulation(tmp_path, name)
