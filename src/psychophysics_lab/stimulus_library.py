"""Researcher-facing drawings and composition, independent of the TUI/display.

Add simple drawings here. Coordinates and sizes are degrees; intensities are
digital commands, NOT measured luminance. A function makes an immutable drawing;
Scene combines drawings in written order. Procedures own time, input and state.
"""
from dataclasses import dataclass
from types import MappingProxyType
import json
import math
import numpy as np


def _number(name, value, low=None, high=None, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if (positive and value <= 0) or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f"{name} is outside its permitted range")
    return float(value)


@dataclass(frozen=True)
class Drawing:
    """An immutable, serializable primitive. Prefer the named functions below."""
    kind: str
    parameters: object

    def __post_init__(self):
        if not isinstance(self.kind, str) or self.kind not in _FIELDS or not isinstance(self.parameters, dict):
            raise ValueError("Use a known drawing and a parameter dictionary")
        p = dict(self.parameters)
        if p.keys() != _FIELDS[self.kind]:
            raise ValueError(f"Unexpected/missing parameters for {self.kind}")
        for name, value in p.items():
            if name == "waveform":
                if value not in ("sine", "cosine"):
                    raise ValueError("waveform must be sine or cosine")
            else:
                p[name] = _number(name, value,
                    low=0 if name in {"intensity", "mean", "amplitude", "inner_ratio"} else None,
                    high=1 if name in {"intensity", "mean", "amplitude", "inner_ratio"} else None,
                    positive=name in {"size_deg", "length_deg", "width_deg", "height_deg", "radius_x_deg", "radius_y_deg", "sigma_deg", "spatial_frequency_cpd"})
        if "amplitude" in p and p["amplitude"] > min(p["mean"], 1-p["mean"]):
            raise ValueError("Grating mean +/- amplitude must stay in [0,1]; no silent clipping")
        if p.get("inner_ratio") == 1:
            raise ValueError("Annulus inner_ratio must be below 1")
        if self.kind == "fixation" and p["width_deg"] > p["length_deg"]:
            raise ValueError("Fixation width exceeds its arm length")
        object.__setattr__(self, "parameters", MappingProxyType(p))

    def at(self, x_deg, y_deg):
        """Return a repositioned copy, leaving this drawing unchanged."""
        return Drawing(self.kind, dict(self.parameters) | {"x_deg": x_deg, "y_deg": y_deg})

    def to_dict(self):
        return {"kind": self.kind, "parameters": dict(self.parameters)}

    @property
    def radius_bound(self):
        p = self.parameters
        if self.kind in ("grating", "gabor"):
            return p["size_deg"] / math.sqrt(2)
        if self.kind == "gaussian_dot":
            return 4 * p["sigma_deg"]
        if self.kind in ("ellipse", "annulus"):
            return max(p["radius_x_deg"], p["radius_y_deg"])
        if self.kind == "fixation":
            return math.hypot(p["length_deg"], p["width_deg"]) / 2
        return math.hypot(p.get("length_deg", p.get("height_deg")), p["width_deg"]) / 2

    def _layer(self, x, y):
        p = self.parameters
        x, y = x-p["x_deg"], y-p["y_deg"]
        angle = math.radians(p["orientation_deg"])
        u, v = x*math.cos(angle)+y*math.sin(angle), -x*math.sin(angle)+y*math.cos(angle)
        if self.kind == "fixation":
            mask = ((abs(u) <= p["width_deg"]/2) & (abs(v) <= p["length_deg"]/2)) | ((abs(v) <= p["width_deg"]/2) & (abs(u) <= p["length_deg"]/2))
        elif self.kind in ("line", "rectangle"):
            mask = (abs(u) <= p["width_deg"]/2) & (abs(v) <= p.get("length_deg", p.get("height_deg"))/2)
        elif self.kind in ("ellipse", "annulus"):
            r2 = (u/p["radius_x_deg"])**2 + (v/p["radius_y_deg"])**2
            mask = r2 <= 1
            if self.kind == "annulus":
                mask &= r2 >= p["inner_ratio"]**2
        elif self.kind == "gaussian_dot":
            r2 = u*u+v*v
            return p["intensity"], np.where(r2 <= (4*p["sigma_deg"])**2, np.exp(-r2/(2*p["sigma_deg"]**2)), 0)
        else:
            # Orientation rotates the carrier, not the square aperture.
            mask = (abs(x) <= p["size_deg"]/2) & (abs(y) <= p["size_deg"]/2)
            phase = 2*np.pi*p["spatial_frequency_cpd"]*u + math.radians(p["phase_deg"])
            carrier = np.sin(phase) if p["waveform"] == "sine" else np.cos(phase)
            envelope = np.exp(-(u*u+v*v)/(2*p["sigma_deg"]**2)) if self.kind == "gabor" else 1
            return p["mean"] + p["amplitude"]*envelope*carrier, mask
        return p["intensity"], mask


