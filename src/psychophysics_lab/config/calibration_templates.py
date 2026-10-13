"""Researcher-editable luminance measurement files, not automatic calibration.

Templates contain no fabricated photometer readings. Real intensity/luminance
pairs can be imported without optional instrument notes. Import always creates
an unverified draft; laboratory verification remains explicit.
"""
from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path

from .models import LuminanceCalibrationPoint, MonitorProfile
from ..data.locking import file_lock
from ..data.session import atomic_write_json

FORMAT = "psycolab.luminance.measurements"
VERSION = 1
MAX_IMPORT_BYTES = 128 * 1024


def template_identity(profile: MonitorProfile) -> tuple[str, int]:
    """Shared reference becomes a *new* local copy; local revisions stay pinned."""
    return (
        profile.id if profile.origin == "local" else profile.id + "_local",
        profile.revision if profile.origin == "local" else 0,
    )


def example_luminance_document(profile: MonitorProfile) -> dict:
    """Make a valid JSON file whose null readings are impossible to import."""
    profile_id, revision = template_identity(profile)
    return {
        "format": FORMAT,
        "schema_version": VERSION,
        "monitor_profile_id": profile_id,
        "based_on_revision": revision,
        "photometer_model_and_method": "REPLACE_WITH_REAL_METER_AND_MEASUREMENT_METHOD",
        "measurement_date": "YYYY-MM-DD",
        "notes": (
            "REPLACE: monitor brightness, measurement geometry, aperture, "
            "warm-up, ambient light, uncertainty, equipment serial/reference "
            "and any applied transfer-function settings."
        ),
        "measurements": [
            {"screen_intensity": command, "luminance_cdm2": None}
            for command in (0.0, 0.25, 0.5, 0.75, 1.0)
        ],
        "instructions": (
            "Replace at least TWO null luminance_cdm2 values with REAL cd/m² "
            "measurements at distinct digital commands. Unfilled null rows are "
            "ignored. Method, date and notes are recommended but OPTIONAL: "
            "leaving placeholders produces warnings, not an import failure. "
            "Inspect the imported draft, Save local revision and review "
            "laboratory verification separately. Never copy fake example data."
        ),
    }


def write_luminance_example(local_config_root: Path, profile: MonitorProfile) -> Path:
    """Create a local editable file without ever overwriting an existing one."""
    profile_id, revision = template_identity(profile)
    destination = (
        local_config_root / "calibration_templates" /
        f"luminance_{profile_id}_rev{revision:06d}.json"
    ).resolve()
    root = local_config_root.resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Calibration template path must stay inside local configuration.")
    with file_lock(root / "calibration_templates.lock"):
        if not destination.exists() and not destination.is_symlink():
            atomic_write_json(destination, example_luminance_document(profile))
    return destination


def _measured_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a measured JSON number (not null or example text).")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{label} must be finite.")
    return x


