"""Researcher-driven calibration guidance, lifecycle and manual diagnostic durations."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Static

from psychophysics_lab.config.local import content_hash
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.readiness import profile_readiness
from psychophysics_lab.core.display_tests import (
    diagnostic_timeout_reached, resolve_test,
)
from psychophysics_lab.core.geometry_check import GeometryCheckRequest
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC
from psychophysics_lab.ui.calibration_guide import (
    CalibrationGuideScreen, GUIDE_STEPS, guide_statuses
)
from psychophysics_lab.ui.setup import (
    DisplayCheckScreen, ExperimentConfigScreen,
    PsyCoLabSetupApp, ReviewScreen
)
from psychophysics_lab.ui.profiles import ProfileScreen

ROOT = Path(__file__).resolve().parents[1]


def test_manual_diagnostics_are_unlimited_and_timed_cases_still_work():
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    for seconds in (0, 61, 120, 99999):
        request = GeometryCheckRequest(profile.id, "visual_angle_deg",
                                       5, duration_s=seconds)
        _, plan = resolve_test(profile, request, (1920, 1080))
        assert plan["duration_s"] == seconds
        assert plan["termination"] == (
            "manual_escape_or_enter" if seconds == 0 else "manual_or_timeout"
        )
    assert not diagnostic_timeout_reached(0, 10000000)
    assert not diagnostic_timeout_reached(60, 59)
    assert diagnostic_timeout_reached(60, 60)
    assert diagnostic_timeout_reached(60, 120)
    with pytest.raises(ValueError, match="nonnegative"):
        resolve_test(profile, GeometryCheckRequest(profile.id, "visual_angle_deg",
                                                  5, duration_s=-1), (1920,1080))


def test_readiness_stage_progress_does_not_conflate_software_check_with_photometry(tmp_path,monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    profile=load_monitor_profiles(ROOT)["legacy_reference_display"]
    ready=profile_readiness(CSF_SPEC,profile,repo_root=ROOT,
                            values={"starting_probe_intensity":1.,
                                    "Background_Screen_intensity":.25})
    states=guide_statuses(ready, profile, {})
    assert len(states)==7
    assert states[3][0]=="missing"  # luminance is never inferred from a ruler
    assert states[4][0] in {"missing","partial"}
    assert states[5][0]=="missing"  # current starting command would clip
    assert states[6][0]=="verified"  # explicit legacy reference profile ID
    assert all(key in {"display","geometry","spatial","luminance",
                       "timing","contrast","qualification"} for key,_ in GUIDE_STEPS)


def test_review_guide_is_persistent_navigable_and_user_dismissible(tmp_path,monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path/"machine"))
    profile=load_monitor_profiles(ROOT)["legacy_reference_display"]
    values=CSF_SPEC.normalise_values({
        "Max_monitor_Luminance":500.,
        "Background_Luminance":49.,
        "Background_Screen_intensity":.25,
        "starting_probe_intensity":1.,
    })
    request=SetupRequest("P001","new",CSF_SPEC.id,profile.id,values,str(tmp_path/"data"))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(110,34)) as pilot:
            app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            review=app.screen
            assert isinstance(review,ReviewScreen)
            review.query_one("#review-calibration-guide",Button).press()
            await pilot.pause()
            guide=app.screen
            assert isinstance(guide,CalibrationGuideScreen)
            assert "qualification" == GUIDE_STEPS[guide.stage_index][0] or "contrast" == GUIDE_STEPS[guide.stage_index][0]
            assert "Step " in str(guide.query_one("#guide-progress",Static).render())
            assert "not an automatic" in str(guide.query_one("#guide-content",Static).render()).lower() or "NOT" in str(guide.query_one("#guide-content",Static).render())
            assert guide.query_one("#guide-next",Button).disabled
            guide.query_one("#guide-prev",Button).press()
            await pilot.pause()
            assert GUIDE_STEPS[guide.stage_index][0]=="contrast"
            await pilot.press("left")
            await pilot.pause()
            assert GUIDE_STEPS[guide.stage_index][0]=="timing"
            await pilot.press("right")
            await pilot.pause()
            assert GUIDE_STEPS[guide.stage_index][0]=="contrast"
            guide.query_one("#guide-close",Button).press()
            await pilot.pause()
            assert app.screen is review
            # Guide is still available; no run started, no data written.
            assert not (tmp_path/"data").exists()
    asyncio.run(scenario())


def test_guide_link_opens_current_profile_editor_without_changing_monitor(tmp_path,monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "machine"))
    profile=load_monitor_profiles(ROOT)["legacy_reference_display"]
    values=CSF_SPEC.normalise_values({
        "Max_monitor_Luminance":500.,
        "Background_Luminance":49.,
        "Background_Screen_intensity":.25,
        "starting_probe_intensity":.8,
    })
    request=SetupRequest("P001","new",CSF_SPEC.id,profile.id,values,str(tmp_path/"data"))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(110,34)) as pilot:
            app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            app.screen.query_one("#review-calibration-guide",Button).press()
            await pilot.pause()
            guide=app.screen
            assert GUIDE_STEPS[guide.stage_index][0]=="geometry" or GUIDE_STEPS[guide.stage_index][0]=="qualification"
            guide.query_one("#guide-open",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,(ProfileScreen,DisplayCheckScreen))
            if isinstance(app.screen,ProfileScreen):
                assert app.screen.profile.id==profile.id
            else:
                from textual.widgets import Select
                assert app.screen.query_one("#geometry-monitor",Select).value==profile.id
    asyncio.run(scenario())


def test_duration_control_defaults_to_manual_exit(tmp_path,monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path/"machine"))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one("#nav-display",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
            assert app.screen.query_one("#geometry-duration",Input).value=="0"
            assert app.screen._request().duration_s==0
            app.screen.query_one("#geometry-duration",Input).value="180"
            await pilot.pause()
            assert app.screen._request().duration_s==180
    asyncio.run(scenario())
