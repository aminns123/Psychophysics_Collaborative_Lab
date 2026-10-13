"""Conservative digital-range guard for the existing box=False shader.

The production formula is RGB = bg + envelope*C_disp*sin(phase)/2.
This guard does not clamp contrast or infer physical luminance. Human
presentation fails before drawing any out-of-range modulation; synthetic
staircases retain the legacy unconstrained numeric update for diagnosis.
"""
import math


def grating_command_bounds(contrast, background):
    if any(isinstance(v, bool) or not math.isfinite(v) for v in (contrast, background)):
        raise ValueError("Grating contrast and background must be finite numbers.")
    if contrast < 0 or not 0 <= background <= 1:
        raise ValueError("Grating contrast must be nonnegative and background must be in [0, 1].")
    return background - contrast / 2., background + contrast / 2.


def validate_grating_command(contrast, background):
    lower, upper = grating_command_bounds(contrast, background)
    if lower < -1e-15 or upper > 1 + 1e-15:
        limit = 2 * min(background, 1 - background)
        raise ValueError(f"Grating command may clip: conservative RGB range {lower:.6g}–{upper:.6g}, "
            f"valid range 0–1. For background {background:g}, C_disp must be <= {limit:g}. "
            "Review starting intensity/steps and the laboratory contrast policy. No contrast was clamped.")
    return lower, upper
