"""Reusable fixation cross. A drawing module, not an experiment phase.

EDIT PARAMETERS or render() to change the geometry. The framework controls
where and when it appears; 0–1 intensities are DIGITAL commands only.
"""
import numpy as np
from psychophysics_lab.researcher import ConfigField, StimulusSpec

PARAMETERS = (
    ConfigField("size_deg", "Patch diameter", "float", 0.8, units="degrees", minimum=0.2, maximum=3),
    ConfigField("arm_length_deg", "Cross arm length", "float", 0.35, units="degrees", minimum=0.05, maximum=1),
    ConfigField("width_deg", "Cross line width", "float", 0.06, units="degrees", minimum=0.01, maximum=0.3),
    ConfigField("intensity", "Digital brightness", "float", 1.0, units="0–1", minimum=0, maximum=1),
)

def render(parameters, x_deg, y_deg):
    """Draw a cross around the centre of its degree-coordinate patch."""
    half_arm = parameters["arm_length_deg"] / 2
    half_width = parameters["width_deg"] / 2
    horizontal = (np.abs(y_deg) <= half_width) & (np.abs(x_deg) <= half_arm)
    vertical = (np.abs(x_deg) <= half_width) & (np.abs(y_deg) <= half_arm)
    return np.where(horizontal | vertical, parameters["intensity"], 0.5)

SPEC = StimulusSpec(
    "fixation_cross", "Fixation cross", "Reusable + drawn in degrees.",
    "src/psychophysics_lab/stimuli/fixation_cross.py",
    parameters=PARAMETERS, default_config="configs/stimuli/fixation_cross.json",
    family="fixation", render=render, calibration_requirements=("geometry",),
)
