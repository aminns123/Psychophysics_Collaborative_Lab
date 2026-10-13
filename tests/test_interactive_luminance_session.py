"""Headless acceptance of interactive psychophysical-display photometry logging.

Real fullscreen photometer output remains a Windows hardware acceptance task.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.config.calibration_templates import read_luminance_measurements
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.core.luminance_session import (
    LocalLuminanceSession, LuminanceSessionArtifacts, LuminanceSessionRequest,
    latest_luminance_pilot, parse_photometer_reading, stepped_command,
    summarise_readings, validate_luminance_session,
)
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, DisplayCheckScreen


ROOT = Path(__file__).resolve().parents[1]


def profile():
    return load_monitor_profiles(ROOT)["legacy_reference_display"]


def request(p=None, minimum=.25, step=.05):
    p=p or profile()
    return LuminanceSessionRequest(
        monitor_profile_id=p.id, background_command=minimum,
        command_step=step, patch_degrees=6.0
    )


def test_patch_is_physical_six_degree_square_on_black_and_background_limited():
    p=profile()
    plan=validate_luminance_session(request(p),p)
    expected=2*p.viewing_distance_m*math.tan(math.radians(3))
    assert plan["square_side_m"]==pytest.approx(expected)
    assert plan["patch_degrees"]==6.
    assert plan["surround_command"]==0.
    assert plan["starting_command"]==1.
    assert plan["minimum_command"]==.25
    assert plan["photometry_verified"] is False
    assert stepped_command(1.0,-1,.25,.05)==.95
    assert stepped_command(.30,-1,.25,.05)==.25
    assert stepped_command(.25,-1,.25,.05)==.25
    assert stepped_command(.25,1,.25,.05)==.3
    assert stepped_command(1.,1,.25,.05)==1.
    assert stepped_command(.26,-1,.25,.05)==.25
    with pytest.raises(ValueError, match="Direction"):
        stepped_command(1, 0, .25, .05)


@pytest.mark.parametrize("minimum,step",[(1.,.05),(-.1,.05),(.25,0),(.25,1.1),
                                          (.25,float("nan"))])
def test_invalid_sweep_bounds_fail_before_fullscreen(minimum,step):
    p=profile()
    with pytest.raises(ValueError):
        validate_luminance_session(request(p,minimum,step),p)


@pytest.mark.parametrize("reading",["", "-3.4","nan","inf","-inf","abc","."])
def test_invalid_photometer_inputs_are_rejected(reading):
    with pytest.raises(ValueError):
        parse_photometer_reading(reading)
    assert parse_photometer_reading("0")==0.
    assert parse_photometer_reading("  100.7  ")==pytest.approx(100.7)


def test_repeat_readings_persist_individually_and_aggregated_pilot_import(tmp_path):
    p=profile()
    session=LocalLuminanceSession(tmp_path,p,request(p))
    assert session.folder.is_relative_to(tmp_path)
    assert "calibration_sessions" in str(session.folder)
    assert session.session_file.exists()
    initial=json.loads(session.pilot_json_file.read_text())
    assert initial["measurements"][0]["luminance_cdm2"] is None
    assert initial["monitor_profile_id"]=="legacy_reference_display_local"
    assert initial["based_on_revision"]==0
    assert session.session["status"]=="in_progress"

    for value in ("100", "102", "101"):
        session.record(.5,value)
        persisted=json.loads(session.session_file.read_text())
        assert persisted["readings"][-1]["luminance_cdm2"]==float(value)
        assert len(persisted["readings"])==len(session.session["readings"])
    session.record(1., "180")
    assert session.session["readings"][0]["screen_intensity"]==.5
    assert len(session.session["readings"])==4
    summaries=summarise_readings(session.session["readings"])
    assert summaries[0]["screen_intensity"]==.5
    assert summaries[0]["luminance_cdm2"]==pytest.approx(101)
    assert summaries[0]["sample_sd_cdm2"]==pytest.approx(1)
    assert summaries[0]["n"]==3
    assert summaries[0]["readings_cdm2"]==[100.,102.,101.]

    artifacts=session.finish()
    assert artifacts.status=="completed"
    assert artifacts.readings_count==4
    assert artifacts.measured_commands==2
    assert latest_luminance_pilot(tmp_path,p.id)==artifacts.pilot_json_file
    completed=json.loads(artifacts.session_file.read_text())
    assert completed["status"]=="completed"
    assert len(completed["readings"])==4
    pilot=json.loads(artifacts.pilot_json_file.read_text())
    assert len(pilot["measurements"])==2
    assert pilot["measurements"][0]["luminance_cdm2"]==pytest.approx(101)
    assert pilot["measurements"][0]["n"]==3
    assert pilot["source_session_file"]==str(artifacts.session_file)

    # Researcher supplies actual instrument provenance before using the
    # EXISTING JSON Import -> Draft -> Save local revision workflow.
    with pytest.raises(ValueError, match="photometer"):
        read_luminance_measurements(str(artifacts.pilot_json_file),p)
    pilot["photometer_model_and_method"]="Research meter and centre-screen method"
    pilot["notes"]="Screen warmed up, instrument settings checked, uncertainty reviewed."
    artifacts.pilot_json_file.write_text(json.dumps(pilot))
    imported=read_luminance_measurements(str(artifacts.pilot_json_file),p)
    assert len(imported["luminance_calibration"])==2
    assert imported["luminance_calibration"][0]["luminance_cdm2"]==pytest.approx(101)
    assert imported["calibration_status"]=="manual_unverified"


def test_invalid_entry_does_not_change_saved_raw_or_summary(tmp_path):
    p=profile()
    session=LocalLuminanceSession(tmp_path,p,request())
    session.record(.5,"70.5")
    original=json.loads(session.session_file.read_text())
    before=json.loads(session.pilot_json_file.read_text())
    with pytest.raises(ValueError,match="nonnegative"):
        session.record(.5,"-20")
    with pytest.raises(ValueError,match="outside the configured"):
        session.record(.1,"90")
    with pytest.raises(ValueError,match="finite"):
        session.record(.5,"inf")
    assert json.loads(session.session_file.read_text())==original
    assert json.loads(session.pilot_json_file.read_text())==before


def test_new_session_never_overwrites_prior_raw_file(tmp_path):
    p=profile()
    s1=LocalLuminanceSession(tmp_path,p,request())
    s1.record(.5,"33")
    s1.finish()
    s2=LocalLuminanceSession(tmp_path,p,request())
    assert s2.folder!=s1.folder
    assert json.loads(s2.session_file.read_text())["readings"]==[]
    assert json.loads(s1.session_file.read_text())["readings"][0]["luminance_cdm2"]==33
    assert latest_luminance_pilot(tmp_path,p.id)==s2.pilot_json_file


def test_repeated_means_preserve_specific_profile_revision(tmp_path):
    p=replace(profile(),origin="local",id="local_display",revision=4)
    session=LocalLuminanceSession(tmp_path,p,request(p))
    session.record(.25,"12")
    session.record(1.,"320")
    pilot=json.loads(session.pilot_json_file.read_text())
    assert pilot["based_on_revision"]==4
    assert pilot["monitor_profile_id"]=="local_display"
    assert session.session["monitor_profile_sha256"]
    assert session.session["monitor_profile"]["revision"]==4
    assert session.session["resolved_test"]["photometry_verified"] is False


def test_tui_buttons_launch_request_and_show_editable_pilot_path(tmp_path,monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR",str(tmp_path/"machine"))
    monkeypatch.setattr("psychophysics_lab.core.display.preflight_fullscreen_display",lambda *_:None)
    opened=[]
    import os
    monkeypatch.setattr(os,"startfile",lambda path:opened.append(path),raising=False)

    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"human_workspace")
        launches=[]
        monkeypatch.setattr(app,"exit",lambda arg=None:launches.append(arg))
        async with app.run_test(size=(112,34)) as pilot:
            app.query_one("#nav-display",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
            screen=app.screen
            assert float(screen.query_one("#geometry-luminance-step",Input).value)==pytest.approx(.05)
            screen.query_one("#geometry-luminance-background",Input).value=".3"
            screen.query_one("#open-luminance-pilot",Button).press()
            await pilot.pause()
            assert "Editable luminance JSON" in str(screen.query_one("#geometry-status",Static).render())
            screen.query_one("#launch-luminance-session",Button).press()
            await pilot.pause()
            assert len(launches)==1
            launched=launches[0]
            assert isinstance(launched,LuminanceSessionRequest)
            assert launched.monitor_profile_id=="legacy_reference_display"
            assert launched.background_command==pytest.approx(.3)
            assert launched.command_step==pytest.approx(.05)
            assert launched.patch_degrees==6.
    asyncio.run(scenario())


def test_launcher_reopens_tui_after_interactive_photometry(tmp_path,monkeypatch):
    import psychophysics_lab.app as launcher
    import psychophysics_lab.core.luminance_session as lum
    root=tmp_path/"checkout"
    root.mkdir()
    workspace=tmp_path/"external_subject_data"
    prompts=[]
    measurement_request=LuminanceSessionRequest(
        "legacy_reference_display", background_command=.25,
        data_root=str(workspace)
    )
    def fake_tui(**kwargs):
        prompts.append(kwargs)
        return measurement_request if len(prompts)==1 else None
    monkeypatch.setattr(launcher,"find_repo_root",lambda:root)
    monkeypatch.setattr(launcher,"default_data_root",lambda _:workspace)
    monkeypatch.setattr(launcher,"preferred_data_root",lambda _r,default:default)
    monkeypatch.setattr("psychophysics_lab.ui.setup.run_setup_tui",fake_tui)
    pilot=tmp_path/"machine_config"/"pilot_luminance.json"
    raw=tmp_path/"machine_config"/"session.json"
    def fake_hardware(req, *, repo_root, data_root):
        assert req is measurement_request
        assert repo_root==root
        assert data_root==workspace.resolve()
        return LuminanceSessionArtifacts(raw,pilot,4,2,"completed")
    monkeypatch.setattr(lum,"run_interactive_luminance",fake_hardware)
    result=launcher._main([])
    assert result==0
    assert len(prompts)==2
    summary=prompts[1]["geometry_summary"]
    assert "completed" in summary
    assert "4" in summary and "2" in summary
    assert str(pilot) in summary
    assert "\\n" not in summary
    assert not workspace.joinpath("trials.tsv").exists()


def test_luminance_hardware_failure_reopens_tui_and_keeps_diagnostics(tmp_path,monkeypatch):
    import psychophysics_lab.app as launcher
    import psychophysics_lab.core.luminance_session as lum
    root=tmp_path/"checkout"
    root.mkdir()
    workspace=tmp_path/"workspace"
    prompts=[]
    req=LuminanceSessionRequest(
        "legacy_reference_display", background_command=.1, data_root=str(workspace)
    )
    def fake_tui(**kwargs):
        prompts.append(kwargs)
        return req if len(prompts)==1 else None
    monkeypatch.setattr(launcher,"find_repo_root",lambda:root)
    monkeypatch.setattr(launcher,"default_data_root",lambda _:workspace)
    monkeypatch.setattr(launcher,"preferred_data_root",lambda _r,default:default)
    monkeypatch.setattr("psychophysics_lab.ui.setup.run_setup_tui",fake_tui)
    monkeypatch.setattr(launcher,"write_crash_report",lambda *args,**kwargs:tmp_path/"error.log")
    def fail(*args,**kwargs):
        raise ValueError("Display driver interrupted")
    monkeypatch.setattr(lum,"run_interactive_luminance",fail)
    assert launcher._main([])==0
    assert len(prompts)==2
    assert "Display driver interrupted" in prompts[1]["geometry_summary"]
    assert str(tmp_path/"error.log") in prompts[1]["geometry_summary"]
