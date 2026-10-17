"""Private, stable Scene rasterisation for legacy composition recipes.

This module is framework infrastructure, NOT a second stimulus-authoring file.
Researchers add a complete LibraryStimulus class solely to
psychophysics_lab/stimulus_library.py. Existing Scene functions remain here to
preserve the mathematics and serialized recipes used by historical experiments.

Do not add new shape definitions here: create a standalone stimulus class in
the public library instead, and compose available primitives when appropriate.
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


