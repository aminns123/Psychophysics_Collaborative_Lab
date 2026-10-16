"""EDIT SCIENCE HERE: a Gaussian-windowed sinusoid in visual-angle coordinates.

The framework supplies x/y in degrees, handles display geometry and collects keys.
Digital contrast is a command modulation, not a claim of calibrated optical contrast.
"""
import numpy as np
from psychophysics_lab.researcher import ConfigField, StimulusSpec

# EDIT PARAMETERS: names, units and limits are the only validation schema.
PARAMETERS = (
    ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., units="cycles/degree", minimum=.05, maximum=30),
    ConfigField("orientation_deg", "Orientation", "float", 30., units="degrees", minimum=-90, maximum=90),
    ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=20),
    ConfigField("contrast", "Digital Michelson modulation", "float", .2, units="fraction", minimum=0, maximum=1),
    ConfigField("phase_deg", "Phase", "float", 0., units="degrees", minimum=0, maximum=360),
)


def render(parameters, x_deg, y_deg):
    """EDIT APPEARANCE: return grayscale commands in [0,1], one per grid pixel."""
    angle       = np.deg2rad(parameters["orientation_deg"])
    coordinate  = x_deg * np.cos(angle) + y_deg * np.sin(angle)
    carrier     = np.cos(2 * np.pi * parameters["spatial_frequency_cpd"] * coordinate + np.deg2rad(parameters["phase_deg"]))
    sigma       = parameters["size_deg"] / 6
    envelope    = np.exp(-(x_deg*x_deg + y_deg*y_deg) / (2*sigma*sigma))
    return .5 + .5 * parameters["contrast"] * envelope * carrier


SPEC = StimulusSpec("probe_white_line", "Teaching Gabor", "Gaussian-windowed grating; degrees and digital contrast.",
    "src/psychophysics_lab/stimuli/probe_white_line.py", parameters=PARAMETERS,
    default_config="configs/stimuli/probe_white_line.json", family="orientation_patch", render=render,
    calibration_requirements=("geometry",))
