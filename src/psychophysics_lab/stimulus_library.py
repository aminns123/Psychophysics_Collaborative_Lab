"""PsyCoLab: ONE file where each stimulus is ONE self-contained class.

Copy a LibraryStimulus subclass in this file; edit only the copied class:
PARAMETERS (science/settings), render() (pixels), SPEC (ID/description).
New classes register automatically. They need no generator, separate
stimulus module, JSON defaults file, or edits in another class/table.

Experiments are separate .py files; they control trial timing, locations,
responses, adaptation and optional beep sounds. All grayscale values 0â€“1
are digital commands, not calibrated luminance.

Scene() and convenience constructors below are optional pre-existing LEGO
pieces, imported from framework internals. Never edit a shared renderer or
registration list to add your own class.
"""
import json
import numpy as np
from psychophysics_lab.experiments._internal.spec import ConfigField
from .stimuli.registry import StimulusSpec
from .core.scene_primitives import (
    Drawing, Scene, fixation, line, rectangle, square, ellipse, annulus,
    gaussian_dot, grating, gabor,
)


class LibraryStimulus:
    """Marker for complete registered definitions inside this ONE file.

    Subclass with PARAMETERS, render and SPEC; the registry discovers new
    classes without another Python adapter or contributions.py edit.
    """


# ----------------------------------------------------------------------------
# SIMPLE COMPLETE STIMULI â€” copy one class; no other code needs changing.
# The Scene convenience functions remain available above via an import.
# ----------------------------------------------------------------------------

class LinePatch(LibraryStimulus):
    """A line at arbitrary orientation (0Â° = vertical)."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 2., units="degrees", minimum=.1, maximum=45),
        ConfigField("length_deg", "Line length", "float", 1., units="degrees", minimum=.01, maximum=10),
        ConfigField("width_deg", "Line thickness", "float", .08, units="degrees", minimum=.001, maximum=2),
        ConfigField("orientation_deg", "Orientation", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        angle = np.deg2rad(parameters["orientation_deg"])
        u = x_deg*np.cos(angle) + y_deg*np.sin(angle)
        v = -x_deg*np.sin(angle) + y_deg*np.cos(angle)
        inside = (np.abs(u) <= parameters["width_deg"]/2) & (np.abs(v) <= parameters["length_deg"]/2)
        image = np.where(inside, parameters["intensity"], .5)
        return image

    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": max(p["size_deg"], abs(np.cos(np.deg2rad(p["orientation_deg"]))) * p["length_deg"] + abs(np.sin(np.deg2rad(p["orientation_deg"]))) * p["width_deg"], abs(np.sin(np.deg2rad(p["orientation_deg"]))) * p["length_deg"] + abs(np.cos(np.deg2rad(p["orientation_deg"]))) * p["width_deg"])}

    @staticmethod
    def visible(p, x, y, steps):
        return LinePatch.render(p | {"intensity": 1.0}, x, y) > .5

    SPEC = StimulusSpec(
        id="oriented_line", display_name="Oriented line",
        description="An oriented filled line, specified in degrees.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="line", render=render,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry",),
    )


class SquarePatch(LibraryStimulus):
    """A filled square centred on the stimulus origin."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 3., units="degrees", minimum=.1, maximum=45),
        ConfigField("side_deg", "Square side", "float", 1., units="degrees", minimum=.01, maximum=20),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        half = parameters["side_deg"]/2
        inside = (np.abs(x_deg) <= half) & (np.abs(y_deg) <= half)
        image = np.where(inside, parameters["intensity"], .5)
        return image

    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": max(p["size_deg"], p["side_deg"])}

    @staticmethod
    def visible(p, x, y, steps):
        return SquarePatch.render(p | {"intensity": 1.0}, x, y) > .5

    SPEC = StimulusSpec(
        id="square_patch", display_name="Square",
        description="A filled square with a digital background of 0.5.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry",),
    )


