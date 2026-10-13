"""Configuration validity and human qualification are distinct boundaries."""
from dataclasses import replace
from .local import content_hash
from ..data.participants import validate_participant_id


def compatible(spec, profile) -> bool:
    """Retained public qualification policy; never used to hide available profiles."""
    return not spec.compatible_monitor_profiles or profile.id in spec.compatible_monitor_profiles or spec.id in profile.qualified_experiments


def human_blockers(spec, profile, values=None):
    reasons = []
    if not compatible(spec, profile):
        reasons.append("This experiment/profile combination has not been qualified. Use Calibrate to complete laboratory checks and explicitly record experiment qualification; headless simulation remains available.")
    if profile.origin == "local" and not profile.display_binding:
        reasons.append("This local profile is an UNBOUND DRAFT. Calibrate → Edit / copy display profile → Detect connected displays → select monitor → Save local revision.")
    if spec.id == "contrast_sensitivity" and values:
        if values.get("condition_unit") != "legacy_shader_radians" and not profile.expected_resolution_px:
            reasons.append("Physical cpd acquisition needs expected fullscreen pixel resolution. Save it in Calibrate and check the framebuffer.")
        from ..stimuli.contrast_validation import validate_grating_command
        from Events.display_contrast import normalized_display_contrast
        try:
            contrast = normalized_display_contrast(float(values["starting_probe_intensity"]),
                background_intensity=float(values["Background_Screen_intensity"]), maximum_intensity=1.)
            validate_grating_command(contrast, float(values["Background_Screen_intensity"]))
        except ValueError as exc:
            reasons.append(str(exc))
    return tuple(reasons)


def validate_setup(request, spec, profile, *, mode="human"):
    """Default preserves strict public preflight; UI must name configuration/simulation mode."""
    if mode not in {"human", "configuration", "simulation"}:
        raise ValueError("Unknown acquisition validation mode.")
    participant=validate_participant_id(request.participant_id)
    if request.session_mode not in {'new','reuse'}:
        raise ValueError('Unknown starting-settings mode.')
    profile.validate()
    if request.experiment_id != spec.id:
        raise ValueError('Selected experiment identity differs from request.')
    if request.monitor_profile_id!=profile.id:
        raise ValueError('Selected profile identity differs from request.')
    if request.monitor_profile_hash and request.monitor_profile_hash!=content_hash(profile.to_dict()):
        raise ValueError('Display profile changed since review. Return to configuration, refresh the display and Review again.')
    values=spec.normalise_values(request.experiment_values)
    if spec.monitor_validator:
        spec.monitor_validator(values,profile)
    if spec.id == "contrast_sensitivity" and values.get("condition_unit") != "legacy_shader_radians":
        from ..experiments.contrast_sensitivity import resolved_condition_frequencies
        from ..stimuli.spatial_calibration import resolve_spatial_geometry, validate_requested_cpd
        conditions = resolved_condition_frequencies(values["condition_values"], values["condition_unit"])
        if profile.expected_resolution_px:
            validate_requested_cpd(conditions, resolve_spatial_geometry(profile, profile.expected_resolution_px))
    if mode == "human":
        blockers = human_blockers(spec, profile, values)
        if blockers:
            raise ValueError("Human acquisition blocked:\n" + "\n".join(blockers))
    return replace(request,participant_id=participant,experiment_values=values,monitor_profile_hash=content_hash(profile.to_dict()))
