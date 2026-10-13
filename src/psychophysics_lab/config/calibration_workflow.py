"""Chronological calibration navigation, driven by persisted observations.

A completed page represents SAVED evidence, not automatic laboratory certification.
Advance only when the requested stage has persisted; the user can always browse
pages manually, including when the lab lacks a photometer or photodiode.
"""
from __future__ import annotations

from pathlib import Path

from .calibration_progress import calibration_progress
from .local import save_preferences


ORDER = ("bind", "geometry", "spatial", "luminance", "timing", "review")


def next_stage(stage: str) -> str | None:
    if stage not in ORDER:
        raise ValueError(f"Unknown calibration stage: {stage}")
    index = ORDER.index(stage) + 1
    return ORDER[index] if index < len(ORDER) else None


def advance_if_completed(profile, local_config_root: Path, stage: str) -> str | None:
    """Persist the next page only after its predecessor has saved real evidence.

    Verification remains independent: e.g. recorded luminance pairs complete
    the acquisition step but do not certify photometry for human experiments.
    """
    following = next_stage(stage)
    if following is None:
        return None
    state = calibration_progress(profile, local_config_root)[stage]
    if not state["completed"]:
        return None
    save_preferences(local_config_root, calibration_active_stage=following)
    return following


def import_and_save_luminance(profile, local_config_root: Path, json_path: str):
    """One atomic, user-initiated import: validate data, then save a local revision.

    No implicit certification; preserve the original shared reference and
    existing append-only profile history. Returns (persisted profile, warnings).
    """
    from .calibration_templates import read_luminance_measurements, template_identity
    from .local import save_profile
    from .monitor import _profile_from_dict

    draft = read_luminance_measurements(
        json_path, profile, local_config_root=local_config_root
    )
    target_id, _ = template_identity(profile)
    fields = profile.to_dict()
    fields.update({
        "id": target_id,
        "origin": "local",
        "luminance_calibration": draft["luminance_calibration"],
        "calibration_method": draft["calibration_method"],
        "calibration_date": draft["calibration_date"],
        "calibration_notes": draft["calibration_notes"],
        "calibration_status": "manual_unverified",
        "qualified_experiments": [],
    })
    for key in ("calibration_method", "calibration_date", "calibration_notes"):
        if not draft[key]:
            fields[key] = profile.to_dict()[key]  # Optional omissions never erase saved provenance.
    unchanged_mapping = all(fields[key] == profile.to_dict()[key] for key in
                            ("luminance_calibration", "calibration_method", "calibration_date"))
    if unchanged_mapping:
        fields["calibration_status"] = profile.calibration_status
        fields["qualified_experiments"] = list(profile.qualified_experiments)
    if profile.origin != "local":
        fields["revision"] = 0
        fields["profile_uuid"] = ""
    saved = save_profile(
        local_config_root,
        _profile_from_dict(fields),
        expected_revision=profile.revision if profile.origin == "local" else 0,
    )
    return saved, list(draft.get("warnings", ()))