class RectanglePatch(LibraryStimulus):
    """A filled rectangle; size is the overall display patch diameter."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 3., units="degrees", minimum=.1, maximum=45),
        ConfigField("width_deg", "Rectangle width", "float", 1., units="degrees", minimum=.01, maximum=20),
        ConfigField("height_deg", "Rectangle height", "float", 2., units="degrees", minimum=.01, maximum=20),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        inside = ((np.abs(x_deg) <= parameters["width_deg"]/2)
                  & (np.abs(y_deg) <= parameters["height_deg"]/2))
        image = np.where(inside, parameters["intensity"], .5)
        return image

    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": max(p["size_deg"], p["width_deg"], p["height_deg"])}

    @staticmethod
    def visible(p, x, y, steps):
        return RectanglePatch.render(p | {"intensity": 1.0}, x, y) > .5

    SPEC = StimulusSpec(
        id="rectangle_patch", display_name="Rectangle",
        description="A filled width-by-height rectangle.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry",),
    )


class EllipsePatch(LibraryStimulus):
    """A filled ellipse defined by the two semi-axes, not the full diameters."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=60),
        ConfigField("radius_x_deg", "Horizontal semi-axis", "float", 2., units="degrees", minimum=.01, maximum=30),
        ConfigField("radius_y_deg", "Vertical semi-axis", "float", 1., units="degrees", minimum=.01, maximum=30),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        r2 = (x_deg/parameters["radius_x_deg"])**2 + (y_deg/parameters["radius_y_deg"])**2
        image = np.where(r2 <= 1., parameters["intensity"], .5)
        return image

    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": max(p["size_deg"], 2*p["radius_x_deg"], 2*p["radius_y_deg"])}

    @staticmethod
    def visible(p, x, y, steps):
        return EllipsePatch.render(p | {"intensity": 1.0}, x, y) > .5

    SPEC = StimulusSpec(
        id="ellipse_patch", display_name="Filled ellipse",
        description="A filled ellipse with semi-axes in degrees.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry",),
    )


class AnnulusPatch(LibraryStimulus):
    """Elliptical annulus with an inner-to-outer semi-axis ratio."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=60),
        ConfigField("radius_x_deg", "Horizontal semi-axis", "float", 2., units="degrees", minimum=.01, maximum=30),
        ConfigField("radius_y_deg", "Vertical semi-axis", "float", 1., units="degrees", minimum=.01, maximum=30),
        ConfigField("inner_ratio", "Inner-to-outer radius ratio", "float", .85, minimum=0, maximum=.99),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        r2 = (x_deg/parameters["radius_x_deg"])**2 + (y_deg/parameters["radius_y_deg"])**2
        inside = (r2 <= 1.) & (r2 >= parameters["inner_ratio"]**2)
        image = np.where(inside, parameters["intensity"], .5)
        return image

    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": max(p["size_deg"], 2*p["radius_x_deg"], 2*p["radius_y_deg"])}

    @staticmethod
    def visible(p, x, y, steps):
        return AnnulusPatch.render(p | {"intensity": 1.0}, x, y) > .5

    SPEC = StimulusSpec(
        id="annulus_patch", display_name="Elliptical annulus",
        description="An elliptical ring with a fractional inner semi-axis.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry",),
    )


class GaussianDot(LibraryStimulus):
    """A Gaussian dot, smoothly blended with its background."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 2., units="degrees", minimum=.1, maximum=45),
        ConfigField("sigma_deg", "Gaussian standard deviation", "float", .2, units="degrees", minimum=.001, maximum=10),
        ConfigField("intensity", "Peak digital brightness", "float", 1., units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        sigma = parameters["sigma_deg"]
        r2 = x_deg*x_deg + y_deg*y_deg
        envelope = np.where(r2 <= (4*sigma)**2, np.exp(-r2/(2*sigma*sigma)), 0.)
        image = .5 + (parameters["intensity"]-.5)*envelope
        return image

    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": max(p["size_deg"], 8*p["sigma_deg"])}

    @staticmethod
    def visible(p, x, y, steps):
        return GaussianDot.render(p | {"intensity": 1.0}, x, y) > .5

    SPEC = StimulusSpec(
        id="gaussian_dot", display_name="Gaussian dot",
        description="A Gaussian dot truncated at four standard deviations.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry",),
    )


