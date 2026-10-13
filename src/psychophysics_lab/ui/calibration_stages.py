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
    progress = calibration_progress(profile, local_config_root)
    return {
        key: (
            item["completed"],
            ("STAGE SAVED; VERIFICATION PENDING" if item["completed"] and not item["ready"]
             else "STAGE SAVED; VERIFICATION DECLARED OR REQUIREMENTS MET" if item["completed"] and item["ready"]
             else item["state"].upper().replace("_", " "))
            + ": " + item["message"]
        )
        for key, item in progress.items()
    }
