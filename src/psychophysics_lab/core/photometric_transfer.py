"""Measured monotonic luminance transfer; never inferred from digital commands."""

import numpy as np


def commands_for_luminance(requested, commands, measured_cd_m2):
    commands = np.asarray(commands, dtype=float)
    luminance = np.asarray(measured_cd_m2, dtype=float)
    requested = np.asarray(requested, dtype=float)
    if commands.ndim != 1 or len(commands) < 3 or luminance.shape != commands.shape:
        raise ValueError("Provide at least three paired measured luminance samples.")
    if not all(np.isfinite(x).all() for x in (commands, luminance, requested)):
        raise ValueError("Transfer inputs must be finite.")
    if (
        np.any(np.diff(commands) <= 0)
        or np.any(np.diff(luminance) <= 0)
        or commands[0] < 0
        or commands[-1] > 1
        or luminance[0] < 0
    ):
        raise ValueError(
            "Measured transfer must be strictly increasing, with commands in [0,1]."
        )
    if np.any(requested < luminance[0]) or np.any(requested > luminance[-1]):
        raise ValueError(
            "Requested luminance is outside the measured gamut; no extrapolation/clipping."
        )
    return np.interp(requested, luminance, commands)
