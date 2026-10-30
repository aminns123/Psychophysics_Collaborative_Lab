"""Independent laboratory annulus, using the installed numerical renderer."""
import numpy as np
from psychophysics_lab.stimulus_library import LibraryStimulus
from psychophysics_lab.researcher import ConfigField, StimulusSpec

class LaboratoryAnnulus(LibraryStimulus):
    PARAMETERS = (
        ConfigField('size_deg', 'Annulus patch extent', 'float', 3., minimum=2., maximum=5., units='degrees'),
        ConfigField('radius_deg', 'Annulus radius', 'float', .3, minimum=.1, maximum=.6, units='degrees'),
        ConfigField('rim_deg', 'Annulus rim thickness', 'float', .05, minimum=.01, maximum=.1, units='degrees'),
        ConfigField('intensity', 'Annulus digital intensity', 'float', .7, minimum=.5, maximum=1., units='0 to 1 command'),
    )

    def render(parameters, x_deg, y_deg):
        radius = np.hypot(x_deg, y_deg)
        return np.where(np.abs(radius-parameters['radius_deg']) <= parameters['rim_deg']/2,
                        parameters['intensity'], .5)

    SPEC = StimulusSpec(id='auditlab__annulus', display_name='Laboratory annulus',
        description='A finite ring on digital grey 0.5; not calibrated optical contrast.',
        source_path='stimulus_library.py', parameters=PARAMETERS, default_config='',
        family='audit_annulus', render=render, calibration_requirements=('geometry',))
