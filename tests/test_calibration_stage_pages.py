"""Calibration page navigation, revision-scoped indicators and safe demo data."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path

from textual.widgets import Button, ContentSwitcher, Select, Static

from psychophysics_lab.config.local import content_hash
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import LuminanceCalibrationPoint
from psychophysics_lab.config.calibration_templates import (
    demo_luminance_document, parse_luminance_measurements, write_luminance_demo
)
from psychophysics_lab.ui.calibration_stages import STAGES, stage_states
from psychophysics_lab.ui.setup import DisplayCheckScreen, PsyCoLabSetupApp


ROOT = Path(__file__).resolve().parents[1]


def test_fake_example_has_numbers_but_cannot_be_imported(tmp_path):
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    demo = demo_luminance_document(profile)
    assert demo["example_only"] is True
    assert len(demo["measurements"]) >= 2
    assert all(isinstance(row["luminance_cdm2"], float) for row in demo["measurements"])
    path = write_luminance_demo(tmp_path, profile)
    assert path.is_file()
    assert json.loads(path.read_text()) == demo
    try:
        parse_luminance_measurements(demo, profile)
    except ValueError as exc:
        assert "FAKE demonstration" in str(exc)
    else:
        raise AssertionError("Fake measurements must never pass calibration import")


def test_stages_use_current_profile_hash_and_human_flags(tmp_path):
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile = replace(
        reference, id="lab_display", origin="local", revision=3,
        display_binding={"index": 0, "x": 0, "y": 0, "width": 1920, "height": 1080},
        expected_resolution_px=(1920, 1080),
        measurement_sources={
            "physical_width_m": "manual", "physical_height_m": "manual",
            "viewing_distance_m": "manual",
        },
        geometry_status="verified",
        timing_status="verified",
        calibration_status="verified",
        luminance_calibration=(
            LuminanceCalibrationPoint(0.0, 0.5),
            LuminanceCalibrationPoint(1.0, 140.0),
        ),
        qualified_experiments=("contrast_sensitivity",),
    )
    status = stage_states(profile, tmp_path)
    assert status["bind"][0] and status["luminance"][0]
    assert status["timing"][0]
    # Qualification does not stand in for missing geometry/spatial setup records.
    assert not status["review"][0]
    assert not status["geometry"][0] and not status["spatial"][0]
    folder = tmp_path / "diagnostics" / "display_geometry" / profile.id
    folder.mkdir(parents=True)
    for name, kind, measurement in (
        ("ruler", "size", {"measured_length_mm": 100.0}),
        ("spatial", "spatial", {}),
    ):
        sub = folder / name
        sub.mkdir()
        (sub / "geometry_check.json").write_text(json.dumps({
            "status": "completed",
            "monitor_profile": profile.to_dict(),
            "monitor_profile_sha256": content_hash(profile.to_dict()),
            "request": {"test_kind": kind},
            "measurement": measurement,
        }))
    status = stage_states(profile, tmp_path)
    assert all(status[key][0] for key, _ in STAGES)
    # A verification-only save changes the profile revision/hash, not physical setup.
    marked = replace(profile, revision=4, calibration_notes="Reviewed in the laboratory")
    assert stage_states(marked, tmp_path)["geometry"][0]
    assert stage_states(marked, tmp_path)["spatial"][0]
    revised = replace(profile, viewing_distance_m=profile.viewing_distance_m + 0.1)
    status = stage_states(revised, tmp_path)
    assert not status["geometry"][0] and not status["spatial"][0]


def test_calibration_six_pages_are_navigable_and_keep_shared_inputs(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "machine"))
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(130, 42)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, DisplayCheckScreen)
            assert len(screen.query("#calibration-stage-nav Button")) == 6
            switcher = screen.query_one("#calibration-pages", ContentSwitcher)
            assert switcher.current == "cal-panel-bind"
            selected = screen.query_one("#geometry-monitor", Select).value
            assert "INCOMPLETE" in str(screen.query_one("#calibration-review-detail", Static).render())
            for stage, _ in STAGES:
                screen.query_one(f"#cal-stage-{stage}", Button).press()
                await pilot.pause()
                assert switcher.current == f"cal-panel-{stage}"
                assert screen.query_one("#geometry-monitor", Select).value == selected
            screen.query_one("#calibration-refresh", Button).press()
            await pilot.pause()
            assert switcher.current == "cal-panel-review"
    asyncio.run(scenario())