def fixation(length_deg=.35, width_deg=.06, intensity=1., x_deg=0., y_deg=0., orientation_deg=0.):
    """Plus sign; length is the full length of each arm."""
    return Drawing("fixation", locals())


def line(length_deg=.6, width_deg=.08, intensity=1., x_deg=0., y_deg=0., orientation_deg=0.):
    """Filled line; zero orientation is vertical, positive rotates CCW."""
    return Drawing("line", locals())


def rectangle(width_deg=1., height_deg=1., intensity=1., x_deg=0., y_deg=0., orientation_deg=0.):
    return Drawing("rectangle", locals())


def square(size_deg=1., intensity=1., x_deg=0., y_deg=0., orientation_deg=0.):
    return rectangle(size_deg, size_deg, intensity, x_deg, y_deg, orientation_deg)


def ellipse(radius_x_deg=.5, radius_y_deg=.5, intensity=1., x_deg=0., y_deg=0., orientation_deg=0.):
    """Filled ellipse with semi-axes in degrees."""
    return Drawing("ellipse", locals())


def annulus(radius_x_deg=.5, radius_y_deg=.5, inner_ratio=.9, intensity=1., x_deg=0., y_deg=0., orientation_deg=0.):
    """Elliptical ring; inner_ratio scales both outer semi-axes.

    The old EllipseCircle2D normalized width w maps to sqrt(1-w), not
    a constant thickness in degrees. Its normalized axes require conversion.
    """
    return Drawing("annulus", locals())


def gaussian_dot(sigma_deg=.035, intensity=1., x_deg=0., y_deg=0., orientation_deg=0.):
    """Gaussian alpha against the scene; truncated at four sigma."""
    return Drawing("gaussian_dot", locals())


def grating(size_deg=5., spatial_frequency_cpd=1., amplitude=.1, mean=.5,
            phase_deg=0., waveform="sine", x_deg=0., y_deg=0., orientation_deg=0.):
    """Square aperture, digital mean + amplitude * sinusoid; 0 = vertical bars.

    Legacy Grating_M non-box mode uses amplitude=contr/2. Its fs is radians
    per patch, so cpd=fs/(2*pi*patch_width_deg), NOT fs/31.5 in general.
    """
    return Drawing("grating", locals())


def gabor(size_deg=5., spatial_frequency_cpd=2., sigma_deg=.8, amplitude=.1, mean=.5,
          phase_deg=0., waveform="cosine", x_deg=0., y_deg=0., orientation_deg=0.):
    """Gaussian-windowed sinusoid; not a replacement for the legacy CSF shader."""
    return Drawing("gabor", locals())


# Strict recipe schema; add a public function and its parameter set for new art.
import inspect as _inspect
_FUNCTIONS = {f.__name__: f for f in (fixation, line, rectangle, ellipse, annulus, gaussian_dot, grating, gabor)}
_FIELDS = {name: set(_inspect.signature(f).parameters) for name, f in _FUNCTIONS.items()}


