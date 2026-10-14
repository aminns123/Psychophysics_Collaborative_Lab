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


def stage_next_action(stage: str, progress: dict) -> str:
    """A short, researcher-facing next action, separate from certification."""
    item = progress[stage]
    if stage == 'bind':
        return ('NEXT: Open Bind / edit, select the actual display and enter physical measurements.'
                if not item['completed'] else
                'Saved. NEXT: Choose Geometry → present the ruler and record its measured length.')
    if stage == 'geometry':
        if not item['software_completed']:
            return 'NEXT: Present the ruler bar fullscreen.'
        if not item['measurement_recorded']:
            return 'NEXT: Enter the physical ruler measurement (mm), then Record measurement.'
        return 'Saved. NEXT: Review the percentage error; choose Spatial when ready.'
    if stage == 'spatial':
        if not item['software_completed']:
            return 'NEXT: Launch the grating and inspect its visible cycles.'
        if not item['completed']:
            return 'NEXT: Select the report, record Yes / No / Uncertain and any abnormality.'
        return 'Observation saved. NEXT: Choose Luminance when ready.'
    if stage == 'luminance':
        return ('Saved test/photometer pairs remain available. NEXT: Choose Timing; '
                'real human acquisition still needs genuine photometry.'
                if item['completed'] else
                'NEXT: Open luminance readings. Choose TEST values or actual meter observations, '
                'then Add and Save. A photometer is NOT needed for software tests.')
    if stage == 'timing':
        return ('Saved. NEXT: Review; independent photon timing is a separate check.'
                if item['completed'] else
                'NEXT: Present a timing diagnostic; review software frames. '
                'Physical photon timing requires an external sensor.')
    if stage == 'review':
        return ('NEXT: Finish setup → Experiment for Test/Simulation. '
                'For human acquisition, review physical evidence and experiment qualification.')
    return ''
