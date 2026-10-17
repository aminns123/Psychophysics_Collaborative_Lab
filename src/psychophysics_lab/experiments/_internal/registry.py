from __future__ import annotations

from psychophysics_lab._reference_csf.experiment_definition import CSF_SPEC
from psychophysics_lab.experiments._internal.spec import ExperimentSpec

_REGISTRY: dict[str, ExperimentSpec] = {
    CSF_SPEC.id: CSF_SPEC,
}


def list_experiments(*, include_historical=False) -> tuple[ExperimentSpec, ...]:
    from psychophysics_lab.experiments._internal.contributions import load_contributions
    load_contributions()
    # Adding a development protocol must not change the established launch
    # default. Keep the reference first, then normal and blocked experiments.
    return tuple(_REGISTRY[key] for key in sorted((key for key, spec in _REGISTRY.items() if include_historical or not spec.historical), key=lambda key:
        (key != CSF_SPEC.id, bool(_REGISTRY[key].acquisition_block_reason), key)))


def get_experiment(experiment_id: str) -> ExperimentSpec:
    from psychophysics_lab.experiments._internal.contributions import load_contributions
    load_contributions()
    try:
        return _REGISTRY[experiment_id]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"Unknown experiment {experiment_id!r}. Registered experiments: {known}") from exc


def register_experiment(spec: ExperimentSpec) -> None:
    """Small explicit registry hook for future experiments.

    Local experiments export SPEC and are discovered automatically. This hook
    remains for internal loaders and explicit programmatic registration.
    """
    if spec.id in _REGISTRY:
        raise ValueError(f"Experiment id already registered: {spec.id}")
    _REGISTRY[spec.id] = spec
