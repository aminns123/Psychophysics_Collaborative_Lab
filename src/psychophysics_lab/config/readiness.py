"""Read-only profile readiness. Recorded checks never certify qualification."""
from .local import content_hash, config_root
from .preflight import compatible, human_blockers


# Status/provenance changes create a new profile revision, but do not change
# the geometry of the actual display. Preserve physically applicable diagnostic
# evidence without silently accepting a changed screen or viewing arrangement.
_DIAGNOSTIC_PHYSICAL_FIELDS = (
    "physical_width_m", "physical_height_m", "viewing_distance_m",
    "expected_resolution_px", "display_binding", "refresh_rate_hz",
)


def diagnostic_matches_profile(payload, profile) -> bool:
    """Require a consistent recorded profile snapshot and matching physical configuration."""
    if not isinstance(payload, dict) or payload.get("status") != "completed":
        return False
    snapshot = payload.get("monitor_profile")
    if not isinstance(snapshot, dict):
        return False
    try:
        if payload.get("monitor_profile_sha256") != content_hash(snapshot):
            return False
    except (ValueError, TypeError):
        return False
    if snapshot.get("id") != profile.id or snapshot.get("profile_uuid", "") != profile.profile_uuid:
        return False
    current = profile.to_dict()
    return all(snapshot.get(field) == current.get(field)
               for field in _DIAGNOSTIC_PHYSICAL_FIELDS)


def profile_readiness(spec, profile, *, repo_root=None, values=None):
    matched = None
    spatial_check = None
    temporal_check = None
    if repo_root is not None:
        from .calibration_progress import diagnostic_evidence
        groups = diagnostic_evidence(profile, config_root(repo_root))
        for stage, rows in groups.items():
            for row in rows:
                if not row["compatible"]:
                    continue
                payload = row["payload"]
                base = {"diagnostic_uuid": payload.get("diagnostic_uuid"),
                        "profile_revision": profile.revision,
                        "evidence_revision": payload["monitor_profile"].get("revision")}
                measurement = payload.get("measurement")
                if stage == "geometry" and matched is None and isinstance(measurement, dict) and measurement.get("measured_length_mm") is not None:
                    matched = base | {"measurement": measurement, "interpretation": "Recorded ruler check for this physical setup; not automatic acceptance."}
                if stage == "spatial" and spatial_check is None:
                    spatial_check = base | {"interpretation": "Software sine pattern was presented; physical spatial frequency NOT independently measured."}
                if stage == "timing" and temporal_check is None:
                    temporal_check = base | {"interpretation": "Software timing test was presented; photon onset NOT verified."}
    from .calibration_progress import calibration_progress
    stages = calibration_progress(profile, config_root(repo_root)) if repo_root is not None else None
    return {"calibration_stages": stages, "available": True, "profile_id": profile.id, "profile_revision": profile.revision,
            "profile_sha256": content_hash(profile.to_dict()), "bound": bool(profile.display_binding),
            "measurement_sources": dict(profile.measurement_sources),
            "geometry_status": profile.geometry_status, "geometry_check": matched,
            "spatial_check": spatial_check, "temporal_check": temporal_check,
            "photometrically_calibrated": profile.has_verified_luminance_mapping,
            "timing_status": profile.timing_status, "experiment_qualified": compatible(spec, profile),
            "human_blockers": list(human_blockers(spec, profile, values))}


def readiness_text(spec, profile, repo_root=None, values=None):
    result = profile_readiness(spec, profile, repo_root=repo_root, values=values)
    lines = [f"Experiment qualification: {'declared' if result['experiment_qualified'] else 'NOT QUALIFIED'}",
        f"Ruler check for revision {profile.revision}: {'recorded (review measured error)' if result['geometry_check'] else 'not recorded'}",
        f"Photometric mapping: {'verified table declared' if result['photometrically_calibrated'] else 'unverified/absent'}",
        f"Timing status: {profile.timing_status} (nominal refresh does not measure photon timing)"]
    lines.extend(result["human_blockers"])
    return "\n".join(lines)
