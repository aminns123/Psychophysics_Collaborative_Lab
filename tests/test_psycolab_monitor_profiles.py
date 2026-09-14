import json

from psychophysics_lab.config.monitor import load_monitor_profiles


def test_monitor_profiles_load_from_repository_shape(tmp_path):
    directory = tmp_path / "configs" / "monitors"
    directory.mkdir(parents=True)
    (directory / "lab.json").write_text(
        json.dumps(
            {
                "id": "lab",
                "display_name": "Lab display",
                "physical_width_m": 0.61,
                "physical_height_m": 0.35,
                "refresh_rate_hz": 60,
                "viewing_distance_m": 1.0,
            }
        ),
        encoding="utf-8",
    )

    profiles = load_monitor_profiles(tmp_path)
    assert profiles["lab"].refresh_rate_hz == 60
    assert profiles["lab"].physical_width_m == 0.61
