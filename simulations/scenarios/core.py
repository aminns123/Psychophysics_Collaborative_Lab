"""Experiment-specific synthetic scenarios: contracts, not a universal observer.

Each experiment authors its own scenario and evaluation policy. No acquisition
data are written by this module; the runner uses PsyCoLab's canonical pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from psychophysics_lab.data.identifiers import validate_path_component


@dataclass(frozen=True)
class SimulationScenario:
    id: str
    experiment_id: str
    description: str
    observer_parameters: Mapping[str, Any] = field(default_factory=dict)
    experiment_values: Mapping[str, Any] = field(default_factory=dict)
    seeds: tuple[int, ...] = (123,)
    expect_analysis: bool | None = None
    evaluate: Callable[..., Mapping[str, Any]] | None = None
    validator: Callable[..., Any] | None = None

    def __post_init__(self) -> None:
        validate_path_component(self.id, label="scenario")
        validate_path_component(self.experiment_id, label="scenario experiment")
        if not self.description.strip():
            raise ValueError("A simulation scenario needs a description.")
        if not self.seeds or any(type(seed) is not int or seed < 0 for seed in self.seeds):
            raise ValueError("A scenario needs at least one nonnegative integer seed.")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Duplicate random seeds in scenario.")
        if not isinstance(self.observer_parameters, Mapping) or not isinstance(self.experiment_values, Mapping):
            raise TypeError("Scenario observer/experiment parameters must be mappings.")
        if self.expect_analysis is not None and type(self.expect_analysis) is not bool:
            raise TypeError("expect_analysis must be True, False or None.")
        if self.evaluate is not None and not callable(self.evaluate):
            raise TypeError("Scenario evaluator must be callable.")
        if self.validator is not None and not callable(self.validator):
            raise TypeError("Scenario validator must be callable.")
