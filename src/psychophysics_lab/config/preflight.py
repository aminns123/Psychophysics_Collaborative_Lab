"""Single display-independent validation boundary for review and acquisition."""
from dataclasses import replace
from .local import content_hash
from ..data.participants import validate_participant_id

def compatible(spec, profile) -> bool:
    return not spec.compatible_monitor_profiles or profile.id in spec.compatible_monitor_profiles or spec.id in profile.qualified_experiments

def validate_setup(request, spec, profile):
    participant=validate_participant_id(request.participant_id)
    if request.session_mode not in {'new','reuse'}: raise ValueError('Unknown starting-settings mode.')
    profile.validate()
    if request.experiment_id != spec.id: raise ValueError('Selected experiment identity differs from request.')
    if not compatible(spec,profile): raise ValueError('This experiment/profile combination has not been qualified.')
    if request.monitor_profile_id!=profile.id: raise ValueError('Selected profile identity differs from request.')
    if request.monitor_profile_hash and request.monitor_profile_hash!=content_hash(profile.to_dict()):
        raise ValueError('Display profile changed since review. Review the setup again.')
    values=spec.normalise_values(request.experiment_values)
    if spec.monitor_validator: spec.monitor_validator(values,profile)
    if spec.id == "contrast_sensitivity" and values.get("condition_unit") != "legacy_shader_radians":
        from ..experiments.contrast_sensitivity import resolved_condition_frequencies
        from ..stimuli.spatial_calibration import resolve_spatial_geometry, validate_requested_cpd
        conditions = resolved_condition_frequencies(values["condition_values"], values["condition_unit"])
        if profile.expected_resolution_px:
            validate_requested_cpd(
                conditions,
                resolve_spatial_geometry(profile, profile.expected_resolution_px)
            )
    return replace(request,participant_id=participant,experiment_values=values,monitor_profile_hash=content_hash(profile.to_dict()))
