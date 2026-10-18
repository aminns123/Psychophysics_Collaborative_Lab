"""Explicit migration of old input names; saved session files are never rewritten."""
import math


def migrate_probe_intensity(values):
    """Old starting_contrast meant an increment, never an absolute intensity."""
    values = dict(values)
    if "starting_contrast" not in values:
        return values
    raw = values.pop("starting_contrast")
    if isinstance(raw, bool) or isinstance(values.get("background_intensity"), bool):
        raise ValueError("Legacy probe increment and background must be numbers, not booleans.")
    increment = float(raw)
    background = float(values.get("background_intensity", .5))
    intensity = background + increment
    if not math.isfinite(increment) or increment < 0 or not math.isfinite(intensity):
        raise ValueError("Legacy starting_contrast must be a finite nonnegative digital increment.")
    if increment > 0 and intensity == background:
        raise ValueError("Legacy increment is too small to express as an absolute starting intensity; retain the original settings and choose an explicit representable intensity.")
    if "starting_probe_intensity" in values and float(values["starting_probe_intensity"]) != intensity:
        raise ValueError("Both starting_probe_intensity and legacy starting_contrast are present and disagree. Keep one explicitly named setting.")
    values["starting_probe_intensity"] = intensity
    return values
