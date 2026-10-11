from __future__ import annotations

import json
from pathlib import Path

from .models import LuminanceCalibrationPoint, MonitorProfile
from ..paths import find_repo_root
from .local import config_root
import warnings


def _profile_from_dict(data: dict) -> MonitorProfile:
    if not isinstance(data, dict):
        raise ValueError("Monitor profile must contain a JSON object.")
    calibration_data = data.get("luminance_calibration", [])
    if not isinstance(calibration_data, list) or any(not isinstance(item, dict) for item in calibration_data):
        raise ValueError("Luminance calibration must be a list of measurement objects.")
    qualifications = data.get("qualified_experiments", [])
    if not isinstance(qualifications, (list, tuple)) or any(not isinstance(item, str) for item in qualifications):
        raise ValueError("Qualified experiments must be a list of experiment IDs.")
    numeric = ("physical_width_m", "physical_height_m", "refresh_rate_hz", "viewing_distance_m", "pyglet_wakeup_rate_hz")
    if any(isinstance(data.get(key), bool) for key in numeric):
        raise ValueError("Display dimensions and rates must be numbers, not booleans.")
    resolution = data.get("expected_resolution_px")
    if resolution is not None:
        if not isinstance(resolution, (list, tuple)) or len(resolution) != 2 or any(type(x) is not int for x in resolution):
            raise ValueError("Resolution must be two integer pixel dimensions.")
        resolution = tuple(resolution)

    if any(isinstance(item.get(key), bool) for item in data.get("luminance_calibration", []) for key in ("screen_intensity", "luminance_cdm2")):
        raise ValueError("Calibration points must contain measured numbers, not booleans.")
    calibration = tuple(
        LuminanceCalibrationPoint(
            screen_intensity=float(item["screen_intensity"]),
            luminance_cdm2=float(item["luminance_cdm2"]),
        )
        for item in data.get("luminance_calibration", [])
    )

    profile = MonitorProfile(
        id=str(data["id"]),
        display_name=str(data["display_name"]),
        physical_width_m=float(data["physical_width_m"]),
        physical_height_m=float(data["physical_height_m"]),
        refresh_rate_hz=float(data["refresh_rate_hz"]),
        viewing_distance_m=float(data["viewing_distance_m"]),
        pyglet_wakeup_rate_hz=float(data.get("pyglet_wakeup_rate_hz", data["refresh_rate_hz"])),
        expected_resolution_px=resolution,
        notes=str(data.get("notes", "")),
        calibration_status=str(data.get("calibration_status", "unverified")),
        luminance_calibration=calibration,
        calibration_notes=str(data.get("calibration_notes", "")),
        profile_uuid=str(data.get("profile_uuid", "")),
        revision=data.get("revision", 0),
        origin=str(data.get("origin", "reference")),
        display_binding=data.get("display_binding"),
        qualified_experiments=tuple(data.get("qualified_experiments", [])),
        calibration_method=str(data.get("calibration_method", "")),
        calibration_date=str(data.get("calibration_date", "")),
        geometry_status=str(data.get("geometry_status", "unverified")),
        timing_status=str(data.get("timing_status", "unverified")),
        measurement_sources=data.get("measurement_sources", {}),
    )
    profile.validate()
    return profile


def load_monitor_profiles(repo_root: Path | None = None) -> dict[str, MonitorProfile]:
    root = repo_root or find_repo_root()
    directory = root / "configs" / "monitors"
    if not directory.exists():
        raise FileNotFoundError(f"Monitor profile directory does not exist: {directory}")

    profiles: dict[str, MonitorProfile] = {}
    for path in sorted(directory.glob("*.json")):
        profile = _profile_from_dict(json.loads(path.read_text(encoding="utf-8")))
        if profile.id in profiles:
            raise ValueError(f"Duplicate monitor profile id: {profile.id}")
        profiles[profile.id] = profile

    local_directory = config_root(root) / "profiles"
    for directory in sorted(local_directory.glob("*")):
        revisions = sorted(directory.glob("revision_*.json"))
        if not revisions:
            continue
        try:
            profile = _profile_from_dict(json.loads(revisions[-1].read_text(encoding="utf-8")))
            if profile.id in profiles:
                raise ValueError(f"Local profile conflicts with reference id: {profile.id}")
            if profile.origin != "local" or profile.id != directory.name:
                raise ValueError("Local profile identity/origin differs from its directory.")
            profiles[profile.id] = profile
        except (OSError, ValueError, KeyError, TypeError) as exc:
            warnings.warn(f"Local display profile unavailable: {directory.name}: {exc}", RuntimeWarning)

    if not profiles:
        raise RuntimeError("No PsyCoLab monitor profiles were found.")
    return profiles
