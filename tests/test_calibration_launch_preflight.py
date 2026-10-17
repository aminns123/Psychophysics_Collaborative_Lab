"""Windows fullscreen calibration launch: TUI preflight and recoverable failures."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.core.display import (
    DisplayInfo, preflight_fullscreen_display
)
from psychophysics_lab.config.local import preferences
from psychophysics_lab.ui.profiles import ProfileScreen
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, DisplayCheckScreen

ROOT = Path(__file__).resolve().parents[1]


def test_unbound_saved_profile_preflight_gives_actionable_instructions(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "data")
        called = []
        monkeypatch.setattr(app, "exit", lambda result=None: called.append(result))
        async with app.run_test(size=(85, 26)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            app.screen.query_one("#edit-profile", Button).press()
            await pilot.pause()
            editor = app.screen
            editor.query_one("#profile-physical_width_m", Input).value = ".534"
            editor.query_one("#profile-pixel-width", Input).value = "2560"
            editor.query_one("#profile-pixel-height", Input).value = "1440"
            editor.query_one("#profile-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            assert app.screen.query_one("#geometry-monitor", Select).value == "legacy_reference_display_local"
            assert app.monitor_profiles["legacy_reference_display_local"].display_binding is None
            app.screen.query_one("#launch-geometry", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            assert not called
            message = str(app.screen.query_one("#geometry-status", Static).render())
            assert "UNBOUND DRAFT" in message
            assert "Detect connected displays" in message
            assert "NOT launched" in message
    asyncio.run(scenario())


def test_detect_choose_bind_save_then_calibration_launches_selected_display(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    connected = DisplayInfo(0, 0, 0, 1600, 900, 60., "MONITOR-A")
    monkeypatch.setattr("psychophysics_lab.ui.profiles.enumerate_displays", lambda: [connected])
    monkeypatch.setattr("psychophysics_lab.core.display.enumerate_displays", lambda: [connected])
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "data")
        called=[]
        monkeypatch.setattr(app,"exit",lambda value=None: called.append(value))
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            app.screen.query_one("#edit-profile", Button).press()
            await pilot.pause()
            editor=app.screen
            editor.query_one("#profile-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            assert app.monitor_profiles["legacy_reference_display_local"].display_binding is None

            app.screen.query_one("#edit-profile", Button).press()
            await pilot.pause()
            editor=app.screen
            assert isinstance(editor,ProfileScreen)
            editor.query_one("#profile-detect",Button).press()
            await pilot.pause()
            assert editor.query_one("#profile-binding",Select).value == 0
            editor.query_one("#profile-use-detected",Button).press()
            await pilot.pause()
            assert editor.query_one("#profile-pixel-width",Input).value == "1600"
            assert editor.query_one("#profile-pixel-height",Input).value == "900"
            editor.query_one("#profile-save",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
            profile=app.monitor_profiles["legacy_reference_display_local"]
            assert profile.revision==2
            assert profile.display_binding["device_id"]=="MONITOR-A"
            assert profile.expected_resolution_px == (1600,900)
            app.screen.query_one("#launch-geometry", Button).press()
            await pilot.pause()
            assert len(called)==1
            assert called[0].monitor_profile_id == profile.id
            assert preferences(app.local_config_root)["active_monitor_profile_id"]==profile.id
    asyncio.run(scenario())


@pytest.mark.parametrize("case", ["unbound", "mismatched", "missing", "refresh"])
def test_monitor_binding_preflight_fails_closed_without_screen_fallback(case):
    from psychophysics_lab.config.models import MonitorProfile
    display=DisplayInfo(0,0,0,1920,1080,60.,"SCREEN-A")
    base=MonitorProfile("my_local", "My Monitor", .54,.32,60.,.9,
                        origin="local",expected_resolution_px=(1920,1080))
    if case=="unbound":
        chosen=base
    else:
        binding={"device_id":"SCREEN-A", "index":0,"x":0,"y":0,
                 "width":1920,"height":1080}
        chosen=replace(base,display_binding=binding)
        if case=="mismatched":
            chosen=replace(chosen,expected_resolution_px=(2560,1440))
        elif case=="missing":
            binding["device_id"]="OFFLINE"
            chosen=replace(chosen,display_binding=binding)
        elif case=="refresh":
            chosen=replace(chosen,refresh_rate_hz=144.)
    with pytest.raises(ValueError) as exc:
        preflight_fullscreen_display(chosen, [display])
    assert case=="unbound" and "UNBOUND DRAFT" in str(exc.value) or case!="unbound"


def test_fullscreen_geometry_runtime_exception_returns_to_tui_and_reports(tmp_path, monkeypatch):
    """A driver exception AFTER the Textual screen closes must not crash the launcher."""
    import psychophysics_lab.app as launcher
    from psychophysics_lab.core.geometry_check import GeometryCheckRequest
    root=tmp_path/"psycolab"
    root.mkdir()
    workspace=tmp_path/"data"
    prompts=[]
    captured=[]
    request=GeometryCheckRequest("legacy_reference_display", "physical_mm", 100.)
    def fake_tui(**kwargs):
        prompts.append(kwargs)
        return request if len(prompts)==1 else None
    monkeypatch.setattr(launcher,"find_repo_root",lambda:root)
    monkeypatch.setattr(launcher,"default_data_root",lambda _:workspace)
    monkeypatch.setattr(launcher,"preferred_data_root",lambda _r,default:default)
    monkeypatch.setattr(launcher,"remember_data_root",lambda *args:None)
    monkeypatch.setattr("psychophysics_lab.ui.setup.run_setup_tui",fake_tui)
    def broken_display(*args, **kwargs):
        raise ValueError("Bound display is missing or ambiguous.")
    monkeypatch.setattr("psychophysics_lab.core.geometry_check.run_geometry_check",broken_display)
    monkeypatch.setattr(launcher,"write_crash_report",lambda *args, **kwargs:tmp_path/"diagnostic.log")
    outcome=launcher._main([])
    assert outcome==0
    assert len(prompts)==2
    assert "geometry_summary" in prompts[1]
    assert "missing or ambiguous" in prompts[1]["geometry_summary"]
    assert str(tmp_path/"diagnostic.log") in prompts[1]["geometry_summary"]