class SinusoidalGrating(LibraryStimulus):
    """A rectangular-patch sinusoid, distinct from the reference CSF shader."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=45),
        ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., units="cycles/degree", minimum=.01, maximum=50),
        ConfigField("orientation_deg", "Carrier orientation", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("phase_deg", "Phase", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("contrast", "Digital modulation", "float", .2, units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        theta = np.deg2rad(parameters["orientation_deg"])
        coordinate = x_deg*np.cos(theta) + y_deg*np.sin(theta)
        wave = np.sin(2*np.pi*parameters["spatial_frequency_cpd"]*coordinate
                      + np.deg2rad(parameters["phase_deg"]))
        inside = (np.abs(x_deg) <= parameters["size_deg"]/2) & (np.abs(y_deg) <= parameters["size_deg"]/2)
        image = np.where(inside, .5 + .5*parameters["contrast"]*wave, .5)
        return image

    SPEC = StimulusSpec(
        id="sine_grating", display_name="Sinusoidal grating",
        description="NumPy sinusoid in cpd; NOT the physical CSF reference GLSL.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="grating", render=render,
        calibration_requirements=("geometry",),
    )



def _validate_gabor_aperture(parameters):
    """Only opt-in edge fades constrain the interior plateau in degrees."""
    if (parameters["envelope_mode"] == "edge_fade"
            and parameters["fade_width_deg"] > parameters["size_deg"] / 2):
        raise ValueError(
            "Edge fade width must be at most half the square aperture width. "
            "Reduce fade_width_deg or enlarge size_deg; digital contrasts are not rescaled."
        )


def _explicit_square_grating_envelope(parameters, x_deg, y_deg):
    """One spatial envelope used by both Gabor classes in opt-in edge modes.

    The square aperture has exact width size_deg in calibrated visual degrees.
    The carrier's angular frequency, orientation, phase and contrast remain
    independent of the edge envelope. No off-aperture pixels are modulated.
    """
    mode = parameters.get("envelope_mode", "legacy_gaussian")
    half = parameters["size_deg"] / 2
    edge = np.maximum(np.abs(x_deg), np.abs(y_deg))
    if mode == "flat_hard_edge":
        return np.asarray(edge <= half, dtype=float)
    if mode == "edge_fade":
        _validate_gabor_aperture(parameters)
        fade = parameters["fade_width_deg"]
        if fade == 0:
            return np.asarray(edge <= half, dtype=float)
        # Full modulation within half-fade degrees; raised cosine falls to
        # exactly zero at the requested square support edge.
        progress = np.clip((half - edge) / fade, 0, 1)
        return (1 - np.cos(np.pi * progress)) / 2
    raise ValueError(f"Unsupported explicit grating envelope: {mode!r}")


class GaborPatch(LibraryStimulus):
    """A Gaussian-windowed grating in degrees, independent of CSF's GLSL."""
    PARAMETERS = (
        ConfigField("size_deg", "Square aperture width", "float", 5., units="degrees", minimum=.1, maximum=45, help_text="For flat or fade edge modes, exactly the square aperture width in visual degrees. Legacy Gaussian mode retains its original bounded patch."),
        ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., units="cycles/degree", minimum=.01, maximum=50),
        ConfigField("sigma_deg", "Gaussian SD", "float", .8, units="degrees", minimum=.001, maximum=20, help_text="Used only in legacy_gaussian mode; flat and edge-fade modes use the explicit square aperture instead."),
        ConfigField(
            "envelope_mode", "Envelope / edge behavior", "choice", "legacy_gaussian",
            choices=("legacy_gaussian", "flat_hard_edge", "edge_fade"),
            help_text="Legacy Gaussian preserves historic data. Flat hard edge gives full carrier modulation inside the square aperture; edge fade uses a raised cosine. Hard edges add high spatial frequencies: the carrier Nyquist check alone does not qualify edge sampling on the actual display."
        ),
        ConfigField(
            "fade_width_deg", "Edge fade width", "float", .1, units="degrees",
            minimum=0, maximum=10,
            help_text="Used only in edge_fade mode: inward fade distance at each square edge, at most half the aperture width."
        ),
        ConfigField("orientation_deg", "Carrier orientation", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("phase_deg", "Phase", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("contrast", "Digital modulation", "float", .2, units="0â€“1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        theta = np.deg2rad(parameters["orientation_deg"])
        coordinate = x_deg*np.cos(theta) + y_deg*np.sin(theta)
        carrier = np.cos(2*np.pi*parameters["spatial_frequency_cpd"]*coordinate
                         + np.deg2rad(parameters["phase_deg"]))
        r2 = x_deg*x_deg + y_deg*y_deg
        sigma = parameters["sigma_deg"]
        if parameters.get("envelope_mode", "legacy_gaussian") == "legacy_gaussian":
            envelope = np.exp(-r2/(2*sigma*sigma))
        else:
            envelope = _explicit_square_grating_envelope(parameters, x_deg, y_deg)
        inside = (np.abs(x_deg) <= parameters["size_deg"]/2) & (np.abs(y_deg) <= parameters["size_deg"]/2)
        image = np.where(inside, .5 + .5*parameters["contrast"]*envelope*carrier, .5)
        return image

    SPEC = StimulusSpec(
        id="gabor_patch", display_name="Gabor patch",
        description="Cosine grating with selectable legacy Gaussian, full-aperture hard edge or raised-cosine edge fade.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="gabor", render=render,
        calibration_requirements=("geometry",),
        validator=_validate_gabor_aperture,
        legacy_parameter_defaults={"envelope_mode": "legacy_gaussian", "fade_width_deg": 0.1},
    )


class FixationCross(LibraryStimulus):
    """Registered fixation_cross; edit PARAMETERS, render and SPEC here."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 0.8, units="degrees", minimum=0.2, maximum=3),
        ConfigField("arm_length_deg", "Cross arm length", "float", 0.35, units="degrees", minimum=0.05, maximum=1),
        ConfigField("width_deg", "Cross line width", "float", 0.06, units="degrees", minimum=0.01, maximum=0.3),
        ConfigField("intensity", "Digital brightness", "float", 1.0, units="0â€“1", minimum=0, maximum=1),
    )
    
    def render(parameters, x_deg, y_deg):
        """Draw a cross around the centre of its degree-coordinate patch."""
        half_arm    = parameters["arm_length_deg"] / 2
        half_width  = parameters["width_deg"] / 2
        horizontal  = (np.abs(y_deg) <= half_width) & (np.abs(x_deg) <= half_arm)
        vertical    = (np.abs(x_deg) <= half_width) & (np.abs(y_deg) <= half_arm)
        image = np.where(horizontal | vertical, parameters["intensity"], 0.5)
        return image
    
    SPEC = StimulusSpec(
        "fixation_cross", "Fixation cross", "Reusable + drawn in degrees.",
        "src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, default_config="configs/stimuli/fixation_cross.json",
        family="fixation", render=render, calibration_requirements=("geometry",),
    )


class VerticalLineProbe(LibraryStimulus):
    """Registered legacy-compatible vertical_line_probe; edit PARAMETERS, render and SPEC here."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 1.0, units="degrees", minimum=0.3, maximum=5),
        ConfigField("length_deg", "Line length", "float", 0.6, units="degrees", minimum=0.1, maximum=2),
        ConfigField("width_deg", "Line width", "float", 0.08, units="degrees", minimum=0.02, maximum=0.5),
        ConfigField("intensity", "Digital brightness", "float", 1.0, units="0â€“1", minimum=0, maximum=1),
    )
    
    def render(parameters, x_deg, y_deg):
        """Return digital greyscale, one command value per pixel."""
        inside = ((np.abs(x_deg) <= parameters["width_deg"] / 2)
                  & (np.abs(y_deg) <= parameters["length_deg"] / 2))
        image = np.where(inside, parameters["intensity"], 0.5)
        return image
    
    SPEC = StimulusSpec(
        "vertical_line_probe", "Vertical white line", "Reusable visual-angle line.",
        "src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, default_config="configs/stimuli/vertical_line_probe.json",
        family="line", render=render, calibration_requirements=("geometry",),
    )


class ExampleWhiteLine(LibraryStimulus):
    """Registered legacy-compatible example_stimulus; edit PARAMETERS, render and SPEC here."""
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
                    units="0â€“1 command", minimum=0.5, maximum=1.0),
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
    
    
    # FRAMEWORK DECLARATION: generated files already have the correct ID/paths.
    # The stimulus family is how a compatible experiment recognises this shape.
    SPEC = StimulusSpec(
        id="example_stimulus",
        display_name="Example: White Line",
        description="Beginner visual stimulus: a line on a grey background.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS,
        default_config="configs/stimuli/example_stimulus.json",
        family="simple_line",
        render=render,
        calibration_requirements=("geometry",),
    )


class TeachingGabor(LibraryStimulus):
    """Registered legacy-compatible teaching_gabor; edit PARAMETERS, render and SPEC here."""
    PARAMETERS = (
        ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., units="cycles/degree", minimum=.05, maximum=30),
        ConfigField("orientation_deg", "Orientation", "float", 30., units="degrees", minimum=-90, maximum=90),
        ConfigField("size_deg", "Square aperture width / legacy scale", "float", 5., units="degrees", minimum=.1, maximum=20, help_text="Flat/edge-fade modes use this exact square aperture width. Legacy mode preserves the historic Gaussian sigma = size_deg/6."),
        ConfigField("contrast", "Digital Michelson modulation", "float", .2, units="fraction", minimum=0, maximum=1),
        ConfigField("phase_deg", "Phase", "float", 0., units="degrees", minimum=0, maximum=360),
        ConfigField(
            "envelope_mode", "Envelope / edge behavior", "choice", "legacy_gaussian",
            choices=("legacy_gaussian", "flat_hard_edge", "edge_fade"),
            help_text="Legacy Gaussian is the exact historic teaching appearance. Flat hard edge means full modulation in the chosen square aperture and exact background outside. Hard edges add high spatial frequencies: the carrier Nyquist check alone does not qualify edge sampling on the actual display."
        ),
        ConfigField(
            "fade_width_deg", "Edge fade width", "float", .1, units="degrees",
            minimum=0, maximum=10,
            help_text="Only active for edge_fade; width of the raised-cosine taper on each side of the square aperture."
        ),
    )
    
    
    def render(parameters, x_deg, y_deg):
        """EDIT APPEARANCE: return grayscale commands in [0,1], one per grid pixel."""
        angle       = np.deg2rad(parameters["orientation_deg"])
        coordinate  = x_deg * np.cos(angle) + y_deg * np.sin(angle)
        carrier     = np.cos(2 * np.pi * parameters["spatial_frequency_cpd"] * coordinate + np.deg2rad(parameters["phase_deg"]))
        sigma       = parameters["size_deg"] / 6
        if parameters.get("envelope_mode", "legacy_gaussian") == "legacy_gaussian":
            # Exact historical teaching raster: do not introduce a mask.
            envelope = np.exp(-(x_deg*x_deg + y_deg*y_deg) / (2*sigma*sigma))
        else:
            envelope = _explicit_square_grating_envelope(parameters, x_deg, y_deg)
        image = .5 + .5 * parameters["contrast"] * envelope * carrier
        return image
    
    
    SPEC = StimulusSpec("teaching_gabor", "Teaching Gabor", "Gaussian-windowed grating; degrees and digital contrast.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS,
        default_config="configs/stimuli/teaching_gabor.json", family="orientation_patch", render=render,
        calibration_requirements=("geometry",),
        validator=_validate_gabor_aperture,
        legacy_parameter_defaults={"envelope_mode": "legacy_gaussian", "fade_width_deg": 0.1})


