"""Read-only monitor calibration stage indicators.

A green page records setup completion independently of explicit laboratory
verification; displaying a software stimulus is never photometry or
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
    def description(key, item):
        if key == "review":
            return ("SETUP COMPLETE; " if item["completed"] else "SETUP INCOMPLETE; ") + item["message"]
        if key == "spatial" and item["completed"]:
            return "RESEARCHER-REVIEWED VISUAL CONSISTENCY; NOT INDEPENDENT PHYSICAL CERTIFICATION: " + item["message"]
        if key == "bind" and item["completed"]:
            return "CONFIGURATION SAVED: " + item["message"]
        status = ("STAGE SAVED; VERIFICATION PENDING" if item["completed"] and not item["ready"]
                  else "STAGE SAVED; MANUALLY DECLARED VERIFIED" if item["completed"] and item["ready"]
                  else item["state"].upper().replace("_", " "))
        return status + ": " + item["message"]
    return {key: (item["completed"], description(key, item)) for key, item in progress.items()}
