"""Opt-in literature settings, not a universal optimum or a target guarantee.

García-Pérez (1998), Vision Research 38, 1861–1881,
doi:10.1016/S0042-6989(97)00340-4. Fixed steps in log stimulus strength,
2AFC with chance 0.5, one-up and one through four-down. See docs/ADAPTIVE_METHODS.md.
"""
import math

RATIOS = {1: 0.2845, 2: 0.5488, 3: 0.7393, 4: 0.8415}  # down / up
NOTICE = ("García-Pérez 1998 fixed log-step 2AFC setting; down/up is a step-size ratio, "
          "not the response-count ratio. Model-dependent; not a guaranteed target or universal optimum. "
          "Changing counts never changes your step sizes automatically.")


def paired_step(*, known_value, calculate, n_down, n_up, alternatives=2,
                parameterization="log10_display_contrast") -> float:
    if type(n_down) is not int or type(n_up) is not int or n_up != 1 or n_down not in RATIOS:
        raise ValueError("Literature calculation supports only 1-up and 1–4-down; enter steps manually for this rule.")
    if type(alternatives) is not int or alternatives != 2 or parameterization != "log10_display_contrast":
        raise ValueError("Unsupported or ambiguous step parameterization: requires 2AFC fixed log10 contrast steps.")
    if isinstance(known_value, bool):
        raise ValueError("Step size must be positive and finite.")
    value = float(known_value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Step size must be positive and finite.")
    if calculate not in {"up", "down"}:
        raise ValueError("Choose up or down as the calculated step.")
    result = value * RATIOS[n_down] if calculate == "down" else value / RATIOS[n_down]
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Calculated step is outside the finite numeric range.")
    return result


def bounded_log_step(value, exponent, *, maximum):
    """Apply a log10 step and saturate at the experiment's explicit upper bound.

    The positive floating-point floor prevents underflow to an absorbing zero:
    a subsequent upward step can still recover. This is numerical protection,
    not a perceptual threshold or a restriction to 8-bit display commands.
    Zero is retained by a hold/down command; an up command leaves it at the floor.
    A positive subnormal input keeps its smaller representable floor, so a
    down command never increases it to the normal-number floor.
    No intermediate power can overflow, even for very large valid step sizes.
    """
    import math
    import sys
    floor = sys.float_info.min
    if any(not math.isfinite(v) for v in (value, exponent, maximum)) or not 0 <= value <= maximum or maximum < floor:
        raise ValueError("Log staircase needs a finite strength within a positive finite bound.")
    if exponent == 0:
        return value
    if value == 0:
        return floor if exponent > 0 else 0.0
    # A supplied positive subnormal is valid within [0, maximum]. A down
    # step must never jump UP to the larger normal-number floor.
    floor = min(floor, value)
    proposed_log = math.log10(value) + exponent
    if proposed_log >= math.log10(maximum):
        return maximum
    if proposed_log <= math.log10(floor):
        return floor
    # Keep ordinary arithmetic identical to the existing experiment; the log
    # branch handles exponents whose intermediate power would overflow/underflow.
    return min(maximum, max(floor, value * 10**exponent if abs(exponent) < 300 else 10**proposed_log))
