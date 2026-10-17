"""Explicit algorithm factories; an experiment owns selection and configuration.

Factories may expose experiment-specific interfaces. The legacy_staircase
capability promises AdaptiveRun's select/respond/snapshot contract; other
procedures use their own interface and cannot enter the legacy CSF adapter.
"""
from dataclasses import dataclass
from typing import Callable, Mapping, Any, Protocol
from ..data.identifiers import validate_path_component
from .staircase import AdaptiveRun


class StaircaseAlgorithm(Protocol):
    def select(self, choose): ...
    def respond(self, identity, correct, update_value): ...
    def snapshot(self) -> dict: ...


@dataclass(frozen=True)
class AdaptiveAlgorithm:
    id: str
    description: str
    factory: Callable[..., Any]
    controls: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdaptiveSelection:
    algorithm_id: str
    controls: tuple[str, ...] = ()
    step_calculator: str | None = None
    step_parameterization: str | None = None

    def validate(self, field_keys):
        algorithm = get_algorithm(self.algorithm_id)
        if len(set(self.controls)) != len(self.controls):
            raise ValueError("Adaptive control keys must be unique.")
        if set(self.controls) - set(algorithm.controls):
            raise ValueError("Experiment declares controls unsupported by its adaptive algorithm.")
        if set(self.controls) - set(field_keys):
            raise ValueError("Adaptive controls must be declared experiment fields.")
        if self.step_calculator is not None:
            required = {"n_down", "n_up", "logUNIT_UP", "logUNIT_DW"}
            if self.step_calculator != "garcia_perez_1998" or not required <= set(self.controls):
                raise ValueError("Unsupported step calculator or missing step controls.")


_REGISTRY: dict[str, AdaptiveAlgorithm] = {}


def register_algorithm(algorithm: AdaptiveAlgorithm) -> None:
    validate_path_component(algorithm.id, label="adaptive algorithm")
    if not callable(algorithm.factory):
        raise TypeError("Adaptive algorithm factory must be callable.")
    if algorithm.id in _REGISTRY:
        raise ValueError(f"Adaptive algorithm already registered: {algorithm.id}")
    _REGISTRY[algorithm.id] = algorithm


def get_algorithm(identity: str) -> AdaptiveAlgorithm:
    # A researcher can import one experiment directly, before catalogue loading.
    # Load this built-in mechanism lazily without importing other experiments.
    if identity == "legacy_flanker_log" and identity not in _REGISTRY:
        from .legacy_flanker import SPEC
        register_algorithm(SPEC)
    try:
        return _REGISTRY[identity]
    except KeyError as exc:
        raise ValueError(f"Unknown adaptive algorithm: {identity}") from exc


def list_algorithms() -> tuple[AdaptiveAlgorithm, ...]:
    return tuple(_REGISTRY[key] for key in sorted(_REGISTRY))


register_algorithm(AdaptiveAlgorithm(
    "consecutive_up_down", "Legacy consecutive correct/incorrect response staircase",
    AdaptiveRun, ("down_factor", "up_factor", "n_down", "n_up", "logUNIT_UP", "logUNIT_DW", "initial_one_down_limit", "staircases_per_condition", "reversal_termination", "max_trials"),
    ("legacy_staircase",),
))
