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


def starting_contrast_limits(background, starting, up_step=None):
    """Existing box=False convention; no change to defaults or adaptive updates."""
    from Events.display_contrast import normalized_display_contrast, display_contrast_to_screen_intensity
    if any(isinstance(value,bool) or not math.isfinite(value) for value in (background,starting)) or not 0 <= background < 1:
        raise ValueError("Background must be finite in [0,1); starting intensity must be finite.")
    maximum_contrast = 2 * min(background, 1-background)
    maximum_starting = display_contrast_to_screen_intensity(maximum_contrast, background_intensity=background, maximum_intensity=1.)
    contrast = normalized_display_contrast(starting,background_intensity=background,maximum_intensity=1.)
    lower,upper = grating_command_bounds(contrast,background)
    try:
        validate_grating_command(contrast,background)
    except ValueError:
        valid=False
    else:
        valid=True
    next_up=None
    if up_step is not None:
        if isinstance(up_step,bool) or not math.isfinite(up_step) or up_step <= 0:
            raise ValueError("Upward log10 step must be positive and finite.")
        try:
            next_up=contrast*10**up_step
        except OverflowError:
            next_up=math.inf
    return {"background":background,"contrast":contrast,"maximum_contrast":maximum_contrast,
            "minimum_starting":background,"maximum_starting":maximum_starting,"rgb_bounds":(lower,upper),
            "initial_valid":valid,"next_up_would_exceed":next_up is not None and next_up > maximum_contrast,
            "boundary_policy":"Every human draw validates the planned contrast before OpenGL. An unsafe later step stops acquisition with error, preserving accepted records; no clamping or reversal rewrite. Synthetic numeric staircases remain unconstrained."}


def contrast_limit_text(background, starting, up_step=None):
    result=starting_contrast_limits(background,starting,up_step)
    return (f"With background {background:g}, the non-clipping starting probe range is {background:g}–{result['maximum_starting']:.6g}; "
            f"maximum C_disp is {result['maximum_contrast']:.6g} under the current shader. "
            f"Current starting command: {'valid' if result['initial_valid'] else 'OUT OF RANGE'}. "
            + ("The next upward step can exceed this range. " if result['next_up_would_exceed'] else "Later upward steps can still exceed this range. ")
            + result['boundary_policy'])
