"""Explicit, hardware-independent metadata for inspectable stimulus components."""
from dataclasses import dataclass
from typing import Callable
from ..data.identifiers import validate_path_component

@dataclass(frozen=True)
class StimulusSpec:
    id: str
    display_name: str
    description: str
    source_path: str
    parameters: tuple = ()
    default_config: str = ""
    family: str = ""
    render: Callable | None = None
    calibration_requirements: tuple[str, ...] = ()
    extent_parameter: str = "size_deg"
    frequency_parameter: str = "spatial_frequency_cpd"
    validator: Callable | None = None
    source_dependencies: tuple[str, ...] = ()
    spatial_frequencies: Callable | None = None

    def validate_parameters(self, values):
        if not isinstance(values, dict):
            raise ValueError(f"{self.id}: parameters must be a JSON object.")
        fields = {item.key: item for item in self.parameters}
        if values.keys() != fields.keys():
            raise ValueError(f"{self.id}: missing parameters {sorted(fields.keys()-values.keys())}; unknown parameters {sorted(values.keys()-fields.keys())}.")
        result = {}
        for key, item in fields.items():
            raw = values[key]
            if raw is None or raw == "" or (item.kind in {"float", "int"} and (isinstance(raw, bool) or not isinstance(raw, (int, float)))):
                raise ValueError(f"{self.id}.{key}: supply a {item.kind} value ({item.units}).")
            result[key] = item.coerce(raw)
        if self.validator is not None:
            self.validator(result)
        return result

_REGISTRY = {}

def register_stimulus(spec: StimulusSpec) -> None:
    from pathlib import PurePosixPath
    validate_path_component(spec.id, label="stimulus")
    if any(key not in {"geometry", "luminance", "timing"} for key in spec.calibration_requirements):
        raise ValueError("Unknown stimulus calibration requirement.")
    if len({item.key for item in spec.parameters}) != len(spec.parameters):
        raise ValueError("Stimulus parameter names must be unique.")
    path = PurePosixPath(spec.source_path)
    if path.is_absolute() or ".." in path.parts or "\\" in spec.source_path or not spec.source_path.endswith(".py"):
        raise ValueError("Stimulus source must be a relative Python file.")
    for dependency in spec.source_dependencies:
        path = PurePosixPath(dependency)
        if path.is_absolute() or ".." in path.parts or "\\" in dependency or not dependency.endswith(".py"):
            raise ValueError("Stimulus dependency must be a relative Python file.")
    if spec.id in _REGISTRY:
        raise ValueError(f"Stimulus already registered: {spec.id}")
    _REGISTRY[spec.id] = spec


def get_stimulus(identity):
    list_stimuli()
    if identity not in _REGISTRY:
        raise ValueError(f"Unknown stimulus {identity!r}; add a LibraryStimulus class in stimulus_library.py.")
    return _REGISTRY[identity]

def list_stimuli() -> tuple[StimulusSpec, ...]:
    from dataclasses import replace
    from .._reference_csf.experiment_definition import CSF_SPEC
    if not _REGISTRY["legacy_csf"].parameters:
        # A single researcher-facing definition owns the reference shader.
        # Keep the original ID and CSF-specific validator and human gate.
        from ..stimulus_library import CSFGrating
        _REGISTRY["legacy_csf"] = replace(
            CSFGrating.SPEC,
            parameters=tuple(f for f in CSF_SPEC.fields if f.section == "Stimulus conditions"),
            validator=_validate_csf_parameters,
        )
    from psychophysics_lab.experiments._internal.contributions import load_contributions
    load_contributions()
    return tuple(_REGISTRY[key] for key in sorted(_REGISTRY))


def _validate_csf_parameters(values):
    from .._reference_csf.experiment_definition import resolved_condition_frequencies
    conditions = resolved_condition_frequencies(values['condition_values'], values['condition_unit'])
    if len(conditions) != values['number_conditions']:
        raise ValueError("number_conditions must match the number of condition_values.")

register_stimulus(StimulusSpec("geometry_bar", "Geometry bar", "Calibration diagnostic configured on Geometry; not an experiment stimulus.", "src/psychophysics_lab/stimuli/geometry.py", default_config="configs/stimuli/geometry_bar.json"))
register_stimulus(StimulusSpec("legacy_csf", "Reference CSF renderer", "Existing CSF scientific renderer and timing semantics.", "src/psychophysics_lab/stimulus_library.py"))