class ComposedScene(LibraryStimulus):
    """A registered adapter from a Scene recipe to the existing raster backend.

    Compose fixtures, lines, gratings and elliptical surrounds in experiment
    procedures. Task choices stay in the experiment; reusable primitive equations live in
    core/scene_primitives.py so composition and individual shapes share maths.
    """

    @staticmethod
    def scene(parameters):
        return Scene.from_dict(json.loads(parameters["scene_json"]))

    @staticmethod
    def validate(parameters):
        ComposedScene.scene(parameters).parameters(parameters["size_deg"])

    @staticmethod
    def render(parameters, x_deg, y_deg):
        image = ComposedScene.scene(parameters).render(x_deg, y_deg)
        return image

    @staticmethod
    def frequencies(parameters):
        return tuple(d.parameters["spatial_frequency_cpd"]
                     for d in ComposedScene.scene(parameters).drawings
                     if "spatial_frequency_cpd" in d.parameters)

    PARAMETERS = (
        ConfigField("size_deg", "Scene aperture", "float", 12., units="degrees", minimum=.01, maximum=90),
        ConfigField("scene_json", "Scene recipe", "text", json.dumps(Scene(fixation()).to_dict())),
    )
    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": p["size_deg"]}

    @staticmethod
    def visible(p, x, y, steps):
        return all(np.any(drawing._layer(x, y)[1])
                   for drawing in ComposedScene.scene(p).drawings)

    SPEC = StimulusSpec("composed_scene", "Composed scene",
        "Ordered drawings from the shared stimulus library.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS,
        default_config="configs/stimuli/composed_scene.json", family="scene",
        render=render.__func__, validator=validate.__func__,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry", "luminance"),
        source_dependencies=("src/psychophysics_lab/stimulus_library.py",),
        spatial_frequencies=frequencies.__func__)


