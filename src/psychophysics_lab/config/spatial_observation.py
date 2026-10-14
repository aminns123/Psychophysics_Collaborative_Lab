"""Append-only researcher observations tied to an immutable spatial presentation.

Visual consistency is subjective evidence, never physical certification.
"""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from uuid import uuid4

from .local import content_hash
from .readiness import diagnostic_matches_profile
from ..data.locking import file_lock
from ..data.session import atomic_write_json

ASSESSMENTS = ("consistent", "discrepancy", "uncertain", "not_assessed")
ABNORMALITIES = ("none", "aliasing", "orientation", "spacing", "clipping", "other", "not_assessed")


def read_report(root, report, profile):
    path = Path(report).resolve()
    base = (Path(root) / "diagnostics" / "display_geometry" / profile.id).resolve()
    if (not base.is_relative_to(Path(root).resolve()) or not path.is_relative_to(base)
            or path.name != "geometry_check.json"):
        raise ValueError("Choose a spatial diagnostic belonging to this display's local records.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("request", {}).get("test_kind") != "spatial":
        raise ValueError("This report is not a spatial diagnostic.")
    if not diagnostic_matches_profile(payload, profile):
        raise ValueError("Diagnostic failed or is stale for this physical configuration; present a new test.")
    if not payload.get("diagnostic_uuid") or not payload.get("actual_fullscreen_resolution_px"):
        raise ValueError("Historical report lacks presentation identity/resolution; present a new test.")
    spatial = payload.get("resolved_test", {}).get("spatial", {})
    for key in ("requested_cycles_per_degree", "cycles_across_patch", "minimum_pixels_per_cycle"):
        value = spatial.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError("Spatial report is incomplete; present a new test.")
    expected = profile.expected_resolution_px
    if expected and list(expected) != payload["actual_fullscreen_resolution_px"]:
        raise ValueError("Actual fullscreen resolution does not match the selected display.")
    return path, payload


def observations(report, payload):
    """Only records linked to these exact report bytes (canonical JSON) apply."""
    found = []
    for path in (Path(report).parent / "spatial_observations").glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if (value.get("schema_version") == 1
                    and value.get("diagnostic_uuid") == payload.get("diagnostic_uuid")
                    and value.get("diagnostic_sha256") == content_hash(payload)
                    and value.get("monitor_profile_sha256") == payload.get("monitor_profile_sha256")
                    and value.get("assessment") in ASSESSMENTS
                    and value.get("abnormality") in ABNORMALITIES
                    and isinstance(value.get("recorded_utc"), str)
                    and isinstance(value.get("observation_uuid"), str)):
                found.append(value)
        except (OSError, ValueError, TypeError):
            continue
    return sorted(found, key=lambda item: (item["recorded_utc"], item["observation_uuid"]))


def visually_consistent(observation):
    return bool(observation and observation["assessment"] == "consistent"
                and observation["abnormality"] == "none")


def record_observation(root, report, profile, *, assessment, abnormality,
                       observed_count=None, count_kind="cycles", notes=""):
    if assessment not in ASSESSMENTS or abnormality not in ABNORMALITIES:
        raise ValueError("Choose an assessment and a rendering-abnormality response.")
    if count_kind not in ("cycles", "bright_maxima"):
        raise ValueError("Choose complete light-dark cycles or bright maxima.")
    if observed_count is not None:
        if isinstance(observed_count, bool):
            raise ValueError("Observed count must be a finite, nonnegative number.")
        observed_count = float(observed_count)
        if not math.isfinite(observed_count) or observed_count < 0:
            raise ValueError("Observed count must be a finite, nonnegative number.")
    answer = dict(assessment=assessment, abnormality=abnormality,
                  observed_count=observed_count, count_kind=count_kind, notes=notes.strip())
    path, payload = read_report(root, report, profile)
    with file_lock(path.parent / "spatial_observations.lock"):
        path, payload = read_report(root, report, profile)
        prior = observations(path, payload)
        if prior and all(prior[-1].get(key) == value for key, value in answer.items()):
            return prior[-1]  # Repeated unchanged Save is a no-op.
        record = dict(schema_version=1, observation_uuid=str(uuid4()),
                      diagnostic_uuid=payload["diagnostic_uuid"], diagnostic_sha256=content_hash(payload),
                      monitor_profile_sha256=payload["monitor_profile_sha256"],
                      monitor_profile_id=profile.id, profile_uuid=profile.profile_uuid,
                      diagnostic_report=path.relative_to(Path(root).resolve()).as_posix(),
                      recorded_utc=datetime.now(timezone.utc).isoformat(),
                      physical_spatial_frequency_certified=False,
                      interpretation="Researcher visual observation only; no numerical acceptance tolerance or physical certification.",
                      **answer)
        destination = path.parent / "spatial_observations" / (record["observation_uuid"] + ".json")
        if not destination.resolve().is_relative_to(path.parent):
            raise ValueError("Observation destination escapes its diagnostic directory.")
        if destination.exists():
            raise ValueError("Observation identity already exists; no record was overwritten.")
        atomic_write_json(destination, record)
        return record


def report_summary(payload):
    profile = payload.get("monitor_profile", {})
    request = payload.get("request", {})
    plan = payload.get("resolved_test", {})
    spatial = plan.get("spatial", {})
    freq = spatial.get("requested_cycles_per_degree")
    cycles = spatial.get("cycles_across_patch")
    pixels = spatial.get("minimum_pixels_per_cycle")
    lines = [f"Display: {profile.get('display_name')} [{profile.get('id')}]",
             f"Physical width × height: {profile.get('physical_width_m')} × {profile.get('physical_height_m')} m; viewing distance: {profile.get('viewing_distance_m')} m",
             f"Actual fullscreen resolution: {payload.get('actual_fullscreen_resolution_px')}",
             f"Requested: {freq} cycles/degree; orientation (phase axis): {request.get('orientation')}",
             f"Requested extent: {request.get('value')} {request.get('mode')}",
             f"Resolved angular extent at actual position: {plan.get('off_axis_extent_deg')} degrees; nominal complete cycles: {cycles}",
             f"Quantised rectangle: {plan.get('rectangle_px')} pixels"]
    if freq and pixels:
        lines.append(f"Conservative phase-axis pixels/degree: {freq * pixels:.6g}; Nyquist: {freq * pixels / 2:.6g} cycles/degree (strictly below); minimum pixels/cycle: {pixels:.6g}")
    lines += [f"Diagnostic UUID: {payload.get('diagnostic_uuid')}; date: {payload.get('finished_utc', payload.get('started_utc'))}; status: {payload.get('status')}",
              "One cycle is a complete light–dark period. Bright maxima alone depend on phase and edge placement; they need not equal the nominal cycle count.",
              "The renderer uses cosine phase at angular pixel centres. Pixel quantisation, boundaries, orientation and changing local visual angle across a flat display affect the count. No automatic numerical tolerance is imposed.",
              "A visual consistency observation does not independently certify physical spatial frequency."]
    return "\n".join(lines)
