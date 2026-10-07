"""Reusable stimulus definitions and testable stimulus geometry."""

from .geometry import (
    WhiteBarStimulus,
    geometry_reference_table,
    physical_length_for_pixels,
    physical_length_for_visual_angle,
    pixels_for_physical_length,
    resolve_white_bar,
    visual_angle_for_physical_length,
)

__all__ = [
    "WhiteBarStimulus",
    "geometry_reference_table",
    "physical_length_for_pixels",
    "physical_length_for_visual_angle",
    "pixels_for_physical_length",
    "resolve_white_bar",
    "visual_angle_for_physical_length",
]
