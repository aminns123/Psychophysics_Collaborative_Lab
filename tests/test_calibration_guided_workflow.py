"""Chronological calibration and real readings vs physical verification."""
import asyncio
import json
from dataclasses import replace
from pathlib import Path

from textual.widgets import Button, ContentSwitcher, Input

from psychophysics_lab.config.calibration_progress import calibration_progress
from psychophysics_lab.config.calibration_workflow import advance_if_completed, next_stage
from psychophysics_lab.config.local import preferences
from psychophysics_lab.config.models import LuminanceCalibrationPoint
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.ui.calibration_stages import stage_states
from psychophysics_lab.ui.setup import DisplayCheckScreen, PsyCoLabSetupApp


ROOT = Path(__file__).resolve().parents[1]


def test_saved_real_luminance_pairs_finish_stage_but_not_physical_certification(tmp_path):
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    p = replace(reference, origin="local", id="demo_lab", revision=2,
                luminance_calibration=(LuminanceCalibrationPoint(.1, 2.0),
                                       LuminanceCalibrationPoint(.9, 91.0)),
                calibration_status="manual_unverified",
                calibration_method="", calibration_date="", calibration_notes="")
    state = calibration_progress(p, tmp_path)["luminance"]
    assert state["completed"] is True
    assert state["ready"] is False
    assert stage_states(p, tmp_path)["luminance"][0] is True
    assert "VERIFICATION PENDING" in stage_states(p, tmp_path)["luminance"][1]
    assert not p.has_verified_luminance_mapping
    assert advance_if_completed(p, tmp_path, "luminance") == "timing"
    assert preferences(tmp_path)["calibration_active_stage"] == "timing"


def test_incomplete_stages_do_not_advance_without_user_direction(tmp_path):
    p = load_monitor_profiles(ROOT)["legacy_reference_display"]
    assert advance_if_completed(p, tmp_path, "luminance") is None
    assert preferences(tmp_path).get("calibration_active_stage") is None
    assert next_stage("bind") == "geometry"
    assert next_stage("geometry") == "spatial"
    assert next_stage("spatial") == "luminance"
    assert next_stage("luminance") == "timing"
    assert next_stage("timing") == "review"
    assert next_stage("review") is None


def test_profile_save_stays_on_luminance_until_explicit_next(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "machine"))

    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "participants")
        async with app.run_test(size=(118, 37)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, DisplayCheckScreen)
            screen.query_one("#cal-stage-luminance", Button).press()
            await pilot.pause()
            assert screen.active_calibration_stage == "luminance"
            screen.query_one("#edit-luminance-profile", Button).press()
            await pilot.pause()
            editor = app.screen
            editor.query_one("#profile-luminance", Input).value = json.dumps([
                {"screen_intensity": .2, "luminance_cdm2": 3.1},
                {"screen_intensity": .8, "luminance_cdm2": 128.5},
            ])
            editor.query_one("#profile-calibration_method", Input).value = ""
            editor.query_one("#profile-calibration_notes", Input).value = ""
            editor.query_one("#profile-calibration_date", Input).value = ""
            editor.query_one("#profile-save", Button).press()
            await pilot.pause()
            assert app.screen is screen
            assert screen.active_calibration_stage == "luminance"
            assert screen.query_one("#calibration-pages", ContentSwitcher).current == "cal-panel-luminance"
            saved = app.monitor_profiles["legacy_reference_display_local"]
            assert len(saved.luminance_calibration) == 2
            assert saved.calibration_status == "manual_unverified"
            assert stage_states(saved, app.local_config_root)["luminance"][0]
            assert not saved.has_verified_luminance_mapping
            assert preferences(app.local_config_root)["calibration_active_stage"] == "luminance"
            screen.query_one("#calibration-next", Button).press()
            await pilot.pause()
            assert screen.active_calibration_stage == "timing"
            screen.query_one("#calibration-previous", Button).press()
            await pilot.pause()
            assert screen.active_calibration_stage == "luminance"
            screen.query_one("#calibration-start", Button).press()
            await pilot.pause()
            assert screen.active_calibration_stage == "bind"
    asyncio.run(scenario())


def test_direct_json_import_one_click_saves_local_revision_and_advances(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "machine"))
    from psychophysics_lab.config.calibration_templates import example_luminance_document

    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "participants")
        async with app.run_test(size=(115, 37)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, DisplayCheckScreen)
            screen.query_one("#cal-stage-luminance", Button).press()
            await pilot.pause()
            p = app.monitor_profiles["legacy_reference_display"]
            document = example_luminance_document(p)
            document["measurements"][0]["luminance_cdm2"] = 1.7
            document["measurements"][4]["luminance_cdm2"] = 192.1
            file = tmp_path / "my_actual_photometry.json"
            file.write_text(json.dumps(document))
            screen.query_one("#cal-luminance-json-path", Input).value = str(file)
            screen.query_one("#calibration-import-luminance", Button).press()
            await pilot.pause()
            # Save remains on Luminance for review; the researcher chooses Next.
            assert screen.active_calibration_stage == "luminance"
            screen.query_one("#calibration-next", Button).press()
            await pilot.pause()
            assert screen.active_calibration_stage == "timing"
            saved = app.monitor_profiles["legacy_reference_display_local"]
            assert len(saved.luminance_calibration) == 2
            assert saved.calibration_status == "manual_unverified"
            assert saved.calibration_method == ""
            assert not saved.has_verified_luminance_mapping
            assert stage_states(saved, app.local_config_root)["luminance"][0]
            assert "SAVED" in str(screen.query_one("#cal-luminance-import-feedback").render())
    asyncio.run(scenario())
