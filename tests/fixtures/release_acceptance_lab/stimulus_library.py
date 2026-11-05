"""Disposable independent diamond: hard L1 boundary on digital grey .5."""
import numpy as np
from psychophysics_lab.stimulus_library import LibraryStimulus
from psychophysics_lab.researcher import ConfigField, StimulusSpec


class AuditDiamond(LibraryStimulus):
    PARAMETERS = (
        ConfigField("size_deg", "Patch extent", "float", 2., minimum=1., maximum=4., units="degrees"),
        ConfigField("radius_deg", "Major semiaxis", "float", .3, minimum=.1, maximum=.45, units="degrees"),
        ConfigField("ratio", "Minor/major semiaxis ratio", "float", .5, minimum=.25, maximum=.8),
        ConfigField("axis", "Major axis", "choice", "horizontal", choices=("horizontal", "vertical")),
        ConfigField("intensity", "Interior intensity", "float", .7, minimum=.5, maximum=1., units="digital command"),
    )

    def render(p, x_deg, y_deg):
        a, b = p["radius_deg"], p["radius_deg"] * p["ratio"]
        if p["axis"] == "vertical":
            a, b = b, a
        return np.where(abs(x_deg) / a + abs(y_deg) / b <= 1., p["intensity"], .5)

    SPEC = StimulusSpec(id="releaseaudit__diamond", display_name="Disposable diamond",
        description=__doc__, source_path="stimulus_library.py", parameters=PARAMETERS,
        default_config="", family="audit_diamond", render=render,
        calibration_requirements=("geometry",))
