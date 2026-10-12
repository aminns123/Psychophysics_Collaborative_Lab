"""Resolve author-declared simulated settings from *real* experiment fields.

Human experiment controls are the source of truth. The virtual observer
contributes extra, model-only controls; they never leak into human setup.
"""
from __future__ import annotations
from dataclasses import asdict, is_dataclass

from psychophysics_lab.experiments.registry import get_experiment
from .registry import get_simulation


def effective_experiment_values(scenario):
    model = get_simulation(scenario.experiment_id)
    experiment = get_experiment(scenario.experiment_id)
    return experiment.normalise_values(dict(model.defaults) | dict(scenario.experiment_values))


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
