"""Intent-specific TUI must be simple without weakening human-run validation."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest, LuminanceCalibrationPoint
from psychophysics_lab.experiments.contrast_sensitivity import SPEC as CSF_SPEC
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen

ROOT = Path(__file__).resolve().parents[1]


def test_test_intent_is_default_and_participant_identity_is_human_only(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(100,38)) as pilot:
            assert app.query_one("#run-intent",Select).value=="test"
            assert not app.query_one("#human-participant-panel",Vertical).display
            assert "No photometer" in str(app.query_one("#run-intent-help",Static).render())
            app.query_one("#configure",Button).press()
            await pilot.pause()
            editor=app.screen
            assert isinstance(editor,ExperimentConfigScreen)
            assert editor.participant_id=="synthetic_preview"
            app.pop_screen(); await pilot.pause()
            app.query_one("#run-intent",Select).value="human"
            await pilot.pause()
            assert app.query_one("#human-participant-panel",Vertical).display
            app.query_one("#participant",Input).value="H001"
            app.query_one("#configure",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,ExperimentConfigScreen)
            assert app.screen.participant_id=="H001"
    asyncio.run(scenario())


def test_review_shows_selected_mode_only_and_keeps_human_blockers(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    reference=load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile=save_profile(config_root(ROOT), replace(
        reference,id="intent_display",origin="local",
        display_binding={"index":0,"x":0,"y":0,"width":1920,"height":1080},
        expected_resolution_px=(1920,1080),
        calibration_method="photometer fake",
        luminance_calibration=(LuminanceCalibrationPoint(0.0,.3),
                                LuminanceCalibrationPoint(.3,25.0),
                                LuminanceCalibrationPoint(1.0,500.0)),
        calibration_status="manual_unverified",
    ))
    values=CSF_SPEC.field_defaults()|{
        "Max_monitor_Luminance":500.0,"Background_Luminance":25.0,
        "Background_Screen_intensity":.3,"starting_probe_intensity":.5
    }
    request=SetupRequest("synthetic_preview","new",CSF_SPEC.id,profile.id,values,str(tmp_path/"data"))
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(125,48)) as pilot:
            await app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            review=app.screen
            assert review.query_one("#review-run-intent",Select).value=="test"
            assert not review.query_one("#human-review-checks",Vertical).display
            assert review.query_one("#run-presentation-test",Button).display
            assert review.query_one("#run",Button).variant=="default"
            assert not review.readiness_report["human_ready"]
            review.query_one("#review-run-intent",Select).value="human"
            await pilot.pause()
            assert review.query_one("#human-review-checks",Vertical).display
            assert review.query_one("#run",Button).variant=="success"
            assert review.readiness_report["blockers"]
            review.query_one("#review-run-intent",Select).value="simulation"
            await pilot.pause()
            assert not review.query_one("#human-review-checks",Vertical).display
            assert review.query_one("#run-simulation",Button).variant=="primary"
    asyncio.run(scenario())
