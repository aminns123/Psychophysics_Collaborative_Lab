"""Experiment-owned observer/acquisition/analysis registrations.

The CSF model is one implementation, not a universal simulation algorithm.
Future experiments register their own runtime and optional analyser without
changing the human acquisition framework.
"""
from dataclasses import dataclass
from typing import Callable

from psychophysics_lab.data.identifiers import validate_path_component
from psychophysics_lab.analysis.thresholds import analyse_thresholds

from .csf import CSFObserver, DEFAULT_VALUES, runtime


@dataclass(frozen=True)
class SimulationSpec:
    experiment_id: str
    observer_factory: Callable
    runtime_factory: Callable
    defaults: dict
    monitor_profile_id: str = "legacy_reference_display"
    analysis_factory: Callable | None = None
    unavailable_analysis_messages: tuple[str, ...] = ()


_REGISTRY: dict[str, SimulationSpec] = {}


def register_simulation(spec: SimulationSpec) -> None:
    if not isinstance(spec, SimulationSpec):
        raise TypeError("Expected SimulationSpec.")
    validate_path_component(spec.experiment_id, label="simulated experiment")
    if spec.experiment_id in _REGISTRY:
        raise ValueError("Duplicate experiment simulation.")
    if not callable(spec.observer_factory) or not callable(spec.runtime_factory):
        raise TypeError("Each simulation needs an observer factory and a runtime factory.")
    if spec.analysis_factory is not None and not callable(spec.analysis_factory):
        raise TypeError("Experiment analyser must be callable or None.")
    if not isinstance(spec.defaults, dict):
        raise TypeError("Simulation defaults must be a dictionary.")
    if any(not isinstance(message, str) or not message for message in spec.unavailable_analysis_messages):
        raise TypeError("Unavailable-analysis markers must be nonempty text.")
    _REGISTRY[spec.experiment_id] = spec


def get_simulation(experiment_id: str) -> SimulationSpec:
    if experiment_id not in _REGISTRY:
        from psychophysics_lab.experiments.registry import get_experiment
        experiment = get_experiment(experiment_id)
        if experiment.procedure and experiment.supports_simulation:
            return SimulationSpec(experiment_id, TeachingObserver, lambda *args: (lambda *runtime: None), experiment.field_defaults())
    try:
        return _REGISTRY[experiment_id]
    except KeyError as exc:
        raise ValueError(f"No experiment-specific observer registered for {experiment_id}.") from exc


def list_simulations() -> tuple[SimulationSpec, ...]:
    from psychophysics_lab.experiments.registry import list_experiments
    keys = set(_REGISTRY) | {spec.id for spec in list_experiments() if spec.supports_simulation}
    return tuple(get_simulation(key) for key in sorted(keys))


@dataclass(frozen=True)
class TeachingObserver:
    accuracy: float = .85

    def __post_init__(self):
        import math
        if isinstance(self.accuracy, bool) or not math.isfinite(self.accuracy) or not 0 <= self.accuracy <= 1:
            raise ValueError("Observer accuracy must be finite and between 0 and 1.")


register_simulation(SimulationSpec(
    "contrast_sensitivity", CSFObserver, runtime, DEFAULT_VALUES,
    analysis_factory=analyse_thresholds,
    unavailable_analysis_messages=("No reversal observations",),
))
