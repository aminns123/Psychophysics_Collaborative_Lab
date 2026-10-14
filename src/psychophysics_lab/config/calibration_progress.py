"""Shared factual calibration progress; laboratory declarations remain explicit."""
from __future__ import annotations
import json
from pathlib import Path


def diagnostic_evidence(profile, root: Path):
    from .readiness import diagnostic_matches_profile
    base = root / "diagnostics" / "display_geometry" / profile.id
    found = []
    for path in base.rglob("geometry_check.json") if base.exists() else ():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                found.append((path.stat().st_mtime_ns, path, payload))
        except (OSError, ValueError):
            continue
    found.sort(key=lambda row: row[0], reverse=True)
    groups = {"geometry": [], "spatial": [], "timing": []}
    kinds = {"size": "geometry", "position": "geometry", "spatial": "spatial",
             "temporal_binary": "timing", "temporal_sine": "timing"}
    for _, path, payload in found:
        request = payload.get("request")
        if not isinstance(request, dict):
            continue
        stage = kinds.get(request.get("test_kind", "size"))
        if stage:
            groups[stage].append({"path": path.relative_to(root).as_posix(), "payload": payload,
                                  "compatible": diagnostic_matches_profile(payload, profile)})
    return groups


def calibration_progress(profile, root: Path):
    """Text states expose progress independently of red/green verification."""
    evidence = diagnostic_evidence(profile, root)
    manual = all(profile.measurement_sources.get(k) == "manual" for k in
                 ("physical_width_m", "physical_height_m", "viewing_distance_m"))
    bound = profile.origin == "local" and bool(profile.display_binding) and bool(profile.expected_resolution_px) and manual
    result = {"bind": {"ready": bound, "completed": bound, "verified": False,
                       "state": "complete" if bound else "incomplete",
                       "message": "Saved binding, pixel resolution and manually entered physical dimensions" if bound else "Bind the actual display and enter measured screen size/distance"}}
    for stage in ("geometry", "spatial", "timing"):
        rows = evidence[stage]
        valid = [row for row in rows if row["compatible"]]
        measurements = [row for row in valid if isinstance(row["payload"].get("measurement"), dict)
                        and row["payload"]["measurement"].get("measured_length_mm") is not None]
        declaration = profile.geometry_status if stage in ("geometry", "spatial") else profile.timing_status
        if stage == "geometry":
            ready = bound and bool(measurements) and declaration == "verified"
            state = "complete" if ready else "awaiting_review" if measurements else "awaiting_measurement" if valid else "incomplete"
            message = ("Ruler measurement and explicit geometry verification recorded" if ready else
                       "Ruler measurement/error saved; review error and explicitly verify under laboratory criteria" if measurements else
                       "Software ruler presentation completed; enter the physical ruler measurement" if valid else
                       "Run a ruler presentation, record its physical length, then review the error")
        elif stage == "spatial":
            from .spatial_observation import observations, visually_consistent, read_report
            observation = None
            if valid:
                latest = valid[0]
                try:
                    path, payload = read_report(root, root / latest["path"], profile)
                    recorded = observations(path, payload)
                    observation = recorded[-1] if recorded else None
                except (OSError, ValueError, TypeError):
                    pass
            consistent = visually_consistent(observation)
            ready = result["geometry"]["ready"] and consistent
            state = ("visually_consistent" if consistent else "observation_discrepancy" if observation
                     else "awaiting_observation" if valid and valid[0]["payload"].get("diagnostic_uuid")
                     else "software_presented" if valid else "not_tested")
            message = ("Researcher observation recorded — visually consistent; NOT independent physical certification" if consistent
                       else "Observation recorded — discrepancy, uncertainty or not assessed; inspect and record a new assessment" if observation
                       else "Software spatial diagnostic presented; awaiting researcher observation on Spatial" if valid
                       else "Present a spatial grating, then record what you observed")
        else:
            ready = bound and declaration == "verified"
            state = "complete" if ready else "awaiting_measurement" if valid else "incomplete"
            message = ("Independent physical timing explicitly declared verified" if ready else
                       "Software timing diagnostic completed; photon timing requires independent photodiode measurement/review" if valid else
                       "Run software timing diagnostics; physical photon timing remains unverified")
        if not valid and rows and not ready:
            state = "failed" if rows[0]["payload"].get("status") == "error" else "stale"
            message = "Latest attempt failed; rerun and inspect diagnostic error" if state == "failed" else "Earlier evidence is stale or invalid for this physical setup; run a fresh test"
        if valid and rows and rows[0]["payload"].get("status") == "error":
            message += "; latest attempt failed, prior compatible evidence retained"
        # Completion means the required workflow observation was SAVED.
        # Readiness remains a separate, stricter physical verification flag.
        completed = (consistent if stage == "spatial" else
                     (bool(measurements) if stage == "geometry" else bool(valid)) or ready)
        result[stage] = {"ready": ready, "completed": completed,
                         "verified": ready if stage != "spatial" else False, "state": state, "message": message,
                         "software_completed": bool(valid), "measurement_recorded": bool(measurements),
                         "verification_declared": declaration == "verified",
                         "reports": [row["path"] for row in valid]}
        if stage == "spatial":
            result[stage]["observation"] = observation
            result[stage]["physical_spatial_frequency_certified"] = False
    measured = len(profile.luminance_calibration) >= 2
    session_message = ""
    if not measured:
        from .readiness import diagnostic_matches_profile
        sessions = root / "calibration_sessions" / profile.id
        for path in sorted(sessions.glob("*/session.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if diagnostic_matches_profile(dict(payload, status="completed"), profile) and payload.get("readings"):
                    session_message = "Photometer readings saved locally; import the means and Save profile. Method/date/notes are optional."
                    break
            except (OSError, ValueError, TypeError):
                continue
    ready = bound and profile.has_verified_luminance_mapping
    result["luminance"] = {"ready": ready, "completed": measured,
                           "verified": bool(profile.has_verified_luminance_mapping),
                           "state": "complete" if ready else "awaiting_review" if measured else "awaiting_import" if session_message else "awaiting_measurement",
                           "message": "Saved photometer mapping explicitly verified" if ready else
                           "Entered intensity / cd/m² values SAVED (not independently certified). Measurement stage finished; physical certification remains unverified (optional method/date/notes do not block saving)." if measured else
                           session_message or "Enter at least two real intensity / cd/m² pairs, import and save. Instrument details are optional."}
    setup_completed = all(result[key]["completed"] for key in ("bind", "geometry", "spatial", "luminance", "timing"))
    ready = setup_completed
    result["review"] = {"ready": ready, "completed": ready, "verified": False,
                        "state": "complete" if ready else "awaiting_review",
                        "message": "Calibration setup records complete. Finish setup returns to Experiment; physical verification and qualification remain separate." if ready else "Some setup records are incomplete. You may still finish and return to Experiment; review missing observations later."}
    return result
