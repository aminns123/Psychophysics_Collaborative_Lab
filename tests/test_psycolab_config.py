import pytest

from psychophysics_lab.config.models import MonitorProfile
from psychophysics_lab.data.participants import validate_participant_id


@pytest.mark.parametrize("value", ["S001", "subject_1", "pilot-A", "a.b"])
def test_participant_ids_accept_non_identifying_lab_codes(value):
    assert validate_participant_id(value) == value


@pytest.mark.parametrize("value", ["", "../subject", "first last", "/tmp/x"])
def test_participant_ids_reject_unsafe_paths(value):
    with pytest.raises(ValueError):
        validate_participant_id(value)


def test_monitor_profile_validation():
    profile = MonitorProfile(
        id="display",
        display_name="Display",
        physical_width_m=0.61,
        physical_height_m=0.35,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
    )
    profile.validate()


def test_monitor_profile_rejects_invalid_geometry():
    profile = MonitorProfile(
        id="display",
        display_name="Display",
        physical_width_m=0,
        physical_height_m=0.35,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
    )
    with pytest.raises(ValueError):
        profile.validate()
