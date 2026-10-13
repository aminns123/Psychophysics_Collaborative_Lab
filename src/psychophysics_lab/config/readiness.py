"""Read-only profile readiness. Recorded checks never certify qualification."""
import json
from .local import content_hash, config_root
from .preflight import compatible, human_blockers


def profile_readiness(spec, profile, *, repo_root=None, values=None):
    matched = None
    if repo_root is not None:
        base = config_root(repo_root) / "diagnostics" / "display_geometry" / profile.id
        reports = sorted(base.rglob("geometry_check.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True) if base.exists() else []
        for report in reports:
            try:
                payload = json.loads(report.read_text(encoding="utf-8"))
                snapshot = payload.get("monitor_profile", {})
                if (payload.get("status") == "completed" and
                    payload.get("monitor_profile_sha256", content_hash(snapshot)) == content_hash(profile.to_dict()) and
                    payload.get("measurement", {}).get("measured_length_mm") is not None):
                    matched = {"diagnostic_uuid": payload.get("diagnostic_uuid"),
                               "profile_revision": profile.revision,
                               "measurement": payload["measurement"],
                               "interpretation": "Recorded ruler check for this revision; not automatic acceptance."}
                    break
            except (OSError, ValueError, TypeError, AttributeError):
                continue
    return {"available": True, "profile_id": profile.id, "profile_revision": profile.revision,
            "profile_sha256": content_hash(profile.to_dict()), "bound": bool(profile.display_binding),
            "measurement_sources": dict(profile.measurement_sources),
            "geometry_status": profile.geometry_status, "geometry_check": matched,
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
