"""Declarative trial phases shared by authored experiments and legacy adapters.

A phase is either an explicitly timed presentation or a response window.  This
module specifies *intent*, not measured photon timing. Hardware presentation
must report software flip times and be qualified separately on each machine.
"""
from __future__ import annotations

from dataclasses import dataclass
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

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError("Phase name must be a nonempty word (underscores allowed).")
        if self.kind not in {"show", "response"}:
            raise ValueError("Phase kind must be 'show' or 'response'.")
        if self.slot is not None and (not isinstance(self.slot, str) or not self.slot.isidentifier()):
            raise ValueError("Phase slot must be a registered identifier or null for a blank stage.")
        if type(self.duration_ms) is not int or not 0 <= self.duration_ms <= 3_600_000:
            raise ValueError("Phase duration_ms must be an integer from 0 to 3600000.")
        if self.kind == "show" and self.duration_ms == 0:
            raise ValueError("A keyless show phase must have a positive duration; zero would stall.")

    def to_dict(self):
        return {"name": self.name, "kind": self.kind, "slot": self.slot,
                "duration_ms": self.duration_ms, "instructions": self.instructions}


@dataclass(frozen=True)
class TrialTimeline:
    phases: tuple[Phase, ...]

    def __post_init__(self):
        if not self.phases:
            raise ValueError("A trial timeline needs at least one phase.")
        names = [phase.name for phase in self.phases]
        if len(set(names)) != len(names):
            raise ValueError("Each phase name within one trial must be unique.")
        responses = [index for index, phase in enumerate(self.phases) if phase.kind == "response"]
        if responses != [len(self.phases) - 1]:
            raise ValueError("A trial must end in exactly one response phase.")

    def validate_slots(self, registered_slots):
        missing = {p.slot for p in self.phases if p.slot is not None} - set(registered_slots)
        if missing:
            raise ValueError(f"Timeline references undeclared stimulus slots: {sorted(missing)}")
        return self

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
