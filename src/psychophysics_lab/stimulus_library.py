"""PsyCoLab: ONE file where each stimulus is ONE self-contained class.

Copy a LibraryStimulus subclass in this file; edit only the copied class:
PARAMETERS (science/settings), render() (pixels), SPEC (ID/description).
New classes register automatically. They need no generator, separate
stimulus module, JSON defaults file, or edits in another class/table.

Experiments are separate .py files; they control trial timing, locations,
responses, adaptation and optional beep sounds. All grayscale values 0–1
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
# SIMPLE COMPLETE STIMULI — copy one class; no other code needs changing.
# The Scene convenience functions remain available above via an import.
# ----------------------------------------------------------------------------

class LinePatch(LibraryStimulus):
    """A line at arbitrary orientation (0° = vertical)."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 2., units="degrees", minimum=.1, maximum=45),
        ConfigField("length_deg", "Line length", "float", 1., units="degrees", minimum=.01, maximum=10),
        ConfigField("width_deg", "Line thickness", "float", .08, units="degrees", minimum=.001, maximum=2),
        ConfigField("orientation_deg", "Orientation", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0–1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        angle = np.deg2rad(parameters["orientation_deg"])
        u = x_deg*np.cos(angle) + y_deg*np.sin(angle)
        v = -x_deg*np.sin(angle) + y_deg*np.cos(angle)
        inside = (np.abs(u) <= parameters["width_deg"]/2) & (np.abs(v) <= parameters["length_deg"]/2)
        image = np.where(inside, parameters["intensity"], .5)
        return image

    SPEC = StimulusSpec(
        id="oriented_line", display_name="Oriented line",
        description="An oriented filled line, specified in degrees.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="line", render=render,
        calibration_requirements=("geometry",),
    )


class SquarePatch(LibraryStimulus):
    """A filled square centred on the stimulus origin."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 3., units="degrees", minimum=.1, maximum=45),
        ConfigField("side_deg", "Square side", "float", 1., units="degrees", minimum=.01, maximum=20),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0–1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        half = parameters["side_deg"]/2
        inside = (np.abs(x_deg) <= half) & (np.abs(y_deg) <= half)
        image = np.where(inside, parameters["intensity"], .5)
        return image

    SPEC = StimulusSpec(
        id="square_patch", display_name="Square",
        description="A filled square with a digital background of 0.5.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        calibration_requirements=("geometry",),
    )


class RectanglePatch(LibraryStimulus):
    """A filled rectangle; size is the overall display patch diameter."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 3., units="degrees", minimum=.1, maximum=45),
        ConfigField("width_deg", "Rectangle width", "float", 1., units="degrees", minimum=.01, maximum=20),
        ConfigField("height_deg", "Rectangle height", "float", 2., units="degrees", minimum=.01, maximum=20),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0–1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        inside = ((np.abs(x_deg) <= parameters["width_deg"]/2)
                  & (np.abs(y_deg) <= parameters["height_deg"]/2))
        image = np.where(inside, parameters["intensity"], .5)
        return image

    SPEC = StimulusSpec(
        id="rectangle_patch", display_name="Rectangle",
        description="A filled width-by-height rectangle.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        calibration_requirements=("geometry",),
    )


class EllipsePatch(LibraryStimulus):
    """A filled ellipse defined by the two semi-axes, not the full diameters."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=60),
        ConfigField("radius_x_deg", "Horizontal semi-axis", "float", 2., units="degrees", minimum=.01, maximum=30),
        ConfigField("radius_y_deg", "Vertical semi-axis", "float", 1., units="degrees", minimum=.01, maximum=30),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0–1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        r2 = (x_deg/parameters["radius_x_deg"])**2 + (y_deg/parameters["radius_y_deg"])**2
        image = np.where(r2 <= 1., parameters["intensity"], .5)
        return image

    SPEC = StimulusSpec(
        id="ellipse_patch", display_name="Filled ellipse",
        description="A filled ellipse with semi-axes in degrees.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        calibration_requirements=("geometry",),
    )


class AnnulusPatch(LibraryStimulus):
    """Elliptical annulus with an inner-to-outer semi-axis ratio."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=60),
        ConfigField("radius_x_deg", "Horizontal semi-axis", "float", 2., units="degrees", minimum=.01, maximum=30),
        ConfigField("radius_y_deg", "Vertical semi-axis", "float", 1., units="degrees", minimum=.01, maximum=30),
        ConfigField("inner_ratio", "Inner-to-outer radius ratio", "float", .85, minimum=0, maximum=.99),
        ConfigField("intensity", "Digital brightness", "float", 1., units="0–1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        r2 = (x_deg/parameters["radius_x_deg"])**2 + (y_deg/parameters["radius_y_deg"])**2
        inside = (r2 <= 1.) & (r2 >= parameters["inner_ratio"]**2)
        image = np.where(inside, parameters["intensity"], .5)
        return image

    SPEC = StimulusSpec(
        id="annulus_patch", display_name="Elliptical annulus",
        description="An elliptical ring with a fractional inner semi-axis.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        calibration_requirements=("geometry",),
    )


class GaussianDot(LibraryStimulus):
    """A Gaussian dot, smoothly blended with its background."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 2., units="degrees", minimum=.1, maximum=45),
        ConfigField("sigma_deg", "Gaussian standard deviation", "float", .2, units="degrees", minimum=.001, maximum=10),
        ConfigField("intensity", "Peak digital brightness", "float", 1., units="0–1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        sigma = parameters["sigma_deg"]
        r2 = x_deg*x_deg + y_deg*y_deg
        envelope = np.where(r2 <= (4*sigma)**2, np.exp(-r2/(2*sigma*sigma)), 0.)
        image = .5 + (parameters["intensity"]-.5)*envelope
        return image

    SPEC = StimulusSpec(
        id="gaussian_dot", display_name="Gaussian dot",
        description="A Gaussian dot truncated at four standard deviations.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="shape", render=render,
        calibration_requirements=("geometry",),
    )


class SinusoidalGrating(LibraryStimulus):
    """A rectangular-patch sinusoid, distinct from the reference CSF shader."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=45),
        ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., units="cycles/degree", minimum=.01, maximum=50),
        ConfigField("orientation_deg", "Carrier orientation", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("phase_deg", "Phase", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("contrast", "Digital modulation", "float", .2, units="0–1", minimum=0, maximum=1),
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


class GaborPatch(LibraryStimulus):
    """A Gaussian-windowed grating in degrees, independent of CSF's GLSL."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 5., units="degrees", minimum=.1, maximum=45),
        ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., units="cycles/degree", minimum=.01, maximum=50),
        ConfigField("sigma_deg", "Gaussian SD", "float", .8, units="degrees", minimum=.001, maximum=20),
        ConfigField("orientation_deg", "Carrier orientation", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("phase_deg", "Phase", "float", 0., units="degrees", minimum=-360, maximum=360),
        ConfigField("contrast", "Digital modulation", "float", .2, units="0–1", minimum=0, maximum=1),
    )

    def render(parameters, x_deg, y_deg):
        theta = np.deg2rad(parameters["orientation_deg"])
        coordinate = x_deg*np.cos(theta) + y_deg*np.sin(theta)
        carrier = np.cos(2*np.pi*parameters["spatial_frequency_cpd"]*coordinate
                         + np.deg2rad(parameters["phase_deg"]))
        r2 = x_deg*x_deg + y_deg*y_deg
        sigma = parameters["sigma_deg"]
        envelope = np.exp(-r2/(2*sigma*sigma))
        inside = (np.abs(x_deg) <= parameters["size_deg"]/2) & (np.abs(y_deg) <= parameters["size_deg"]/2)
        image = np.where(inside, .5 + .5*parameters["contrast"]*envelope*carrier, .5)
        return image

    SPEC = StimulusSpec(
        id="gabor_patch", display_name="Gabor patch",
        description="Gaussian-windowed cosine carrier in cycles per degree.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, family="gabor", render=render,
        calibration_requirements=("geometry",),
    )


class FixationCross(LibraryStimulus):
    """Registered fixation_cross; edit PARAMETERS, render and SPEC here."""
    PARAMETERS = (
        ConfigField("size_deg", "Patch diameter", "float", 0.8, units="degrees", minimum=0.2, maximum=3),
        ConfigField("arm_length_deg", "Cross arm length", "float", 0.35, units="degrees", minimum=0.05, maximum=1),
        ConfigField("width_deg", "Cross line width", "float", 0.06, units="degrees", minimum=0.01, maximum=0.3),
        ConfigField("intensity", "Digital brightness", "float", 1.0, units="0–1", minimum=0, maximum=1),
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
        ConfigField("intensity", "Digital brightness", "float", 1.0, units="0–1", minimum=0, maximum=1),
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
                    units="0–1 command", minimum=0.5, maximum=1.0),
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
        image = .5 + .5 * parameters["contrast"] * envelope * carrier
        return image
    
    
    SPEC = StimulusSpec("teaching_gabor", "Teaching Gabor", "Gaussian-windowed grating; degrees and digital contrast.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS,
        default_config="configs/stimuli/teaching_gabor.json", family="orientation_patch", render=render,
        calibration_requirements=("geometry",))


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
    SPEC = StimulusSpec("composed_scene", "Composed scene",
        "Ordered drawings from the shared stimulus library.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS,
        default_config="configs/stimuli/composed_scene.json", family="scene",
        render=render.__func__, validator=validate.__func__,
        calibration_requirements=("geometry", "luminance"),
        source_dependencies=("src/psychophysics_lab/stimulus_library.py",),
        spatial_frequencies=frequencies.__func__)


# Hardware-dependent reference CSF (Events/stimuliC.py) and monitor diagnostic
# geometry_bar are deliberately NOT reimplemented here: duplicating them would
# invent an unverified rendering model. Keep these as read-only adapters until
# physical equivalence has been established. Custom researcher modules already
# tied to saved experiment versions are also preserved, not overwritten.


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
                    units="0–1 command", minimum=0.5, maximum=1.0),
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
        id="new_probe_vertical_line",
        display_name="Example: White Line",
        description="Beginner visual stimulus: a line on a grey background.",
        source_path="src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS,
        default_config="configs/stimuli/new_probe_vertical_line.json",
        family="simple_line",
        render=render,
        calibration_requirements=("geometry",),
    )



class CSFGrating(LibraryStimulus):
    """Reference CSF stimulus: authoritative shader and validated configuration.

    This is deliberately not a NumPy preview: the original display uses a
    GLSL luminance/contrast shader and monitor-specific geometry. An ordinary
    Scene raster does NOT yet reproduce its optical or timing behaviour.
    Researchers can inspect the scientific shader HERE in the single library.
    The existing qualified presentation implementation is internal only.
    """
    from ._reference_csf.experiment_definition import CSF_SPEC as _CSF_SPEC
    PARAMETERS = tuple(
        field for field in _CSF_SPEC.fields if field.section == "Stimulus conditions"
    )
    del _CSF_SPEC

    # Copied verbatim from the previously authoritative Events/stimuliC.py.
    # Acquisition's internal OpenGL presenter now references THIS exact string.
    FRAGMENT_SOURCE = """
        //precision highp float;
        
        uniform float fs;
        uniform float phase;
        uniform float contr;
        uniform float bg;
        uniform float box;
        uniform float theta;
        uniform float Lbg, Lmin, Lmax, gamma, BTRR;
        uniform float width;  // Declare width uniform  # <- added
        uniform float SdeX;
        uniform float SdeY;
        uniform float physicalFrequency;
        uniform float pitchX, pitchY, eyeDistance;
        uniform float screenCx, screenCy, stimCx, stimCy;
        
        vec3 lum2image(float c) {
            vec3 vout;
            float U = 255.0*pow(((1+c)*Lbg-Lmin)/(Lmax-Lmin),1.0/gamma);
            float b1 = (BTRR+1.0)/BTRR;
            //float b = min(floor(U*b1),255.0);
            float b = min(floor(U*b1),255.0) + 1.0/32.0;
            //float b2 = floor((U-b/b1)*(BTRR+1.0));
            float b2 = floor((U-b/b1)*(BTRR+1.0)) + 1.0/32.0;
            vout = vec3(b2/255.0, 0.0 ,b/255.0);
            return vout;
        }

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float pi = 2.0 * acos(0.0);
            float Sde = 0.03; // 0.05 or 0.17 | USE: Sde = 0.03, 0.025 for <10cdm2
            //float m = exp(-0.5*(x*x + y*y)/pow(Sde,2)); // <- 2 or 2.5
            float m = exp(-0.5*((x*x)/pow(SdeX,2) + (y*y)/pow(SdeY,2)));
            // In cpd mode the phase is computed from the physical angular
            // coordinate of every fragment, not an uncalibrated legacy scalar.
            // This also avoids a screen-wide-FOV approximation near eccentricity.
            vec2 phase_coords = vec2(x, y);
            float frequency_phase = fs * (x*cos(theta)+y*sin(theta));
            if (physicalFrequency > 0.5) {
                vec2 pitch = vec2(pitchX, pitchY);
                vec2 screen_centre = vec2(screenCx, screenCy);
                vec2 monitor_px = vec2(stimCx,stimCy) + phase_coords * width;
                vec2 screen_m = (monitor_px - screen_centre) * pitch;
                vec2 centre_m = (vec2(stimCx,stimCy)-screen_centre)*pitch;
                vec2 degrees_relative = degrees(atan(screen_m / eyeDistance))
                                       - degrees(atan(centre_m / eyeDistance));
                float pi = 2.0 * acos(0.0);
                frequency_phase = 2.0 * pi * fs
                    * (degrees_relative.x * cos(theta)
                       + degrees_relative.y * sin(theta));
            }
            float c = m*contr*sin(frequency_phase + phase);
            if (box == 1.0) {
                gl_FragColor.rgba = vec4(lum2image(c),1.0);
            } else {
                c = bg + c/2.0;
                gl_FragColor.rgba = vec4(c,c,c,1.0);
            }
        }
        """

    @staticmethod
    def render(parameters, x_deg, y_deg):
        raise NotImplementedError(
            "Reference CSF uses its hardware-specific GLSL renderer; "
            "a NumPy Scene preview would not establish shader equivalence."
        )

    SPEC = StimulusSpec(
        "legacy_csf", "CSF grating (reference shader)",
        "Authoritative physical CSF shader, driven by the registered CSF experiment.",
        "src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS,
        default_config="configs/stimuli/legacy_csf.json",
        family="csf", render=None,
        calibration_requirements=("geometry", "luminance", "timing"),
        source_dependencies=(
            "src/psychophysics_lab/_reference_csf/stimuliC.py",
            "src/psychophysics_lab/_reference_csf/libC.py",
            "src/psychophysics_lab/_reference_csf/adaptiveMethods.py",
            "src/psychophysics_lab/_reference_csf/adaptive_session.py",
            "src/psychophysics_lab/_reference_csf/functionsForUse.py",
            "src/psychophysics_lab/_reference_csf/config.py",
            "src/psychophysics_lab/_reference_csf/contrast_sensitivity_function.py",
        ),
    )


class ContrastSensitivityGrating(LibraryStimulus):
    """Thesis CSF: Gaussian sigma in degrees; sinusoidal carrier in cycles/degree.

    RGB command = background + (contrast/2) * Gaussian * sin(carrier phase).
    Contrast is digital peak-to-peak modulation, not measured optical Michelson
    contrast. The 8-degree raster aperture is an explicit implementation extent,
    not a historical aperture established by the thesis. Hardware parity is unverified.
    """
    PARAMETERS = (
        ConfigField("size_deg", "Raster aperture", "float", 8., minimum=.1, maximum=30, units="degrees"),
        ConfigField("sigma_deg", "Gaussian standard deviation", "float", 1., minimum=.001, maximum=5, units="degrees"),
        ConfigField("spatial_frequency_cpd", "Spatial frequency", "float", 2., minimum=.01, maximum=64, units="cycles/degree"),
        ConfigField("contrast", "Digital peak-to-peak modulation", "float", .1, minimum=0, maximum=1, units='digital peak-to-peak modulation'),
        ConfigField("background", "Digital background", "float", .5, minimum=0, maximum=1, units='digital intensity, 0 to 1'),
    )

    @staticmethod
    def validate(parameters):
        if parameters["contrast"] > 2 * min(parameters["background"], 1-parameters["background"]):
            raise ValueError("Requested grating modulation exceeds the available digital range; no silent clipping.")

    def render(parameters, x_deg, y_deg):
        envelope = np.exp(-(x_deg*x_deg + y_deg*y_deg)/(2*parameters["sigma_deg"]**2))
        carrier = np.sin(2*np.pi*parameters["spatial_frequency_cpd"]*x_deg)
        image = parameters["background"] + parameters["contrast"]*envelope*carrier/2
        return image

    SPEC = StimulusSpec("thesis_csf_grating", "Contrast sensitivity grating", "Gaussian-windowed grating in explicit degree coordinates.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS, family="thesis_csf",
        render=render, validator=validate.__func__, floating_raster=True, calibration_requirements=("geometry", "luminance"))


class GaussianFixation(LibraryStimulus):
    """Thesis fixation: sigma .035 degrees; peak background + .09, limited to 1."""
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

    SPEC = StimulusSpec("thesis_gaussian_fixation", "Gaussian fixation", "Small Gaussian fixation marker in degrees.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS, family="thesis_fixation",
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
        if p["ring_present"] and p["ring_radius_deg"]*p["aspect_ratio"] <= .16:
            raise ValueError("Ring inner axes must remain positive after the .16 degree inset.")
        increment = (p["contrast"] if p["probe_present"] else 0) + (p["ring_increment"] if p["ring_present"] else .009 if p["flanker_present"] else 0)
        if p["background"]+increment>1 or (p["flanker_present"] and p["background"]<.009):
            raise ValueError("Scene digital increments exceed gamut; no clipping.")

    def render(p,x,y):
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
            dx=np.abs(np.gradient(x, axis=1)) if x.shape[1]>1 else .0001
            dy=np.abs(np.gradient(y, axis=0)) if y.shape[0]>1 else .0001
            cx=np.maximum(0,np.minimum(x+dx/2,p["probe_x_deg"]+p["probe_width_deg"]/2)-np.maximum(x-dx/2,p["probe_x_deg"]-p["probe_width_deg"]/2))/dx
            cy=np.maximum(0,np.minimum(y+dy/2,p["probe_y_deg"]+p["probe_length_deg"]/2)-np.maximum(y-dy/2,p["probe_y_deg"]-p["probe_length_deg"]/2))/dy
            image += p["contrast"]*cx*cy
        envelope=np.exp(-(x*x+y*y)/(2*.035**2))
        image = image*(1-envelope)+min(1.,p["background"]+.09)*envelope
        return image

    SPEC=StimulusSpec("detection_scene","Degree-based detection scene","Explicit line, ring, flanker and fixation in degrees.",
        "src/psychophysics_lab/stimulus_library.py",parameters=PARAMETERS,family="detection_scene",render=render,
        validator=validate, floating_raster=True,
        legacy_parameter_defaults={"probe_length_deg": .133, "probe_width_deg": .013}, spatial_frequencies=lambda p:(p["flanker_cpd"],) if p["flanker_present"] else (),
        calibration_requirements=("geometry","luminance"))


def library_stimulus_specs():
    """Discover explicitly subclassed shared definitions only."""
    specifications = tuple(cls.SPEC for cls in LibraryStimulus.__subclasses__())
    if len({spec.id for spec in specifications}) != len(specifications):
        raise ValueError("Shared stimulus classes require unique SPEC.id values.")
    return specifications
