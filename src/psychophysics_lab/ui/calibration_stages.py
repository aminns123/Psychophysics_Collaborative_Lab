"""Read-only monitor calibration stage indicators.

A green status is based on matching saved laboratory evidence and explicit
human verification; displaying a software stimulus is never photometry or
photon-onset verification. No file in this module changes certification.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config.readiness import diagnostic_matches_profile


STAGES = (
    ("bind", "1 · Display"),
    ("geometry", "2 · Geometry"),
    ("spatial", "3 · Spatial"),
    ("luminance", "4 · Luminance"),
    ("timing", "5 · Timing"),
    ("review", "6 · Review"),
)


def stage_states(profile, local_config_root: Path) -> dict[str, tuple[bool, str]]:
    sources = profile.measurement_sources
    manual_geometry = all(
        sources.get(field) == "manual"
        for field in ("physical_width_m", "physical_height_m", "viewing_distance_m")
    )
    bound = (
        profile.origin == "local" and bool(profile.display_binding)
        and profile.expected_resolution_px is not None and manual_geometry
    )
    root = local_config_root / "diagnostics" / "display_geometry" / profile.id
    ruler = spatial = temporal = False
    if root.exists():
        for path in root.rglob("geometry_check.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not diagnostic_matches_profile(payload, profile):
                    continue
                kind = payload.get("request", {}).get("test_kind")
                if (kind in {"size", "position"}
                        and payload.get("measurement", {}).get("measured_length_mm") is not None):
                    ruler = True
                if kind == "spatial":
                    spatial = True
                if kind in {"temporal_binary", "temporal_sine"}:
                    temporal = True
            except (OSError, ValueError, TypeError, AttributeError):
                continue
    geometry = bound and ruler and profile.geometry_status == "verified"
    return {
        "bind": (
            bound, "Saved binding, pixel resolution and manually entered physical dimensions"
            if bound else "Bind the actual display and enter measured screen size/distance",
        ),
        "geometry": (
            geometry, "Ruler measurement and explicit geometry verification recorded"
            if geometry else "Requires a ruler measurement and explicit geometry verification",
        ),
        "spatial": (
            geometry and spatial, "Fullscreen spatial diagnostic recorded for verified geometry"
            if geometry and spatial else "Complete geometry and inspect a spatial grating",
        ),
        "luminance": (
            bound and profile.has_verified_luminance_mapping,
            "Measured photometer mapping explicitly verified"
            if bound and profile.has_verified_luminance_mapping
            else "Genuine photometer measurements and review required",
        ),
        "timing": (
            bound and profile.timing_status == "verified",
            "Independent physical timing explicitly verified"
            if bound and profile.timing_status == "verified"
            else "Timing not physically verified (software test alone is insufficient)",
        ),
        "review": (
            bound and bool(profile.qualified_experiments),
            f"Explicit qualification for: {', '.join(profile.qualified_experiments)}"
            if bound and profile.qualified_experiments
            else "No explicitly qualified experiment on this bound display",
        ),
    }
