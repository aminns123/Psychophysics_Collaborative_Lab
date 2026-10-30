"""Explicit per-experiment scenario modules.

Add the path to SCENARIO_MODULES when contributing an experiment. Each module
exports SCENARIOS: a tuple of SimulationScenario. No implicit folder scanning.
"""
from __future__ import annotations

import importlib
import json
from functools import partial

from .core import SimulationScenario

SCENARIO_MODULES = ()
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


def _teaching_analysis(experiment_id, observer, runs):
    """Check the selected procedure's actual analysis contract, not a target value.

    A bounded adaptive demonstration may legitimately have no complete condition.
    It must then retain the analyser's declared explanation; a completed adaptive
    run must produce its analysis. Fixed-level and no-analyser procedures must
    not acquire an inappropriate staircase estimate.
    """
    from simulations.registry import get_simulation

    model = get_simulation(experiment_id)
    checks = []
    for record in runs:
        config = json.loads((record.artifacts.run_directory / "experiment_config.json").read_text(encoding="utf-8"))
        values = config["normalised_experiment_values"]
        expected = model.analysis_factory is not None and values.get("contrast_method") != "constant_stimuli"
        actual = record.analysis is not None
        passed = actual == expected
        detail = f"expected analysis={expected}, actual={actual}"
        if expected and not actual and record.artifacts.status != "completed":
            unavailable_file = record.artifacts.run_directory / "analysis" / "threshold_unavailable.json"
            try:
                unavailable = json.loads(unavailable_file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError):
                unavailable = {}
            reason = unavailable.get("reason", "") if isinstance(unavailable, dict) else ""
            passed = (isinstance(unavailable, dict) and unavailable.get("data_kind") == "synthetic"
                      and isinstance(reason, str)
                      and any(message in reason for message in model.unavailable_analysis_messages))
            detail += f"; incomplete run requires a declared analyser explanation: {reason!r}"
        checks.append({"name": f"experiment-specific analysis expectation (seed {record.seed})",
                       "passed": passed, "detail": detail})
    return {"checks": checks}


def list_scenarios(experiment_id: str | None = None, *, include_historical=False) -> tuple[SimulationScenario, ...]:
    _load()
    from psychophysics_lab.experiments._internal.registry import list_experiments
    specs = list_experiments(include_historical=include_historical or experiment_id is not None)
    visible = {spec.id for spec in specs}
    extra = tuple(SimulationScenario("teaching_demo", spec.id, "Seeded pipeline demonstration; inspect observer metadata; no physical qualification",
                                    evaluate=partial(_teaching_analysis, spec.id))
                  for spec in specs if spec.supports_simulation and (experiment_id is None or spec.id == experiment_id))
    return tuple(_REGISTRY[key] for key in sorted(_REGISTRY)
                 if key[0] in visible and (experiment_id is None or key[0] == experiment_id)) + extra


def get_scenario(experiment_id: str, scenario_id: str) -> SimulationScenario:
    _load()
    if scenario_id == "teaching_demo":
        found = next((item for item in list_scenarios(experiment_id) if item.id == scenario_id), None)
        if found is not None:
            return found
    try:
        return _REGISTRY[(experiment_id, scenario_id)]
    except KeyError as exc:
        raise ValueError(f"No scenario {scenario_id!r} is registered for {experiment_id!r}.") from exc
