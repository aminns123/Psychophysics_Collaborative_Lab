"""Read-only monitor calibration stage indicators.

A green status is based on matching saved laboratory evidence and explicit
human verification; displaying a software stimulus is never photometry or
photon-onset verification. No file in this module changes certification.
"""
from __future__ import annotations

from pathlib import Path



STAGES = (
    ("bind", "1 · Display"),
    ("geometry", "2 · Geometry"),
    ("spatial", "3 · Spatial"),
    ("luminance", "4 · Luminance"),
    ("timing", "5 · Timing"),
    ("review", "6 · Review"),
)


def stage_states(profile, local_config_root: Path) -> dict[str, tuple[bool, str]]:
    from ..config.calibration_progress import calibration_progress
    return {key: (value["ready"], f"{value['state'].upper().replace('_', ' ')}: {value['message']}")
            for key, value in calibration_progress(profile, local_config_root).items()}
