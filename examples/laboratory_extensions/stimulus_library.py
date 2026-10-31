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


class LearningLine(LibraryStimulus):
    """Lesson 3's own line: finite edge coverage on grey; not optical calibration."""
    PARAMETERS = (
        ConfigField('size_deg','Patch extent','float',5.,units='degrees',minimum=4.,maximum=8.),
        ConfigField('length_deg','Line length','float',.8,units='degrees',minimum=.2,maximum=1.5),
        ConfigField('width_deg','Line width','float',.08,units='degrees',minimum=.02,maximum=.2),
        ConfigField('edge_deg','Edge transition','float',.01,units='degrees',minimum=.002,maximum=.02),
        ConfigField('intensity','Digital line command','float',.7,units='0 to 1 command',minimum=.5,maximum=1.),
    )

    def validate(parameters):
        if parameters['edge_deg'] > parameters['width_deg'] / 2:
            raise ValueError('Edge transition must not exceed half the line width.')

    def render(parameters, x_deg, y_deg):
        # TRY CHANGING: the mask deliberately, then re-preview every condition.
        coverage=np.clip((parameters['width_deg']/2-np.abs(x_deg))/parameters['edge_deg']+.5,0,1)
        coverage*=np.abs(y_deg)<parameters['length_deg']/2
        return .5+(parameters['intensity']-.5)*coverage

    SPEC = StimulusSpec(id='demolab__learning_line',display_name='Learning: soft-edged line',
        description=__doc__,source_path='stimulus_library.py',parameters=PARAMETERS,
        default_config='',family='learning_line',render=render,validator=validate,
        calibration_requirements=('geometry',))
