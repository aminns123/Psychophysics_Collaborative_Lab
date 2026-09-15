from psychophysics_lab.config.models import MonitorProfile
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC


def _values():
    values = CSF_SPEC.field_defaults()
    values.update(
        {
            "Max_monitor_Luminance": 500.0,
            "Background_Luminance": 49.0,
            "Background_Screen_intensity": 0.374,
        }
    )
    return values


def test_csf_path_exposes_fixed_scientific_conditions_and_calibration_status():
    profile = MonitorProfile(
        id="legacy_reference_display",
        display_name="Legacy",
        physical_width_m=0.610,
        physical_height_m=0.350,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
        calibration_status="manual_unverified",
    )
    assert CSF_SPEC.data_path_parts(_values(), profile) == (
        "max_500cdm2",
        "background_49cdm2_unverified",
    )


def test_csf_verified_profile_uses_clean_physical_luminance_folder():
    # data_path_parts only needs the verified-mapping property; use a tiny
    # calibration point through the public model API.
    from psychophysics_lab.config.models import LuminanceCalibrationPoint

    profile = MonitorProfile(
        id="verified_display",
        display_name="Verified",
        physical_width_m=0.610,
        physical_height_m=0.350,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
        calibration_status="verified",
        luminance_calibration=(
            LuminanceCalibrationPoint(screen_intensity=0.374, luminance_cdm2=49.0),
        ),
    )
    assert CSF_SPEC.data_path_parts(_values(), profile) == (
        "max_500cdm2",
        "background_49cdm2",
    )
