"""Bright-on-background display-contrast conversion, in digital command units.

This convention uses *remaining upper digital headroom*, not Weber luminance
contrast, and is not a substitute for physical photometric qualification.

    C_disp = (I_stim - I_background) / (1 - I_background)
    I_stim = I_background + C_disp * (1 - I_background)

The functions do not re-interpret legacy probe increments, adaptive states,
grating peak-to-peak amplitudes or previously recorded threshold columns.
Scientific experiment migration to these units must be reviewed separately.
"""

from __future__ import annotations

import math


def _finite_number(value, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not a boolean.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")
    return result


def _background(value) -> float:
    background = _finite_number(value, name="background intensity")
    if not 0 <= background < 1:
        raise ValueError(
            "Bright display contrast requires a digital background in [0, 1)."
        )
    return background


def bright_display_contrast_to_increment(contrast, background) -> float:
    """Convert headroom-normalized contrast to a positive digital increment.

    Inputs are normalized digital commands, not optical luminances. No clamping
    is performed: values outside the declared scientific range are rejected.
    """
    base = _background(background)
    contrast = _finite_number(contrast, name="display contrast")
    if not 0 <= contrast <= 1:
        raise ValueError("Bright display contrast must be in [0, 1].")
    return contrast * (1 - base)


def bright_display_contrast_to_intensity(contrast, background) -> float:
    """Return the normalized pixel command for a brighter-than-background mark."""
    base = _background(background)
    return base + bright_display_contrast_to_increment(contrast, base)


def increment_to_bright_display_contrast(increment, background) -> float:
    """Describe a legacy positive digital increment in the proposed new units.

    This does NOT convert historical stored observations in place. The caller
    must track which convention was selected for each acquisition.
    """
    base = _background(background)
    increment = _finite_number(increment, name="digital increment")
    if not 0 <= increment <= 1 - base:
        raise ValueError("Digital increment must lie in available upper headroom.")
    return increment / (1 - base)


def intensity_to_bright_display_contrast(intensity, background) -> float:
    """Convert an absolute digital mark intensity to the new bright convention."""
    base = _background(background)
    intensity = _finite_number(intensity, name="stimulus intensity")
    if not base <= intensity <= 1:
        raise ValueError("Stimulus intensity must be between background and 1.")
    return increment_to_bright_display_contrast(intensity - base, base)
