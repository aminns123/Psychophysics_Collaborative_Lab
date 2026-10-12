"""Geometry-derived spatial-frequency calibration; no hardware or Pyglet imports.

Contrast, luminance (photometry), refresh and latency calibration are
independent of this geometric transformation. A monitor profile is an INPUT
measurement, not a verified calibration merely because numbers exist.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class SpatialGeometry:
    resolution_px: tuple[int, int]
    physical_size_m: tuple[float, float]
    viewing_distance_m: float
    pixel_pitch_m: tuple[float, float]
    pixels_per_degree_at_centre: tuple[float, float]
    nyquist_cpd_at_centre: tuple[float, float]
    geometry_status: str

    def to_dict(self):
        return asdict(self)


def resolve_spatial_geometry(profile, resolution_px: tuple[int, int]) -> SpatialGeometry:
    """Return independent x/y calibration for a flat display at the gaze centre.

    Derived pixel visual angle is arctan(pitch/distance) in degrees, not
    screen-wide FOV / N (which biases the local spatial frequency).
    """
    w, h = resolution_px
    if type(w) is not int or type(h) is not int or min(w, h) < 2:
        raise ValueError("Display pixel resolution must have two positive integer dimensions.")
    width, height, distance = (float(profile.physical_width_m), float(profile.physical_height_m),
                               float(profile.viewing_distance_m))
    if any(not math.isfinite(v) or v <= 0 for v in (width, height, distance)):
        raise ValueError("Physical screen width, height and viewing distance must be positive and finite.")
    pitch_x, pitch_y = width / w, height / h
    ppd_x = 1.0 / math.degrees(math.atan(pitch_x / distance))
    ppd_y = 1.0 / math.degrees(math.atan(pitch_y / distance))
    return SpatialGeometry((w, h), (width, height), distance, (pitch_x, pitch_y),
                           (ppd_x, ppd_y), (ppd_x / 2, ppd_y / 2),
                           str(profile.geometry_status))


def validate_requested_cpd(frequencies: tuple[float, ...], geometry: SpatialGeometry, *,
                           orientation_rad: float = 0.0) -> None:
    """Reject impossible frequencies by a conservative 2D pixel Nyquist bound."""
    # A grating oriented at theta changes phase by 2*pi*f*(cos(theta)*deg_x+
    # sin(theta)*deg_y). Each screen coordinate has an independent sampling bound.
    x_projection, y_projection = abs(math.cos(orientation_rad)), abs(math.sin(orientation_rad))
    for frequency in frequencies:
        if not math.isfinite(frequency) or frequency <= 0:
            raise ValueError("Spatial frequency in cycles/degree must be positive and finite.")
        if (frequency * x_projection >= geometry.nyquist_cpd_at_centre[0]
                or frequency * y_projection >= geometry.nyquist_cpd_at_centre[1]):
            raise ValueError(
                f"{frequency:g} cycles/degree exceeds the display's spatial sampling limit "
                f"({geometry.nyquist_cpd_at_centre[0]:.3g} horizontal, "
                f"{geometry.nyquist_cpd_at_centre[1]:.3g} vertical cpd)."
            )


def angle_deg_at_pixel(offset_px: float, pitch_m: float, distance_m: float) -> float:
    """Angular coordinate relative to gaze in one screen axis, exact flat-display geometry."""
    return math.degrees(math.atan(offset_px * pitch_m / distance_m))


def shader_radians_for_cpd_at_centre(cpd: float, grating_size_px: int, geometry: SpatialGeometry,
                                    orientation_rad: float = 0) -> float:
    """Expected local GLSL phase span across a normalised grating quad.

    Used only to audit renderer phase calibration. The production cpd shader
    evaluates atan per fragment, preserving the nonlinear eccentricity mapping.
    """
    return 2 * math.pi * cpd * grating_size_px * (
        abs(math.cos(orientation_rad)) / geometry.pixels_per_degree_at_centre[0]
        + abs(math.sin(orientation_rad)) / geometry.pixels_per_degree_at_centre[1]
    )
