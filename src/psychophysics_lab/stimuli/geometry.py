"""Reusable geometry helpers for simple display-validation stimuli.

This module deliberately contains no Pyglet import.  Its calculations are pure
and can be tested headlessly.  Physical rendering remains a laboratory check.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from ..config.models import MonitorProfile


@dataclass(frozen=True)
class WhiteBarStimulus:
    """Resolved white-bar geometry for a fullscreen display check."""

    orientation: str
    length_px: int
    thickness_px: int
    requested_mode: str
    requested_value: float
    intended_length_mm: float
    realised_length_mm: float
    realised_visual_angle_deg: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def physical_length_for_visual_angle(angle_deg: float, viewing_distance_m: float) -> float:
    """Return the chord length on the display required to subtend ``angle_deg``.

    The returned value is in metres and uses the symmetric visual-angle relation
    ``L = 2 d tan(theta / 2)``.
    """
    angle = float(angle_deg)
    distance = float(viewing_distance_m)
    if not math.isfinite(angle) or angle <= 0 or angle >= 180:
        raise ValueError("Visual angle must be finite and between 0 and 180 degrees.")
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("Viewing distance must be a positive finite value.")
    return 2.0 * distance * math.tan(math.radians(angle) / 2.0)


def visual_angle_for_physical_length(length_m: float, viewing_distance_m: float) -> float:
    length = float(length_m)
    distance = float(viewing_distance_m)
    if not math.isfinite(length) or length < 0:
        raise ValueError("Physical length must be finite and non-negative.")
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("Viewing distance must be a positive finite value.")
    return math.degrees(2.0 * math.atan(length / (2.0 * distance)))


def pixels_for_physical_length(length_m: float, physical_extent_m: float, pixel_extent: int) -> int:
    length = float(length_m)
    extent = float(physical_extent_m)
    pixels = int(pixel_extent)
    if not math.isfinite(length) or length <= 0:
        raise ValueError("Requested physical length must be positive and finite.")
    if not math.isfinite(extent) or extent <= 0 or pixels <= 0:
        raise ValueError("Display extent and pixel resolution must be positive.")
    return max(1, int(round((length / extent) * pixels)))


def physical_length_for_pixels(pixel_length: int, physical_extent_m: float, pixel_extent: int) -> float:
    pixels = int(pixel_length)
    extent = float(physical_extent_m)
    screen_pixels = int(pixel_extent)
    if pixels < 0 or not math.isfinite(extent) or extent <= 0 or screen_pixels <= 0:
        raise ValueError("Pixel length, display extent and resolution are invalid.")
    return (pixels / screen_pixels) * extent


def _axes(profile: MonitorProfile, resolution_px: tuple[int, int], orientation: str):
    orientation = str(orientation).strip().lower()
    if orientation not in {"horizontal", "vertical"}:
        raise ValueError("Orientation must be 'horizontal' or 'vertical'.")
    width_px, height_px = (int(resolution_px[0]), int(resolution_px[1]))
    if width_px <= 0 or height_px <= 0:
        raise ValueError("Fullscreen resolution must contain positive dimensions.")
    if orientation == "horizontal":
        return (
            profile.physical_width_m,
            width_px,
            profile.physical_height_m,
            height_px,
        )
    return (
        profile.physical_height_m,
        height_px,
        profile.physical_width_m,
        width_px,
    )


def resolve_white_bar(
    *,
    profile: MonitorProfile,
    resolution_px: tuple[int, int],
    mode: str,
    value: float,
    orientation: str = "horizontal",
    thickness_mm: float = 5.0,
) -> WhiteBarStimulus:
    """Resolve a physical-length or visual-angle white bar to screen pixels."""
    mode = str(mode).strip().lower()
    requested = float(value)
    if mode == "physical_mm":
        if requested <= 0 or not math.isfinite(requested):
            raise ValueError("Physical bar length must be a positive finite number of millimetres.")
        intended_m = requested / 1000.0
    elif mode == "visual_angle_deg":
        intended_m = physical_length_for_visual_angle(requested, profile.viewing_distance_m)
    else:
        raise ValueError("Bar mode must be 'physical_mm' or 'visual_angle_deg'.")

    length_extent_m, length_extent_px, thickness_extent_m, thickness_extent_px = _axes(
        profile, resolution_px, orientation
    )
    if intended_m > length_extent_m:
        raise ValueError(
            f"Requested bar needs {intended_m * 1000:.2f} mm but the selected "
            f"screen axis is only {length_extent_m * 1000:.2f} mm."
        )

    thickness_m = float(thickness_mm) / 1000.0
    if not math.isfinite(thickness_m) or thickness_m <= 0:
        raise ValueError("Bar thickness must be a positive finite number of millimetres.")
    if thickness_m > thickness_extent_m:
        raise ValueError("Bar thickness exceeds the selected display dimension.")

    length_px = pixels_for_physical_length(intended_m, length_extent_m, length_extent_px)
    thickness_px = pixels_for_physical_length(
        thickness_m, thickness_extent_m, thickness_extent_px
    )
    realised_m = physical_length_for_pixels(length_px, length_extent_m, length_extent_px)
    realised_angle = visual_angle_for_physical_length(realised_m, profile.viewing_distance_m)

    return WhiteBarStimulus(
        orientation=str(orientation).strip().lower(),
        length_px=length_px,
        thickness_px=thickness_px,
        requested_mode=mode,
        requested_value=requested,
        intended_length_mm=intended_m * 1000.0,
        realised_length_mm=realised_m * 1000.0,
        realised_visual_angle_deg=realised_angle,
    )


def geometry_reference_table(
    profile: MonitorProfile,
    resolution_px: tuple[int, int],
    *,
    angles_deg: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0, 10.0),
) -> list[dict[str, float | int]]:
    """Return a compact horizontal angle→millimetre→pixel reference table."""
    rows: list[dict[str, float | int]] = []
    for angle in angles_deg:
        bar = resolve_white_bar(
            profile=profile,
            resolution_px=resolution_px,
            mode="visual_angle_deg",
            value=angle,
            orientation="horizontal",
        )
        rows.append(
            {
                "visual_angle_deg": float(angle),
                "intended_length_mm": bar.intended_length_mm,
                "length_px": bar.length_px,
                "realised_length_mm": bar.realised_length_mm,
                "realised_visual_angle_deg": bar.realised_visual_angle_deg,
            }
        )
    return rows
