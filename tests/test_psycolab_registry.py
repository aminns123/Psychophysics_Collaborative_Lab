from datetime import datetime

from psychophysics_lab.config.models import MonitorProfile
from psychophysics_lab.experiments.registry import get_experiment, list_experiments


def test_csf_is_explicitly_registered():
    specs = list_experiments()
    assert [spec.id for spec in specs] == ["contrast_sensitivity"]
    assert get_experiment("contrast_sensitivity") is specs[0]


def test_csf_builds_legacy_setup_without_changing_defaults():
    spec = get_experiment("contrast_sensitivity")
    profile = MonitorProfile(
        id="legacy_reference_display",
        display_name="Legacy",
        physical_width_m=0.610,
        physical_height_m=0.350,
        refresh_rate_hz=60,
        viewing_distance_m=1.0,
    )
    values = spec.field_defaults()
    values.update(
        {
            "Max_monitor_Luminance": 500.0,
            "Background_Luminance": 204.0,
            "Background_Screen_intensity": 0.72,
        }
    )

    setup = spec.build_legacy_setup(
        participant_id="S001",
        values=values,
        monitor_profile=profile,
        now=datetime(2026, 9, 14),
    )

    assert setup["Experiment_Type"] == "contrast_sensitivity_function"
    assert setup["n_down"] == 2
    assert setup["n_up"] == 1
    assert setup["reversal_termination"] == 10
    assert setup["max_trials"] == 30
    assert setup["timeFixate"] == 250
    assert setup["timeInterval"] == 250
    assert setup["timeAB"] == 200
    assert setup["monitor_profile"]["physical_width_m"] == 0.610
