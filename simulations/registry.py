"""Register one observer/driver per experiment, never in the human TUI."""
from dataclasses import dataclass
from typing import Callable
from .csf import CSFObserver, DEFAULT_VALUES, runtime

@dataclass(frozen=True)
class SimulationSpec:
    experiment_id: str
    observer_factory: Callable
    runtime_factory: Callable
    defaults: dict
    monitor_profile_id: str = "legacy_reference_display"

_REGISTRY = {}

def register_simulation(spec):
    if spec.experiment_id in _REGISTRY:
        raise ValueError("Duplicate experiment simulation.")
    _REGISTRY[spec.experiment_id] = spec

def get_simulation(experiment_id):
    try:
        return _REGISTRY[experiment_id]
    except KeyError as exc:
        raise ValueError(f"No experiment-specific observer registered for {experiment_id}.") from exc

register_simulation(SimulationSpec("contrast_sensitivity", CSFObserver, runtime, DEFAULT_VALUES))
