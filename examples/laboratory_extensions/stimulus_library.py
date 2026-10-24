"""One laboratory-owned stimulus library; uses the normal PsyCoLab renderer."""
import numpy as np
from psychophysics_lab.stimulus_library import LibraryStimulus
from psychophysics_lab.researcher import ConfigField, StimulusSpec

class LaboratoryLine(LibraryStimulus):
    """A laboratory-owned line; edit PARAMETERS, render and SPEC here."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch size", "float", 5.0,
                    units="degrees", minimum=4.0, maximum=8.0),
        ConfigField("offset_deg", "Horizontal position", "float", 1.0,
                    units="degrees", minimum=-2.0, maximum=2.0),
        ConfigField("line_width_deg", "Line width", "float", 0.15,
                    units="degrees", minimum=0.03, maximum=0.5),
        ConfigField("line_length_deg", "Line length", "float", 1.2,
                    units="degrees", minimum=0.2, maximum=2.0),
        ConfigField("intensity", "Digital line intensity", "float", 1.0,
                    units="0 to 1 command", minimum=0.5, maximum=1.0),
    )


    # EDIT 2: DRAW THE STIMULUS
    def render(parameters, x_deg, y_deg):
        """Return a 2D array: 0 = black, 0.5 = grey, 1 = white."""
        inside_line = (
            (np.abs(x_deg - parameters["offset_deg"]) < parameters["line_width_deg"] / 2)
            & (np.abs(y_deg) < parameters["line_length_deg"] / 2)
        )
        image = np.where(inside_line, parameters["intensity"], 0.5)
        return image


    # FRAMEWORK DECLARATION: namespace-prefixed ID and root-relative source.
    # The stimulus family is how a compatible experiment recognises this shape.
    SPEC = StimulusSpec(
        id="demolab__line",
        display_name="Example: White Line",
        description="Beginner visual stimulus: a line on a grey background.",
        source_path="stimulus_library.py",
        parameters=PARAMETERS,
        default_config="",
        family="simple_line",
        render=render,
        calibration_requirements=("geometry",),
    )
