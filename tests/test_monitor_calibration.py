import pytest

from psychophysics_lab.config.models import LuminanceCalibrationPoint, MonitorProfile


def _profile(points):
    profile = MonitorProfile(
        id="test",
        display_name="Test display",
        physical_width_m=0.6,
        physical_height_m=0.34,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
        luminance_calibration=tuple(points),
        calibration_status="verified",
    )
    profile.validate()
    return profile


def test_verified_calibration_pair_is_enforced():
    profile = _profile([LuminanceCalibrationPoint(0.5, 100.0)])
    profile.validate_luminance_pair(luminance_cdm2=100.0, screen_intensity=0.5)
    with pytest.raises(ValueError):
        profile.validate_luminance_pair(luminance_cdm2=100.0, screen_intensity=0.6)


def test_unencoded_profile_does_not_invent_a_mapping():
    profile = _profile([])
    profile.validate_luminance_pair(luminance_cdm2=100.0, screen_intensity=0.6)


def test_unverified_points_are_not_treated_as_trusted_mapping():
    profile = MonitorProfile(
        id="draft",
        display_name="Draft calibration",
        physical_width_m=0.6,
        physical_height_m=0.34,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
        luminance_calibration=(LuminanceCalibrationPoint(0.5, 100.0),),
        calibration_status="manual_unverified",
    )
    profile.validate()
    assert not profile.has_verified_luminance_mapping
    profile.validate_luminance_pair(luminance_cdm2=100.0, screen_intensity=0.6)
