"""Reusable trial-strength selection policies for researcher experiments.

See contrast.py for the intentionally small public interface. A method chooses
the next strength; the experiment defines stimuli, display commands and trials.
"""
from .contrast import (
    AdaptiveContrastMethod,
    ConstantContrastMethod,
    fixed_level_schedule,
    select_contrast_method,
)

__all__ = [
    "AdaptiveContrastMethod",
    "ConstantContrastMethod",
    "fixed_level_schedule",
    "select_contrast_method",
]
