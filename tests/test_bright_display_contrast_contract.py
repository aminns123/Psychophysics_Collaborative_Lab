"""Mathematical contract for proposed bright-on-background display contrast.

These tests deliberately do not assert that existing recorded probe increments
or CSF peak-to-peak modulation have silently changed conventions.
"""
import math

import pytest

from psychophysics_lab.methods.display_contrast import (
    bright_display_contrast_to_increment,
    bright_display_contrast_to_intensity,
    increment_to_bright_display_contrast,
    intensity_to_bright_display_contrast,
)


@pytest.mark.parametrize(
    "background,contrast,increment,intensity",
    [
        (0, 0, 0, 0),
        (0, 0.5, 0.5, 0.5),
        (0.25, 0.5, 0.375, 0.625),
        (0.5, 0.05, 0.025, 0.525),
        (0.75, 1, 0.25, 1),
        (0.9, 0.1, 0.01, 0.91),
    ],
)
def test_bright_display_contrast_definition(background, contrast, increment, intensity):
    assert bright_display_contrast_to_increment(contrast, background) == pytest.approx(increment)
    assert bright_display_contrast_to_intensity(contrast, background) == pytest.approx(intensity)
    assert increment_to_bright_display_contrast(increment, background) == pytest.approx(contrast)
    assert intensity_to_bright_display_contrast(intensity, background) == pytest.approx(contrast)


@pytest.mark.parametrize("bad", [-0.01, 1.01, float("nan"), float("inf"), True, None])
def test_reject_invalid_display_contrasts(bad):
    with pytest.raises(ValueError):
        bright_display_contrast_to_increment(bad, .25)


@pytest.mark.parametrize("bad", [-0.01, 1, 1.1, float("nan"), float("-inf"), False])
def test_reject_invalid_bright_backgrounds(bad):
    with pytest.raises(ValueError):
        bright_display_contrast_to_intensity(.5, bad)


@pytest.mark.parametrize("bad", [-.01, .76, float("nan"), True])
def test_reject_increment_outside_headroom(bad):
    with pytest.raises(ValueError):
        increment_to_bright_display_contrast(bad, .25)


def test_no_implicit_weber_equivalence():
    background = .25
    requested = .5
    intensity = bright_display_contrast_to_intensity(requested, background)
    # Digital headroom normalization differs from digital Weber (and from
    # physical Weber, which additionally requires measured luminance).
    digital_weber_like = (intensity - background) / background
    assert intensity == pytest.approx(.625)
    assert digital_weber_like == pytest.approx(1.5)
    assert requested != pytest.approx(digital_weber_like)
