from __future__ import annotations

from .contrast_sensitivity import CSF_SPEC
from .spec import ExperimentSpec

_REGISTRY: dict[str, ExperimentSpec] = {
    CSF_SPEC.id: CSF_SPEC,
}


def list_experiments() -> tuple[ExperimentSpec, ...]:
    return tuple(_REGISTRY[key] for key in sorted(_REGISTRY))


def get_experiment(experiment_id: str) -> ExperimentSpec:
    try:
        return _REGISTRY[experiment_id]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"Unknown experiment {experiment_id!r}. Registered experiments: {known}") from exc


def register_experiment(spec: ExperimentSpec) -> None:
    """Small explicit registry hook for future experiments.

    The public-v1 repository intentionally does not implement automatic plugin
    discovery. A contributor adds a new ExperimentSpec explicitly.
    """
    if spec.id in _REGISTRY:
        raise ValueError(f"Experiment id already registered: {spec.id}")
    _REGISTRY[spec.id] = spec
