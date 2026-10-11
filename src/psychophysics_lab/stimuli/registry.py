"""Explicit, hardware-independent metadata for inspectable stimulus components."""
from dataclasses import dataclass
from ..data.identifiers import validate_path_component

@dataclass(frozen=True)
class StimulusSpec:
    id: str
    display_name: str
    description: str
    source_path: str

_REGISTRY = {}

def register_stimulus(spec: StimulusSpec) -> None:
    from pathlib import PurePosixPath
    validate_path_component(spec.id, label="stimulus")
    path = PurePosixPath(spec.source_path)
    if path.is_absolute() or ".." in path.parts or "\\" in spec.source_path or not spec.source_path.endswith(".py"):
        raise ValueError("Stimulus source must be a relative Python file.")
    if spec.id in _REGISTRY:
        raise ValueError(f"Stimulus already registered: {spec.id}")
    _REGISTRY[spec.id] = spec

def list_stimuli() -> tuple[StimulusSpec, ...]:
    from psychophysics_lab.experiments.contributions import load_contributions
    load_contributions()
    return tuple(_REGISTRY[key] for key in sorted(_REGISTRY))

register_stimulus(StimulusSpec("geometry_bar", "Geometry bar", "Physical and angular geometry diagnostic.", "src/psychophysics_lab/stimuli/geometry.py"))
register_stimulus(StimulusSpec("legacy_csf", "Reference CSF renderer", "Existing CSF scientific renderer and timing semantics.", "Events/stimuliC.py"))