@dataclass(frozen=True, init=False)
class Scene:
    """Ordered alpha composition on ONE background (no opaque patch erasure)."""
    drawings: tuple
    background: float

    def __init__(self, *drawings, background=.5):
        if any(not isinstance(d, Drawing) for d in drawings):
            raise TypeError("Scene accepts drawings returned by stimulus functions")
        if len(drawings) > 128:
            raise ValueError("A scene may contain at most 128 drawings")
        object.__setattr__(self, "drawings", tuple(drawings))
        object.__setattr__(self, "background", _number("background", background, 0, 1))

    def render(self, x_deg, y_deg):
        x, y = np.broadcast_arrays(np.asarray(x_deg, dtype=float), np.asarray(y_deg, dtype=float))
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("Scene coordinates must be finite")
        pixels = np.full(x.shape, self.background)
        for drawing in self.drawings:
            value, alpha = drawing._layer(x, y)
            pixels = pixels*(1-alpha) + value*alpha
        return pixels

    def to_dict(self):
        return {"schema_version": 1, "background": self.background, "drawings": [d.to_dict() for d in self.drawings]}

    @classmethod
    def from_dict(cls, doc):
        if not isinstance(doc, dict) or set(doc) != {"schema_version", "background", "drawings"} or type(doc["schema_version"]) is not int or doc["schema_version"] != 1 or not isinstance(doc["drawings"], list):
            raise ValueError("Invalid scene recipe")
        drawings = []
        for raw in doc["drawings"]:
            if not isinstance(raw, dict) or set(raw) != {"kind", "parameters"}:
                raise ValueError("Invalid drawing recipe")
            drawings.append(Drawing(raw["kind"], raw["parameters"]))
        return cls(*drawings, background=doc["background"])

    def parameters(self, size_deg):
        """Validated parameters for the registered scene adapter / RunContext."""
        size = _number("size_deg", size_deg, positive=True)
        for drawing in self.drawings:
            p = drawing.parameters
            if max(abs(p["x_deg"]), abs(p["y_deg"])) + drawing.radius_bound > size/2:
                raise ValueError("Scene aperture could clip a drawing; enlarge size_deg")
        return {"size_deg": size, "scene_json": json.dumps(self.to_dict(), sort_keys=True, allow_nan=False)}


# ============================================================================
# REGISTERED RESEARCH STIMULI — EDIT HERE (one class per complete stimulus)
# ============================================================================
# A class keeps PARAMETERS, render() and SPEC next to one another.
# Experiment timing, stimulus placement and beeps belong in experiment files.
# The original individual modules are retired: edit this file only.
# Primitive functions and Scene above can be mixed to make more complex art.
from dataclasses import replace as _replace
from .experiments.spec import ConfigField
from .stimuli.registry import StimulusSpec

class LibraryStimulus:
    """Marker for complete registered definitions inside this ONE file.

    Subclass with PARAMETERS, render and SPEC; the registry discovers new
    classes without another Python adapter or contributions.py edit.
    """


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
        return np.where(horizontal | vertical, parameters["intensity"], 0.5)
    
    SPEC = StimulusSpec(
        "fixation_cross", "Fixation cross", "Reusable + drawn in degrees.",
        "src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, default_config="configs/stimuli/fixation_cross.json",
        family="fixation", render=render, calibration_requirements=("geometry",),
    )
    SPEC = _replace(SPEC, source_dependencies=())


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
        return np.where(inside, parameters["intensity"], 0.5)
    
    SPEC = StimulusSpec(
        "vertical_line_probe", "Vertical white line", "Reusable visual-angle line.",
        "src/psychophysics_lab/stimulus_library.py",
        parameters=PARAMETERS, default_config="configs/stimuli/vertical_line_probe.json",
        family="line", render=render, calibration_requirements=("geometry",),
    )
    SPEC = _replace(SPEC, source_dependencies=())


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
        return np.where(inside_line, parameters["intensity"], 0.5)
    
    
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
    SPEC = _replace(SPEC, source_dependencies=())


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
        return .5 + .5 * parameters["contrast"] * envelope * carrier
    
    
    SPEC = StimulusSpec("teaching_gabor", "Teaching Gabor", "Gaussian-windowed grating; degrees and digital contrast.",
        "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS,
        default_config="configs/stimuli/teaching_gabor.json", family="orientation_patch", render=render,
        calibration_requirements=("geometry",))
    SPEC = _replace(SPEC, source_dependencies=())


class ComposedScene(LibraryStimulus):
    """A registered adapter from a Scene recipe to the existing raster backend.

    Compose fixtures, lines, gratings and elliptical surrounds in experiment
    procedures. All drawing mathematics remain in THIS stimulus library.
    """

    @staticmethod
    def scene(parameters):
        return Scene.from_dict(json.loads(parameters["scene_json"]))

    @staticmethod
    def validate(parameters):
        ComposedScene.scene(parameters).parameters(parameters["size_deg"])

    @staticmethod
    def render(parameters, x_deg, y_deg):
        return ComposedScene.scene(parameters).render(x_deg, y_deg)

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
        return np.where(inside_line, parameters["intensity"], 0.5)
    
    
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
    SPEC = _replace(SPEC, source_dependencies=())


def library_stimulus_specs():
    """Discover explicitly subclassed shared definitions only."""
    specifications = tuple(cls.SPEC for cls in LibraryStimulus.__subclasses__())
    if len({spec.id for spec in specifications}) != len(specifications):
        raise ValueError("Shared stimulus classes require unique SPEC.id values.")
    return specifications