def parse_luminance_measurements(data: object, profile: MonitorProfile) -> dict:
    """Validate an imported measurement document without asserting certification."""
    if not isinstance(data, dict) or data.get("format") != FORMAT or data.get("schema_version") != VERSION:
        raise ValueError("Expected a PsyCoLab luminance measurements JSON object (use Create example JSON).")
    profile_id, revision = template_identity(profile)
    if data.get("monitor_profile_id") != profile_id or data.get("based_on_revision") != revision:
        raise ValueError(
            f"Measurements were prepared for another profile/revision. "
            f"Expected {profile_id} revision {revision}. Create a fresh example "
            "for this display and transfer verified measurements only after checking identity."
        )
    if data.get("example_only") is True:
        raise ValueError("FAKE demonstration values cannot be imported as photometer measurements.")
    warnings = []
    method = data.get("photometer_model_and_method")
    method = method.strip() if isinstance(method, str) else ""
    if not method or "REPLACE" in method.upper():
        method = ""
        warnings.append("Photometer/method not recorded; add it later for reproducibility.")

    date_text = data.get("measurement_date")
    date_text = date_text.strip() if isinstance(date_text, str) else ""
    if date_text in ("YYYY-MM-DD", "REPLACE") or not date_text:
        date_text = ""
        warnings.append("Measurement date not recorded; add it later if known.")
    else:
        try:
            date.fromisoformat(date_text)
        except ValueError as exc:
            raise ValueError("Measurement date must be YYYY-MM-DD, or left blank.") from exc

    notes = data.get("notes")
    notes = notes.strip() if isinstance(notes, str) else ""
    if not notes or "REPLACE" in notes.upper():
        notes = ""
        warnings.append("Measurement notes not recorded; add setup details later if available.")

    pairs = data.get("measurements")
    if not isinstance(pairs, list) or len(pairs) < 2:
        raise ValueError("Provide at least two measured digital-command/luminance pairs.")
    points = []
    ignored = 0
    for index, row in enumerate(pairs, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Measurement row {index} must be an object.")
        # Blank rows from the starter template are not observations. They
        # should not prevent importing the OTHER, actually measured rows.
        if row.get("luminance_cdm2") is None:
            ignored += 1
            continue
        command = _measured_number(row.get("screen_intensity"), f"Row {index} screen_intensity")
        luminance = _measured_number(row.get("luminance_cdm2"), f"Row {index} luminance_cdm2")
        point = LuminanceCalibrationPoint(command, luminance)
        point.validate()
        points.append(point)
    if len(points) < 2:
        raise ValueError("At least two REAL intensity/luminance measurements are required; blank template rows do not count.")
    if ignored:
        warnings.append(f"Ignored {ignored} blank template row(s) without a luminance reading.")
    commands = [p.screen_intensity for p in points]
    measured = [p.luminance_cdm2 for p in points]
    if len(set(commands)) != len(commands) or len(set(measured)) != len(measured):
        raise ValueError("Commands and measured luminance values must each be distinct.")
    ordered = sorted(points, key=lambda point: point.screen_intensity)
    if any(a.luminance_cdm2 >= b.luminance_cdm2 for a,b in zip(ordered, ordered[1:])):
        raise ValueError("Measured luminance must increase monotonically with the digital command.")
    return {
        "luminance_calibration": [
            {"screen_intensity": point.screen_intensity,
             "luminance_cdm2": point.luminance_cdm2}
            for point in ordered
        ],
        "calibration_method": method.strip(),
        "calibration_date": date_text,
        "calibration_notes": notes,
        "calibration_status": "manual_unverified",
        "warnings": warnings,
    }


def read_luminance_measurements(path: str, profile: MonitorProfile) -> dict:
    """Read a small, explicit researcher-selected JSON path; never writes files."""
    if not path.strip():
        raise ValueError("Enter the path to your completed luminance JSON file.")
    target = Path(path.strip().strip('"')).expanduser().resolve()
    if not target.is_file():
        raise ValueError(f"Luminance measurements file does not exist: {target}")
    if target.stat().st_size > MAX_IMPORT_BYTES:
        raise ValueError("Luminance JSON exceeds 128 KiB. Use a small measurement table.")
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid UTF-8 JSON file: {exc}") from exc
    return parse_luminance_measurements(document, profile)


def demo_luminance_document(profile: MonitorProfile) -> dict:
    """Visibly synthetic completed example, blocked by the production importer."""
    example = example_luminance_document(profile)
    example.update({
        "example_only": True,
        "photometer_model_and_method": "FAKE EXAMPLE - imaginary photometer, NOT A REAL MEASUREMENT",
        "measurement_date": "2026-01-01",
        "notes": "FAKE EXAMPLE ONLY. Demonstrates JSON structure. Do not use for an experiment.",
        "measurements": [
            {"screen_intensity": 0.0, "luminance_cdm2": 0.2},
            {"screen_intensity": 0.25, "luminance_cdm2": 13.4},
            {"screen_intensity": 0.50, "luminance_cdm2": 57.2},
            {"screen_intensity": 0.75, "luminance_cdm2": 110.8},
            {"screen_intensity": 1.0, "luminance_cdm2": 181.5},
        ],
        "instructions": (
            "FAKE DEMONSTRATION DATA, NOT YOUR SCREEN. example_only=true prevents "
            "import. For real calibration, create the blank measurement template, "
            "take photometer measurements and replace null values with observations."
        ),
    })
    return example


def write_luminance_demo(local_config_root: Path, profile: MonitorProfile) -> Path:
    """Write a sample on demand without overwriting user-entered data."""
    profile_id, revision = template_identity(profile)
    root = local_config_root.resolve()
    destination = (root / "calibration_templates" /
                   f"FAKE_DEMO_luminance_{profile_id}_rev{revision:06d}.json").resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Demo path must remain inside local configuration.")
    with file_lock(root / "calibration_templates.lock"):
        if not destination.exists() and not destination.is_symlink():
            atomic_write_json(destination, demo_luminance_document(profile))
    return destination
