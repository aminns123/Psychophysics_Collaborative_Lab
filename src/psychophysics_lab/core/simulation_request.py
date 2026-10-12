"""Display-independent handoff between Textual and the synthetic test pipeline.

This module intentionally imports neither Textual nor simulation runners. The
TUI returns an immutable request; the outer application executes it only after
Textual has closed, preserving the graphics/acquisition lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SimulationLaunchRequest:
    experiment_id: str
    scenario_id: str
    data_root: Path
    seeds: tuple[int, ...]
    observer_parameters: dict[str, Any] = field(default_factory=dict)
    experiment_values: dict[str, Any] = field(default_factory=dict)
    monitor_profile_id: str | None = None

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.scenario_id:
            raise ValueError("Select both an experiment and a simulation scenario.")
        if not isinstance(self.data_root, Path):
            raise TypeError("Simulation data root must be a Path.")
        if not self.seeds or len(self.seeds) > 128 or any(type(x) is not int or x < 0 for x in self.seeds):
            raise ValueError("Enter 1–128 valid nonnegative integer seeds.")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Simulation seeds must be unique.")
        if not isinstance(self.observer_parameters, dict) or not isinstance(self.experiment_values, dict):
            raise TypeError("Simulation parameter overrides must be dictionaries.")
        if self.monitor_profile_id is not None and (not isinstance(self.monitor_profile_id, str) or not self.monitor_profile_id):
            raise ValueError("Monitor profile selection must be a nonempty profile ID.")


def parse_seeds(text: str) -> tuple[int, ...]:
    parts = [part.strip() for part in text.split(",")]
    if not parts or any(not part or not part.isdecimal() for part in parts):
        raise ValueError("Seeds must be comma-separated nonnegative integers, e.g. 11,12,13.")
    return tuple(int(part) for part in parts)


def parse_parameter(text: str, example: Any) -> Any:
    """Parse with the type of the scenario's declared parameter.

    Unlike permissive float-to-int conversion, this rejects type changes and
    nonfinite numeric values before any run or data directory is created.
    """
    raw = text.strip()
    if not raw:
        raise ValueError("A simulation parameter cannot be empty.")
    if isinstance(example, bool):
        if raw.lower() not in {"true", "false"}:
            raise ValueError("Boolean parameter must be true or false.")
        return raw.lower() == "true"
    if isinstance(example, int):
        if not (raw.isdecimal() or (raw.startswith("-") and raw[1:].isdecimal())):
            raise ValueError("Integer parameter must be a whole number.")
        return int(raw)
    if isinstance(example, float):
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("Simulation numeric values must be finite.")
        return value
    if isinstance(example, str):
        return raw
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Parameter must be valid JSON.") from exc
    if type(value) is not type(example):
        raise ValueError("Parameter must retain the scenario's declared JSON type.")
    return value
