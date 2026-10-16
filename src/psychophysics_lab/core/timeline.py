"""Declarative trial phases shared by authored experiments and legacy adapters.

A phase is either an explicitly timed presentation or a response window.  This
module specifies *intent*, not measured photon timing. Hardware presentation
must report software flip times and be qualified separately on each machine.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Phase:
    name: str
    kind: str  # "show" or "response"
    slot: str | None = None  # None means an empty/blank stage; no stimulus module needed
    duration_ms: int = 0  # response: 0 waits indefinitely; show: strictly positive
    instructions: str = ""
    stimuli: tuple = ()
    actions: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("Phase name must be a nonempty word (underscores allowed).")
        if self.kind not in {"show", "response"}:
            raise ValueError("Phase kind must be 'show' or 'response'.")
        if self.slot is not None and (not isinstance(self.slot, str) or not self.slot.isidentifier()):
            raise ValueError("Phase slot must be a registered identifier or null for a blank stage.")
        if isinstance(self.duration_ms, str) and self.duration_ms.isidentifier():
            pass  # Resolved from validated experiment values before execution.
        elif type(self.duration_ms) is not int or not 0 <= self.duration_ms <= 3_600_000:
            raise ValueError("Phase duration_ms must be an integer from 0 to 3600000.")
        if not isinstance(self.instructions, str):
            raise ValueError("Instructions must be text.")
        object.__setattr__(self, "stimuli", tuple(self.stimuli))
        object.__setattr__(self, "actions", tuple(self.actions))
        if any(not isinstance(item, Stimulus) for item in self.stimuli):
            raise TypeError("Show stimuli must contain Stimulus placements.")
        if self.slot is not None and self.stimuli:
            raise ValueError("Choose slot or stimuli, not both.")
        if any(not isinstance(a, str) or not a for a in self.actions):
            raise ValueError("Response actions must be named meanings.")
        if self.kind == "show" and self.duration_ms == 0:
            raise ValueError("A keyless show phase must have a positive duration; zero would stall.")

    @property
    def placements(self):
        return self.stimuli or ((Stimulus(self.slot),) if self.slot else ())

    def to_dict(self):
        result = {"name": self.name, "kind": self.kind, "slot": self.slot,
                "duration_ms": self.duration_ms, "instructions": self.instructions}
        if self.stimuli:
            result["stimuli"] = [item.to_dict() for item in self.stimuli]
        if self.actions:
            result["actions"] = list(self.actions)
        return result


@dataclass(frozen=True)
class TrialTimeline:
    phases: tuple[Phase, ...]

    def __post_init__(self):
        object.__setattr__(self, "phases", tuple(self.phases))
        if any(not isinstance(p, (Phase, RecordState, UpdateState, UpdateAdaptive)) for p in self.phases):
            raise TypeError("Timeline accepts only declared trial actions.")
        if not self.phases:
            raise ValueError("A trial timeline needs at least one phase.")
        names = [phase.name for phase in self.phases]
        if len(set(names)) != len(names):
            raise ValueError("Each phase name within one trial must be unique.")
        responses = [index for index, phase in enumerate(self.phases) if phase.kind == "response"]
        if len(responses) != 1:
            raise ValueError("A trial requires exactly one response phase.")
        response_index = responses[0]
        if any(isinstance(p, Phase) for p in self.phases[response_index + 1:]):
            raise ValueError("Only non-rendering actions may follow the response phase.")
        if any(isinstance(p, UpdateAdaptive) for p in self.phases[:response_index]):
            raise ValueError("Adaptive updates require a preceding response.")

    def validate_slots(self, registered_slots):
        missing = {s.slot for p in self.phases if isinstance(p, Phase)
                   for s in p.placements} - set(registered_slots)
        if missing:
            raise ValueError(f"Timeline references undeclared stimulus slots: {sorted(missing)}")
        return self

    def resolve(self, values):
        phases = []
        for phase in self.phases:
            if isinstance(phase, Phase) and isinstance(phase.duration_ms, str):
                if phase.duration_ms not in values:
                    raise ValueError(f"Unknown timeline timing field: {phase.duration_ms}")
                phase = replace(phase, duration_ms=values[phase.duration_ms])
                if type(phase.duration_ms) is not int:
                    raise ValueError("Resolved duration must be integer milliseconds.")
            phases.append(phase)
        return TrialTimeline(tuple(phases))

    def to_dict(self):
        return {"schema_version": 1, "phases": [p.to_dict() for p in self.phases]}


def load_timeline(path: Path, *, timings: Mapping[str, int] = (), slots=()) -> TrialTimeline:
    """Load editable chronological JSON with timing keys resolved from experiment fields.

    ``duration_ms`` may be an integer or ``{"field": "fixation_ms"}``. Field
    resolution is explicit: no expressions, hidden file access or Python eval.
    """
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or set(document) != {"schema_version", "phases"} or document["schema_version"] != 1:
        raise ValueError("Timeline JSON must have schema_version=1 and phases only.")
    if not isinstance(document["phases"], list):
        raise ValueError("Timeline phases must be a JSON array.")
    phases = []
    for raw in document["phases"]:
        if not isinstance(raw, dict) or set(raw) - {"name", "kind", "slot", "duration_ms", "instructions"}:
            raise ValueError("Timeline phase has invalid or unknown fields.")
        duration = raw.get("duration_ms", 0)
        if isinstance(duration, dict):
            if set(duration) != {"field"} or duration["field"] not in timings:
                raise ValueError(f"Unknown timeline timing field: {duration!r}")
            duration = timings[duration["field"]]
        phases.append(Phase(name=raw["name"], kind=raw["kind"],
                            slot=raw.get("slot"), duration_ms=duration,
                            instructions=raw.get("instructions", "")))
    return TrialTimeline(tuple(phases)).validate_slots(slots)


def simulated_phases(timeline: TrialTimeline):
    """Deterministic intended timeline for simulation; does not wait or claim photons."""
    elapsed = 0
    events = []
    for phase in timeline.phases:
        events.append({**phase.to_dict(), "planned_onset_ms": elapsed,
                       "planned_offset_ms": elapsed + phase.duration_ms if phase.kind == "show" else None,
                       "timing_basis": "simulated schedule, not measured presentation"})
        if phase.kind == "show":
            elapsed += phase.duration_ms
    return events

# Public action declarations extend this same timeline; they are not another runner.
from collections.abc import Mapping as ABCMapping
from types import MappingProxyType
from typing import Callable


def scientific_snapshot(value):
    """Detach finite JSON scientific values; reject lossy/arbitrary objects."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, ABCMapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("Scientific state keys must be strings.")
        return {key: scientific_snapshot(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [scientific_snapshot(item) for item in value]
    raise ValueError("Scientific state must contain only finite JSON values.")


def immutable_state(value):
    """Read-only detached callback input; nested lists become tuples."""
    value = scientific_snapshot(value)
    def freeze(item):
        if isinstance(item, dict):
            return MappingProxyType({key: freeze(v) for key, v in item.items()})
        if isinstance(item, list):
            return tuple(freeze(v) for v in item)
        return item
    return freeze(value)


def _name(name):
    if not isinstance(name, str) or not name or not name.replace("_", "").isalnum():
        raise ValueError("Action name must be a nonempty word (underscores allowed).")


def _function_name(function):
    if not callable(function):
        raise TypeError("Scientific update must be callable.")
    return function.__module__ + "." + function.__qualname__


@dataclass(frozen=True)
class Stimulus:
    """One registered slot, positioned in degrees from screen centre.

    Patches are opaque and drawn in written order. Per-slot parameters are
    validated by the selected StimulusSpec, supplied through play_trial.
    """
    slot: str
    x_deg: float = 0.
    y_deg: float = 0.

    def __post_init__(self):
        if not isinstance(self.slot, str) or not self.slot.isidentifier():
            raise ValueError("Stimulus requires a declared slot identifier.")
        if any(type(v) not in (int, float) or not math.isfinite(v)
               for v in (self.x_deg, self.y_deg)):
            raise ValueError("Stimulus positions must be finite degrees.")

    def to_dict(self):
        return {"slot": self.slot, "x_deg": self.x_deg, "y_deg": self.y_deg}


def Show(name, *, slot=None, duration, instructions="", stimuli=()):
    """A timed visual stage. No slots means blank (or instruction text)."""
    return Phase(name, "show", slot, duration, instructions, tuple(stimuli))


def CollectResponse(*, actions, timeout=0, name="answer", slot=None, instructions=""):
    """One response using the experiment's declared meanings and TUI key mapping."""
    return Phase(name, "response", slot, timeout, instructions, (), tuple(actions))


@dataclass(frozen=True)
class RecordState:
    name: str
    fields: tuple[str, ...] = ()
    kind = "record_state"
    slot = None
    duration_ms = 0

    def __post_init__(self):
        _name(self.name)
        if any(not isinstance(key, str) or not key.isidentifier() for key in self.fields):
            raise ValueError("Recorded field names must be identifiers.")
        object.__setattr__(self, "fields", tuple(self.fields))

    def to_dict(self):
        return {"name": self.name, "kind": self.kind, "fields": list(self.fields)}


@dataclass(frozen=True)
class UpdateState:
    function: Callable
    name: str = "update_state"
    kind = "update_state"
    slot = None
    duration_ms = 0

    def __post_init__(self):
        _name(self.name)
        _function_name(self.function)

    def to_dict(self):
        return {"name": self.name, "kind": self.kind, "function": _function_name(self.function)}


@dataclass(frozen=True)
class UpdateAdaptive:
    algorithm: object
    identity: object
    update_value: Callable
    state_key: str = "adaptive_value"
    name: str = "update_adaptive"
    kind = "update_adaptive"
    slot = None
    duration_ms = 0

    def __post_init__(self):
        _name(self.name)
        _function_name(self.update_value)
        scientific_snapshot(self.identity)
        if not isinstance(self.state_key, str) or not self.state_key.isidentifier():
            raise ValueError("Adaptive state_key must be an identifier.")

    def to_dict(self):
        return {"name": self.name, "kind": self.kind, "identity": self.identity,
                "state_key": self.state_key, "update_value": _function_name(self.update_value)}
