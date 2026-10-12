"""Explicit per-experiment scenario modules.

Add the path to SCENARIO_MODULES when contributing an experiment. Each module
exports SCENARIOS: a tuple of SimulationScenario. No implicit folder scanning.
"""
from __future__ import annotations

import importlib

from .core import SimulationScenario

SCENARIO_MODULES = ("simulations.scenarios.csf",)
_REGISTRY: dict[tuple[str, str], SimulationScenario] = {}
_loaded = False


def register_scenario(scenario: SimulationScenario) -> None:
    if not isinstance(scenario, SimulationScenario):
        raise TypeError("Expected a SimulationScenario.")
    key = (scenario.experiment_id, scenario.id)
    if key in _REGISTRY:
        raise ValueError(f"Duplicate simulation scenario: {key!r}")
    _REGISTRY[key] = scenario


def _load() -> None:
    global _loaded
    if _loaded:
        return
    before = dict(_REGISTRY)
    try:
        for module_name in SCENARIO_MODULES:
            module = importlib.import_module(module_name)
            for scenario in module.SCENARIOS:
                register_scenario(scenario)
    except Exception:
        _REGISTRY.clear()
        _REGISTRY.update(before)
        raise
    _loaded = True


def list_scenarios(experiment_id: str | None = None) -> tuple[SimulationScenario, ...]:
    _load()
    return tuple(_REGISTRY[key] for key in sorted(_REGISTRY)
                 if experiment_id is None or key[0] == experiment_id)


def get_scenario(experiment_id: str, scenario_id: str) -> SimulationScenario:
    _load()
    try:
        return _REGISTRY[(experiment_id, scenario_id)]
    except KeyError as exc:
        raise ValueError(f"No scenario {scenario_id!r} is registered for {experiment_id!r}.") from exc
