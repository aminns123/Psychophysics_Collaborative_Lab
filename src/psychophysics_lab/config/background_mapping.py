"""One view of the selected display's committed active luminance means."""
from .calibration_dataset import load_active, summary, luminance_state, dataset_hash, physical_snapshot
from .local import content_hash


def mapping_choices(root, profile):
    dataset = load_active(root, profile)
    rows = summary(dataset)
    pairs = [(row["screen_intensity"], row["luminance_cdm2"]) for row in rows]
    committed = [(p.screen_intensity, p.luminance_cdm2) for p in sorted(profile.luminance_calibration, key=lambda p: p.screen_intensity)]
    if dataset["physical_snapshot"] != physical_snapshot(profile) or pairs != committed:
        raise ValueError("Active measurements are stale or differ from this display's committed mapping. Review calibration before selecting a saved pair.")
    state = luminance_state(profile, dataset)
    if any('synthetic' in row['reading_data_kinds'] for row in rows):
        state = 'SYNTHETIC / TEST DATA — not physically verified; simulation/test presentation only'
    return rows, dataset, state


def configuration_mapping_choices(root, profile):
    """Offer committed profile means for *test setup* when active raw data are stale.

    The strict mapping_choices() remains the authority for verified mappings.
    Fallback rows are explicitly unverified and only offered when the profile
    is already unverified. No mismatched dataset is silently trusted.
    """
    try:
        rows, dataset, status = mapping_choices(root, profile)
        return rows, dataset, status, "active"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if profile.has_verified_luminance_mapping or not profile.luminance_calibration:
            return [], None, (
                "Saved luminance mapping unavailable: " + str(exc)
                + " Open Calibrate → Luminance to repair the active measurements."
            ), "unavailable"
        # This profile's stored summary is still useful for a UI or synthetic
        # run, but it is NOT trusted physical calibration of this monitor.
        rows = [
            {"screen_intensity": point.screen_intensity,
             "luminance_cdm2": point.luminance_cdm2,
             "n": None, "summary_only": True,
             "reading_data_kinds": ["unspecified"]}
            for point in sorted(profile.luminance_calibration,
                                key=lambda item: item.screen_intensity)
        ]
        return rows, None, (
            "PROFILE-ONLY TEST VALUES — active measurements are stale or missing. "
            "These historical saved means are NOT physically verified for this setup. "
            "Use only for simulation/test presentation; open Calibrate → Luminance "
            "to repair or replace the raw observations before human acquisition. "
            "Details: " + str(exc)
        ), "profile_only"


def background_provenance(root, profile, values):
    """Record exact values and their relation to saved means without interpolation."""
    if not {"Background_Screen_intensity", "Background_Luminance"}.issubset(values):
        return None
    intensity = values["Background_Screen_intensity"]
    luminance = values["Background_Luminance"]
    result = {"screen_intensity": intensity, "luminance_cdm2": luminance,
              "monitor_profile_id": profile.id, "profile_uuid": profile.profile_uuid,
              "profile_revision": profile.revision, "monitor_profile_sha256": content_hash(profile.to_dict()),
              "luminance_source_hash": profile.luminance_source_hash,
              "profile_verification_declared": profile.has_verified_luminance_mapping,
              "physically_verified_mapping": False,
              "selection_basis": "manual_unmatched", "interpolated": False}
    try:
        rows, dataset, state = mapping_choices(root, profile)
    except (OSError, ValueError, KeyError, TypeError):
        result.update(mapping_state="unavailable", mapping_warning="Active calibration unavailable or stale; inspect local calibration before reuse.")
        return result
    match = next((row for row in rows if row["screen_intensity"] == intensity and row["luminance_cdm2"] == luminance), None)
    result.update(mapping_state=state, dataset_sha256=dataset_hash(dataset), dataset_version=dataset["version"])
    if match is not None:
        result.update(selection_basis="exact_saved_mean_pair", saved_mapping_row=match,
                      physically_verified_mapping=profile.has_verified_luminance_mapping,
                      method=dataset["method"], physical_snapshot=dataset["physical_snapshot"])
    return result
