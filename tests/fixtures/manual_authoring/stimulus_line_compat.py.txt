"""A WHITE VERTICAL LINE — the smallest independent reusable probe.

Only edit PARAMETERS and render() if you want a different appearance.
Experiments position this patch using Stimulus('probe', x_deg=..., y_deg=...).
Do not put trial order, responses or saving code in a stimulus definition.
"""
import numpy as np
from psychophysics_lab.researcher import ConfigField, StimulusSpec

PARAMETERS = (
    ConfigField("size_deg", "Patch diameter", "float", 1.0, units="degrees", minimum=0.3, maximum=5),
    ConfigField("length_deg", "Line length", "float", 0.6, units="degrees", minimum=0.1, maximum=2),
    ConfigField("width_deg", "Line width", "float", 0.08, units="degrees", minimum=0.02, maximum=0.5),
    ConfigField("intensity", "Digital brightness", "float", 1.0, units="0–1", minimum=0, maximum=1),
)

def render(parameters, x_deg, y_deg):
    """Return digital greyscale, one command value per pixel."""
    inside = ((np.abs(x_deg) <= parameters["width_deg"] / 2)
              & (np.abs(y_deg) <= parameters["length_deg"] / 2))
    return np.where(inside, parameters["intensity"], 0.5)

SPEC = StimulusSpec(
    "vertical_line_probe", "Vertical white line", "Reusable visual-angle line.",
    "src/psychophysics_lab/stimuli/vertical_line_probe.py",
    parameters=PARAMETERS, default_config="configs/stimuli/vertical_line_probe.json",
    family="line", render=render, calibration_requirements=("geometry",),
)