class ResearcherVerticalLine(LibraryStimulus):
    """Researcher's original vertical-line stimulus, migrated without altering its maths.

    Keep these PARAMETERS/render defaults stable for experiment provenance.
    Existing Ready fingerprints require fresh test and Ready after migration.
    """
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
                    units="0â€“1 command", minimum=0.5, maximum=1.0),
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
    
    
    # FRAMEWORK DECLARATION: generated files already have the correct ID/paths.
    # The stimulus family is how a compatible experiment recognises this shape.
    @staticmethod
    def geometry(p):
        return {"raster_extent_deg": max(p["size_deg"], 2*abs(p["offset_deg"])+p["line_width_deg"], p["line_length_deg"])}

    @staticmethod
    def visible(p, x, y, steps):
        return ResearcherVerticalLine.render(p | {"intensity": 1.0}, x, y) > .5

    SPEC = StimulusSpec(
        id="new_probe_vertical_line",
        display_name="Example: White Line",
        description="Beginner visual stimulus: a line on a grey background.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS,
        default_config="configs/stimuli/new_probe_vertical_line.json",
        family="simple_line",
        render=render,
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry",),
    )



class ContrastSensitivityGrating(LibraryStimulus):
    """Gaussian-windowed grating with a finite, smoothly tapered support.

    Sigma is the standard deviation of the *Gaussian*, not the grating radius.
    Within (cutoff_sigmas - 1)*sigma its profile is the original Gaussian.
    A raised-cosine taper removes the remaining tail, reaching exactly zero
    modulation at cutoff_sigmas*sigma. The surrounding command is precisely
    background, including within the square floating-point texture.

    The square raster is an implementation extent, not the grating boundary.
    Contrast is digital peak-to-peak modulation, not measured optical contrast.
    """
    PARAMETERS = (
        ConfigField("size_deg", "Minimum raster extent", "float", 8., minimum=.1, maximum=30, units="degrees"),
        ConfigField("sigma_deg", "Gaussian standard deviation", "float", 1., minimum=.001, maximum=5, units="degrees"),
        ConfigField("cutoff_sigmas", "Smooth grating cutoff radius", "float", 3., minimum=2., maximum=5.,
                    units="multiples of sigma",
                    help_text="Gaussian unchanged to (cutoff - 1) sigma, smoothly fades to exact background at cutoff sigma."),
        ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., minimum=.01, maximum=64, units="cycles/degree"),
        ConfigField("contrast", "Digital peak-to-peak modulation", "float", .1, minimum=0, maximum=1, units='digital peak-to-peak modulation'),
        ConfigField("background", "Digital background", "float", .5, minimum=0, maximum=1, units='digital intensity, 0 to 1'),
    )

    @staticmethod
    def validate(parameters):
        if parameters["contrast"] > 2 * min(parameters["background"], 1-parameters["background"]):
            raise ValueError("Requested grating modulation exceeds the available digital range; no silent clipping.")
    def render(parameters, x_deg, y_deg):
        sigma = parameters["sigma_deg"]
        radius_in_sigmas = np.hypot(x_deg, y_deg) / sigma
        # Existing researcher scripts may call render() directly with the
        # original parameter dictionary; preserve the three-sigma default.
        cutoff = parameters.get("cutoff_sigmas", 3.)
        gaussian = np.exp(-.5 * radius_in_sigmas**2)

        # C1-continuous at both ends of the last-sigma taper. No square or
        # discontinuous hard crop that could add high-frequency edge artifacts.
        progress = np.clip(radius_in_sigmas - (cutoff - 1.), 0., 1.)
        taper = .5 * (1. + np.cos(np.pi * progress))
        envelope = np.where(radius_in_sigmas >= cutoff, 0., gaussian * taper)

        carrier = np.sin(2 * np.pi * parameters["spatial_frequency_cpd"] * x_deg)
        return parameters["background"] + parameters["contrast"] * envelope * carrier / 2

    @staticmethod
    def geometry(p):
        radius = p["sigma_deg"] * p["cutoff_sigmas"]
        return {"raster_extent_deg": max(p["size_deg"], 2*radius),
                "support_radius_deg": radius, "support_diameter_deg": 2*radius,
                "taper_start_radius_deg": (p["cutoff_sigmas"]-1)*p["sigma_deg"],
                "background_outside_support": p["background"]}

    @staticmethod
    def visible(p, x, y, steps):
        return np.hypot(x, y) < p["sigma_deg"]*p["cutoff_sigmas"]

    SPEC = StimulusSpec("contrast_sensitivity_grating", "Contrast sensitivity grating",
        "Compact-support Gaussian-windowed grating with smoothly tapered outer edge in degree coordinates.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS, family="contrast_sensitivity_grating",
        render=render, validator=validate.__func__, floating_raster=True, geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry", "luminance"))


class GaussianFixation(LibraryStimulus):
    """Gaussian fixation: sigma .035 degrees; peak background + .09, limited to 1."""
    PARAMETERS = (
        ConfigField("size_deg", "Fixation patch", "float", .5, minimum=.1, maximum=3, units="degrees"),
        ConfigField("sigma_deg", "Gaussian standard deviation", "float", .035, minimum=.001, maximum=.2, units="degrees"),
        ConfigField("increment", "Digital increment above background", "float", .09, minimum=0, maximum=1, units='digital increment'),
        ConfigField("background", "Digital background", "float", .5, minimum=0, maximum=1, units='digital intensity, 0 to 1'),
    )

    def render(parameters, x_deg, y_deg):
        peak = min(1., parameters["background"] + parameters["increment"])
        envelope = np.exp(-(x_deg*x_deg + y_deg*y_deg)/(2*parameters["sigma_deg"]**2))
        image = parameters["background"] + (peak-parameters["background"])*envelope
        return image

    SPEC = StimulusSpec("gaussian_fixation", "Gaussian fixation", "Small Gaussian fixation marker in degrees.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS, family="gaussian_fixation",
        render=render, calibration_requirements=("geometry", "luminance"))



class DetectionScene(LibraryStimulus):
    """Degree-based line/contour/flanker stimulus; digital increments, not optical contrast.

    Ring = outer ellipse minus ellipse with both axes inset by ring_width_deg.
    This defines axial thickness, not a claim of constant normal stroke width.
    Fixation peak is limited to 1; other additive layers must fit in [0,1].
    Probe length/width are editable angular dimensions, independent of raster size.
    Old documents missing these two keys retain the former .133/.013-degree defaults.
    Probe pixels use rectangular pixel-area coverage (subpixel lines do not
    disappear). Layer order: background/flanker, ring, probe, Gaussian fixation.
    """
    PARAMETERS = (
        ConfigField("size_deg","Scene extent","float",14.,minimum=.1,maximum=40, units='degrees'),
        ConfigField("background","Digital background","float",.5,minimum=0,maximum=1, units='digital intensity, 0 to 1'),
        ConfigField("contrast","Probe digital increment","float",.02,minimum=0,maximum=1, units='digital increment'),
        ConfigField("probe_length_deg", "Probe length", "float", 1.0, minimum=0, units="degrees"),
        ConfigField("probe_width_deg", "Probe width", "float", .013, minimum=0, units="degrees"),
        ConfigField("probe_present","Show probe","choice",True,choices=(True,False)),
        ConfigField("probe_x_deg","Probe x","float",0.,minimum=-6,maximum=6, units='degrees'),
        ConfigField("probe_y_deg","Probe y","float",0.,minimum=-6,maximum=6, units='degrees'),
        ConfigField("ring_present","Show ring","choice",False,choices=(True,False)),
        ConfigField("ring_radius_deg","Outer horizontal radius","float",.6,minimum=.17,maximum=3, units='degrees'),
        ConfigField("ring_y_deg","Ring centre y","float",0.,minimum=-5,maximum=5, units='degrees'),
        ConfigField("aspect_ratio","b/a","float",1.,minimum=.5,maximum=1, units='b/a, unitless'),
        ConfigField("ring_increment","Ring increment","float",.1,minimum=0,maximum=1, units='digital increment'),
        ConfigField("flanker_present","Show flanker","choice",False,choices=(True,False)),
        ConfigField("flanker_cpd","Flanker frequency","float",2.,minimum=.01,maximum=32, units='cycles/degree'),
    )

    def validate(p):
        a, b = p["ring_radius_deg"], p["ring_radius_deg"] * p["aspect_ratio"]
        if p["ring_present"] and min(a, b) <= .16:
            raise ValueError(f"Ring inner axes must remain positive: a={a:g}, b={b:g} deg; both must exceed 0.16 deg.")
        if p["ring_present"] and p["background"] + p["ring_increment"] > 1:
            raise ValueError(f"Ring exceeds gamut: background {p['background']:g} + increment {p['ring_increment']:g} > 1; allowed increment <= {1-p['background']:g}.")
        if p["flanker_present"] and not .009 <= p["background"] <= .991:
            raise ValueError(f"Flanker exceeds gamut: background {p['background']:g} must be in [0.009, 0.991] for +/-0.009 modulation.")
        # Additive probe overlap depends on pixel coverage. render_values and
        # the experiment's resolved staircase limit check the actual grid.

    def render(p,x,y, *, pixel_steps=None):
        image = np.full_like(x,p["background"],dtype=float)
        if p["flanker_present"]:
            mask = (abs(x+3.)<=2.5)&(abs(y)<=2.5)  # inner edge -0.5 degrees
            image += mask*.009*np.sin(2*np.pi*p["flanker_cpd"]*(x+3.))
        if p["ring_present"]:
            a,b=p["ring_radius_deg"],p["ring_radius_deg"]*p["aspect_ratio"]
            outer=(x/a)**2+((y-p["ring_y_deg"])/b)**2<=1
            inner=(x/(a-.16))**2+((y-p["ring_y_deg"])/(b-.16))**2<1
            image=np.where(outer & ~inner,p["background"]+p["ring_increment"],image)
        if p["probe_present"]:
            cx, cy = DetectionScene.probe_coverage(p,x,y,pixel_steps)
            image += p["contrast"]*cx*cy
        envelope=np.exp(-(x*x+y*y)/(2*.035**2))
        image = image*(1-envelope)+min(1.,p["background"]+.09)*envelope
        return image

    @staticmethod
    def probe_coverage(p, x, y, pixel_steps=None):
        dx=(np.abs(np.gradient(x, axis=1)) if x.shape[1]>1 else .0001) if pixel_steps is None else pixel_steps[0]
        dy=(np.abs(np.gradient(y, axis=0)) if y.shape[0]>1 else .0001) if pixel_steps is None else pixel_steps[1]
        cx=np.maximum(0,np.minimum(x+dx/2,p["probe_x_deg"]+p["probe_width_deg"]/2)-np.maximum(x-dx/2,p["probe_x_deg"]-p["probe_width_deg"]/2))/dx
        cy=np.maximum(0,np.minimum(y+dy/2,p["probe_y_deg"]+p["probe_length_deg"]/2)-np.maximum(y-dy/2,p["probe_y_deg"]-p["probe_length_deg"]/2))/dy
        return cx, cy

    @staticmethod
    def geometry(p):
        half = p["size_deg"]/2
        if p["probe_present"]:
            half = max(half, abs(p["probe_x_deg"])+p["probe_width_deg"]/2,
                       abs(p["probe_y_deg"])+p["probe_length_deg"]/2)
        if p["ring_present"]:
            half = max(half, p["ring_radius_deg"], abs(p["ring_y_deg"])+p["ring_radius_deg"]*p["aspect_ratio"])
        if p["flanker_present"]:
            half = max(half, 5.5)
        return {"raster_extent_deg": 2*half}

    @staticmethod
    def visible(p, x, y, steps):
        # An explicitly absent probe is a valid catch/alternative, including
        # zero modulation. A present probe must retain geometrical coverage.
        if not p["probe_present"]:
            return True
        cx, cy = DetectionScene.probe_coverage(p,x,y,steps)
        return (cx > 0) & (cy > 0)

    SPEC=StimulusSpec("detection_scene","Degree-based detection scene","Explicit line, ring, flanker and fixation in degrees.",
        "src/psychophysics_lab/stimulus_library.py",parameters=PARAMETERS,family="detection_scene",render=render,
        validator=validate, floating_raster=True, pixel_coverage=True,
        legacy_parameter_defaults={"probe_length_deg": .133, "probe_width_deg": .013}, spatial_frequencies=lambda p:(p["flanker_cpd"],) if p["flanker_present"] else (),
        geometry=geometry.__func__, required_support=visible.__func__,
        calibration_requirements=("geometry","luminance"))


def library_stimulus_specs():
    """Discover explicitly subclassed shared definitions only."""
    specifications = tuple(cls.SPEC for cls in LibraryStimulus.__subclasses__() if cls.__module__ == __name__)
    if len({spec.id for spec in specifications}) != len(specifications):
        raise ValueError("Shared stimulus classes require unique SPEC.id values.")
    return specifications
