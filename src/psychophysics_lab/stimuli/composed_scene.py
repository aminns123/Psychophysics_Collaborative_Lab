"""Internal registered adapter. Researcher drawings live in stimulus_library.py."""
import json
from ..experiments.spec import ConfigField
from .registry import StimulusSpec
from ..stimulus_library import Scene, fixation


def scene(parameters):
    return Scene.from_dict(json.loads(parameters["scene_json"]))


def validate(parameters):
    scene(parameters).parameters(parameters["size_deg"])


def render(parameters, x_deg, y_deg):
    return scene(parameters).render(x_deg, y_deg)


def frequencies(parameters):
    return tuple(d.parameters["spatial_frequency_cpd"] for d in scene(parameters).drawings
                 if "spatial_frequency_cpd" in d.parameters)


PARAMETERS = (
    ConfigField("size_deg", "Scene aperture", "float", 12., units="degrees", minimum=.01, maximum=90),
    ConfigField("scene_json", "Scene recipe", "text", json.dumps(Scene(fixation()).to_dict())),
)
SPEC = StimulusSpec("composed_scene", "Composed scene", "Ordered drawings from the shared stimulus library.",
    "src/psychophysics_lab/stimuli/composed_scene.py", parameters=PARAMETERS,
    default_config="configs/stimuli/composed_scene.json", family="scene", render=render,
    validator=validate, calibration_requirements=("geometry", "luminance"),
    source_dependencies=("src/psychophysics_lab/stimulus_library.py",),
    spatial_frequencies=frequencies)
