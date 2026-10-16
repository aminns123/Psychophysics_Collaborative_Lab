"""EXAMPLE STIMULUS: a single bright vertical line.

START HERE: This file has exactly TWO scientific sections to edit:
    PARAMETERS defines the values you may change.
    render() defines what the stimulus looks like.

The associated JSON file holds the default values. PsyCoLab supplies
x_deg/y_deg (a pixel grid in degrees), presents the result, handles responses,
and records trials. Grayscale values are DIGITAL COMMANDS, not photometry.
"""
import numpy as np
from psychophysics_lab.researcher import ConfigField, StimulusSpec


# EDIT 1: ADJUSTABLE STIMULUS PARAMETERS
PARAMETERS = (
    ConfigField("size_deg", "Patch size", "float", 5.0,
                units="degrees", minimum=4.0, maximum=8.0),
    ConfigField("offset_deg", "Horizontal position", "float", 0.0,
                units="degrees", minimum=-2.0, maximum=2.0),
    ConfigField("line_width_deg", "Line width", "float", 0.15,
                units="degrees", minimum=0.03, maximum=0.5),
    ConfigField("line_length_deg", "Line length", "float", 1.2,
                units="degrees", minimum=0.2, maximum=2.0),
    ConfigField("intensity", "Digital line intensity", "float", 1.0,
                units="0–1 command", minimum=0.5, maximum=1.0),
)


# EDIT 2: DRAW THE STIMULUS
def render(parameters, x_deg, y_deg):
    """Return a 2D array: 0 = black, 0.5 = grey, 1 = white."""
    inside_line = (
        (np.abs(x_deg - parameters["offset_deg"]) < parameters["line_width_deg"] / 2)
        & (np.abs(y_deg) < parameters["line_length_deg"] / 2)
    )
    return np.where(inside_line, parameters["intensity"], 0.5)


# FRAMEWORK DECLARATION: generated files already have the correct ID/paths.
# The stimulus family is how a compatible experiment recognises this shape.
SPEC = StimulusSpec(
    id="new_probe_vertical_line",
    display_name="Example: White Line",
    description="Beginner visual stimulus: a line on a grey background.",
    source_path="src/psychophysics_lab/stimuli/new_probe_vertical_line.py",
    parameters=PARAMETERS,
    default_config="configs/stimuli/new_probe_vertical_line.json",
    family="simple_line",
    render=render,
    calibration_requirements=("geometry",),
)
