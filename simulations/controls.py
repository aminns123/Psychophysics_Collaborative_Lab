"""Resolve author-declared simulated settings from *real* experiment fields.

Human experiment controls are the source of truth. The virtual observer
contributes extra, model-only controls; they never leak into human setup.
"""
from __future__ import annotations
from dataclasses import asdict, is_dataclass

from psychophysics_lab.experiments._internal.registry import get_experiment
from .registry import get_simulation


def effective_experiment_values(scenario):
    model = get_simulation(scenario.experiment_id)
    experiment = get_experiment(scenario.experiment_id)
    values = dict(model.defaults) | dict(scenario.experiment_values)
    # A draft form must display required study choices as empty fields. The
    # execution boundary still normalises the complete settings before any run.
    if any(value is None for value in values.values()):
        fields = {field.key:field for field in experiment.fields}
        if set(values)-set(fields):
            raise ValueError("Scenario contains unknown experiment settings.")
        return {key:fields[key].coerce(value) if value is not None else None
                for key,value in values.items()}
    return experiment.normalise_values(values)


def effective_observer_values(scenario):
    factory = get_simulation(scenario.experiment_id).observer_factory
    observer = factory(**dict(scenario.observer_parameters))
    if is_dataclass(observer) and not isinstance(observer, type):
        return asdict(observer)
    params = getattr(observer, "simulation_parameters", None)
    if callable(params):
        values = params()
        if isinstance(values, dict):
            return dict(values)
    # Explicitly declared parameters remain available to non-dataclass observers.
    return dict(scenario.observer_parameters)
