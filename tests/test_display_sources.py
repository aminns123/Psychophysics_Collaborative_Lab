import asyncio
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from textual.widgets import Button, Input, Select
from psychophysics_lab.config.models import MonitorProfile
from psychophysics_lab.config.monitor import _profile_from_dict
from psychophysics_lab.core.display import screen_info, DisplayInfo
from psychophysics_lab.ui.setup import PsyCoLabSetupApp
from psychophysics_lab.ui.profiles import ProfileScreen

ROOT=Path(__file__).resolve().parents[1]

def test_sources_round_trip_and_no_os_physical_measurement_claim():
    profile=MonitorProfile("local","Local",.5,.3,59.94,.6,measurement_sources={"physical_width_m":"manual","refresh_rate_hz":"os_mode"})
    assert _profile_from_dict(profile.to_dict()) == profile
    with pytest.raises(ValueError,match="Physical"):
        replace(profile,measurement_sources={"viewing_distance_m":"os_mode"}).validate()

@pytest.mark.parametrize("rate", [None,0,-1,float("nan"),float("inf")])
def test_unavailable_refresh_never_fabricated(rate):
    screen=SimpleNamespace(x=0,y=0,width=1920,height=1080,get_mode=lambda:SimpleNamespace(rate=rate))
    assert screen_info(screen,0).refresh_hz is None

def test_unimplemented_os_mode_is_unknown():
    def unavailable():
        raise NotImplementedError()
    assert screen_info(SimpleNamespace(x=0,y=0,width=1,height=1,get_mode=unavailable),0).refresh_hz is None

def test_detection_and_manual_override_are_explicit(tmp_path,monkeypatch):
    detected=DisplayInfo(0,0,0,1600,900,59.94,"A")
    monkeypatch.setattr("psychophysics_lab.ui.profiles.enumerate_displays",lambda:[detected])
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/"human")
        async with app.run_test(size=(100,30)) as pilot:
            app.push_screen(ProfileScreen(profile=app.monitor_profiles["legacy_reference_display"]))
            await pilot.pause()
            screen=app.screen
            original=screen.query_one("#profile-refresh_rate_hz",Input).value
            screen.query_one("#profile-detect",Button).press()
            await pilot.pause()
            assert screen.query_one("#profile-refresh_rate_hz",Input).value == original
            screen.query_one("#profile-use-detected",Button).press()
            await pilot.pause()
            assert screen.query_one("#profile-refresh_rate_hz",Input).value == "59.94"
            screen.query_one("#profile-pixel-width",Input).value="1920"
            screen.query_one("#profile-pixel-height",Input).value="1080"
            screen.query_one("#profile-physical_width_m",Input).value="0.52"
            screen.query_one("#profile-save",Button).press()
            await pilot.pause()
            saved=screen.profile
            assert saved.origin == "local"
            assert saved.expected_resolution_px == (1920,1080)
            assert saved.display_binding["width"] == 1600
            assert saved.measurement_sources["expected_resolution_px"] == "manual"
            assert saved.measurement_sources["refresh_rate_hz"] == "os_mode"
            assert saved.measurement_sources["physical_width_m"] == "manual"
            assert saved.geometry_status == "manual_unverified"
            assert not saved.qualified_experiments
    asyncio.run(scenario())
