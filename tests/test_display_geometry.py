import math

import pytest

from psychophysics_lab.config.models import MonitorProfile
from psychophysics_lab.stimuli.geometry import (
    physical_length_for_visual_angle,
    resolve_white_bar,
    visual_angle_for_physical_length,
)


def profile():
    return MonitorProfile(
        id="test_display",
        display_name="Test display",
        physical_width_m=0.610,
        physical_height_m=0.350,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
    )


def test_visual_angle_roundtrip_is_geometrically_consistent():
    for angle in (0.5, 1.0, 2.0, 5.0, 10.0):
        length = physical_length_for_visual_angle(angle, 1.0)
        assert visual_angle_for_physical_length(length, 1.0) == pytest.approx(angle)


def test_physical_bar_resolves_against_selected_screen_axis():
    bar = resolve_white_bar(
        profile=profile(),
        resolution_px=(1920, 1080),
        mode="physical_mm",
        value=100.0,
        orientation="horizontal",
        thickness_mm=5.0,
    )
    expected_pixels = round((0.100 / 0.610) * 1920)
    assert bar.length_px == expected_pixels
    assert bar.realised_length_mm == pytest.approx(expected_pixels / 1920 * 610)


def test_visual_angle_mode_reports_pixel_rounding_not_false_exactness():
    bar = resolve_white_bar(
        profile=profile(),
        resolution_px=(1920, 1080),
        mode="visual_angle_deg",
        value=5.0,
        orientation="horizontal",
    )
    assert bar.intended_length_mm == pytest.approx(
        2000 * math.tan(math.radians(5.0) / 2.0)
    )
    assert abs(bar.realised_visual_angle_deg - 5.0) < 0.05


def test_impossible_bar_is_rejected():
    with pytest.raises(ValueError):
        resolve_white_bar(
            profile=profile(),
            resolution_px=(1920, 1080),
            mode="physical_mm",
            value=1000.0,
        )
