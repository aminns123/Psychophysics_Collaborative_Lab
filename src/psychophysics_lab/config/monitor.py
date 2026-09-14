from __future__ import annotations

import json
from pathlib import Path

from .models import MonitorProfile
from ..paths import find_repo_root


def _profile_from_dict(data: dict) -> MonitorProfile:
    resolution = data.get("expected_resolution_px")
    if resolution is not None:
        resolution = (int(resolution[0]), int(resolution[1]))

    profile = MonitorProfile(
        id=str(data["id"]),
        display_name=str(data["display_name"]),
        physical_width_m=float(data["physical_width_m"]),
        physical_height_m=float(data["physical_height_m"]),
        refresh_rate_hz=int(data["refresh_rate_hz"]),
        viewing_distance_m=float(data["viewing_distance_m"]),
        pyglet_wakeup_rate_hz=int(data.get("pyglet_wakeup_rate_hz", data["refresh_rate_hz"])),
        expected_resolution_px=resolution,
        notes=str(data.get("notes", "")),
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

    if not profiles:
        raise RuntimeError("No PsyCoLab monitor profiles were found.")
    return profiles
