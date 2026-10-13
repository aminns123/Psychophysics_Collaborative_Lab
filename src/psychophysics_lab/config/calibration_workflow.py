"""Chronological calibration navigation, driven by persisted observations.

A completed page represents SAVED evidence, not automatic laboratory certification.
Advance only when the requested stage has persisted; the user can always browse
pages manually, including when the lab lacks a photometer or photodiode.
"""
from __future__ import annotations

from pathlib import Path

from .calibration_progress import calibration_progress
from .local import save_preferences


ORDER = ("bind", "geometry", "spatial", "luminance", "timing", "review")


def next_stage(stage: str) -> str | None:
    if stage not in ORDER:
        raise ValueError(f"Unknown calibration stage: {stage}")
    index = ORDER.index(stage) + 1
    return ORDER[index] if index < len(ORDER) else None


def advance_if_completed(profile, local_config_root: Path, stage: str) -> str | None:
    """Persist the next page only after its predecessor has saved real evidence.

    Verification remains independent: e.g. recorded luminance pairs complete
    the acquisition step but do not certify photometry for human experiments.
    """
    following = next_stage(stage)
    if following is None:
        return None
    state = calibration_progress(profile, local_config_root)[stage]
    if not state["completed"]:
        return None
    save_preferences(local_config_root, calibration_active_stage=following)
    return following
