"""Experiment-specific simulation acceptance tests; no graphics or real participants."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from simulations.__main__ import main
from simulations.registry import SimulationSpec, get_simulation, register_simulation
from simulations.scenarios import (
    SimulationScenario, get_scenario, list_scenarios, register_scenario, run_scenario
)
from simulations.scenarios.run import ScenarioRun
from simulations.scaffold import scaffold_simulation
from psychophysics_lab.data.workspace import save_workspace_state
from psychophysics_lab.config.models import SetupRequest

ROOT = Path(__file__).resolve().parents[1]


def test_retired_scenarios_are_not_registered_but_extension_point_remains(capsys):
    # The old thesis-specific canned scenarios were retired. Researchers can
    # contribute scenarios for any registered experiment using the same API.
    assert not list_scenarios("contrast_sensitivity")
    assert main(["--list-scenarios"]) == 0
    assert "csf_baseline" not in capsys.readouterr().out
    with pytest.raises(ValueError, match="No scenario"):
        get_scenario("contrast_sensitivity", "csf_baseline")
    assert not list_scenarios("unknown_experiment")


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




