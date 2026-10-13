"""Reproduce the reported local-display workflow using fixtures, never real profiles."""
import asyncio
import csv
from dataclasses import replace, asdict
import json
import math
from pathlib import Path
import pytest
from textual.widgets import Button, Input, Select, Static
from psychophysics_lab.config.local import config_root, save_profile, content_hash, preferences
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.preflight import validate_setup, compatible, human_blockers
from psychophysics_lab.config.readiness import profile_readiness
from psychophysics_lab.core.display import DisplayInfo
from psychophysics_lab.core.geometry_check import run_geometry_check, GeometryCheckRequest, record_geometry_measurement
from psychophysics_lab.core.display_tests import resolve_test
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC
from psychophysics_lab.stimuli.contrast_validation import validate_grating_command, grating_command_bounds
from psychophysics_lab.stimuli.spatial_calibration import resolve_spatial_geometry
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen, ChangeDisplayScreen
from psychophysics_lab.ui.unified_run import VirtualObserverOptionsScreen
from simulations.csf import DEFAULT_VALUES
from simulations.scenarios.run import run_scenario
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def calibrated_fixture(monkeypatch, tmp_path):
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    draft = save_profile(config_root(ROOT), replace(reference, id="legacy_reference_display_local",
        origin="local", physical_width_m=.340, physical_height_m=.210, viewing_distance_m=.5,
        expected_resolution_px=(1536,960), geometry_status="manual_unverified",
        measurement_sources={"physical_width_m":"manual", "physical_height_m":"manual", "viewing_distance_m":"manual"}))
    p = save_profile(config_root(ROOT), replace(draft, display_binding=asdict(DisplayInfo(0,0,0,1536,960,60,"test_display"))), expected_revision=1)
    request=GeometryCheckRequest(p.id,"visual_angle_deg",5)
    bar,plan=resolve_test(p,request,(1536,960))
    monkeypatch.setattr("psychophysics_lab.core.geometry_check._draw_fullscreen",lambda p,r:((1536,960),bar,plan))
    diagnostic=run_geometry_check(request,repo_root=ROOT,data_root=tmp_path/"unused")
    record_geometry_measurement(data_root=config_root(ROOT),report_file=diagnostic.report_file,measured_length_mm=44.)
    return p


@pytest.mark.parametrize("size",[(80,24),(100,30),(140,48)])
def test_exact_local_profile_calibrate_configure_review_virtual_restart_flow(tmp_path,monkeypatch,size):
    profile=calibrated_fixture(monkeypatch,tmp_path)
    assert not compatible(CSF_SPEC,profile)
    readiness=profile_readiness(CSF_SPEC,profile,repo_root=ROOT)
    assert readiness["bound"] and readiness["geometry_check"]["profile_revision"] == 2
    assert not readiness["experiment_qualified"] and not readiness["photometrically_calibrated"]
    assert readiness["geometry_check"]["measurement"]["error_percent"] == pytest.approx(.777,abs=.01)
    launched=[]
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        monkeypatch.setattr(app,"exit",lambda result=None:launched.append(result))
        async with app.run_test(size=size) as pilot:
            await pilot.pause(.2)
            assert app.query_one("#monitor-profile",Select).value == profile.id
            assert "340 × 210" in str(app.query_one("#monitor-summary",Static).render())
            app.query_one("#configure",Button).press()
            await pilot.pause(.2)
            screen=app.screen
            assert isinstance(screen,ExperimentConfigScreen)
            for name,value in {"number-conditions":"3","condition-values":"2,4,8",
                "Max-monitor-Luminance":"500", "Background-Luminance":"49", "Background-Screen-intensity":"0.374",
                "max-trials":"100", "staircases-per-condition":"2"}.items():
                screen.query_one("#field-"+name,Input).value=value
            await pilot.pause(.2)
            screen.query_one("#review",Button).press()
            await pilot.pause(.2)
            assert isinstance(app.screen,ReviewScreen)
            text=str(app.screen.query_one("#review-text",Static).render())
            assert profile.id in text and "340 × 210" in text and "0.500 m" in text
            assert "39.424" in text and "39.893" in text
            assert app.screen.request.monitor_profile_hash == content_hash(profile.to_dict())
            app.screen.query_one("#run-simulation",Button).press()
            await pilot.pause(.2)
            assert isinstance(app.screen,VirtualObserverOptionsScreen)
            app.screen.query_one("#virtual-seeds-0",Input).value="71"
            app.screen.query_one("#virtual-run",Button).press()
            await pilot.pause(.2)
    asyncio.run(scenario())
    assert len(launched)==1 and launched[0].monitor_profile_id==profile.id
    action=launched[0]
    result=run_scenario(experiment_id=action.experiment_id,scenario_id=action.scenario_id,
        repo_root=ROOT,data_root=tmp_path/"data",seeds=action.seeds,observer_parameters=action.observer_parameters,
        experiment_values=action.experiment_values,monitor_profile_id=action.monitor_profile_id,
        monitor_profile_hash=action.monitor_profile_hash)
    run=result.runs[0].artifacts.run_directory
    snapshot=json.loads((run/"monitor_profile.json").read_text())
    assert snapshot == json.loads(json.dumps(profile.to_dict())) and snapshot["revision"]==2
    manifest=json.loads((run/"manifest.json").read_text())
    resolved=json.loads((run/"resolved_experiment.json").read_text())
    runtime=json.loads((run/"runtime_display.json").read_text())
    assert manifest["monitor_profile_sha256"] == action.monitor_profile_hash
    assert resolved["monitor_profile"]==snapshot and runtime["profile_revision"]==2
    assert runtime["assumed_geometry"]["physical_size_m"] == [.34,.21]
    assert not runtime["physical_geometry_verified_by_simulation"]
    assert all(c.passed for c in validate_run(run)), [c for c in validate_run(run) if not c.passed]
    async def restart():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=size) as pilot:
            await pilot.pause(.2)
            assert app.query_one("#monitor-profile",Select).value==profile.id
    asyncio.run(restart())


def test_change_display_cancel_apply_retains_draft_and_requires_new_validation(tmp_path,monkeypatch):
    p=calibrated_fixture(monkeypatch,tmp_path)
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(80,24)) as pilot:
            app.query_one("#monitor-profile",Select).value="legacy_reference_display"
            app.query_one("#configure",Button).press()
            await pilot.pause(.2)
            config=app.screen
            config.query_one("#field-condition-values",Input).value="2,4,8"
            config.query_one("#field-number-conditions",Input).value="3"
            await pilot.pause(.2)
            config.query_one("#change-display",Button).press()
            await pilot.pause(.2)
            app.screen.query_one("#display-choice",Select).value=p.id
            app.screen.query_one("#display-cancel",Button).press()
            await pilot.pause(.2)
            assert config.monitor_profile_id=="legacy_reference_display"
            config.query_one("#change-display",Button).press()
            await pilot.pause(.2)
            app.screen.query_one("#display-choice",Select).value=p.id
            app.screen.query_one("#display-apply",Button).press()
            await pilot.pause(.2)
            assert app.screen is config and config.monitor_profile_id==p.id
            assert config.query_one("#field-condition-values",Input).value=="2,4,8"
            draft=preferences(config_root(ROOT))["calibration_experiment_draft"]
            assert draft["profile"]==p.id and draft["values"]["number_conditions"]=="3"
            config.query_one("#field-condition-unit",Select).value="degrees_per_cycle"
            await pilot.pause(.2)
            assert "periods in degrees/cycle" in str(config.query_one("#condition-unit-help",Static).render())
    asyncio.run(scenario())


def test_stale_review_and_multiseed_dispatch_rejected_before_any_acquisition(tmp_path,monkeypatch):
    p=calibrated_fixture(monkeypatch,tmp_path)
    values=CSF_SPEC.normalise_values(dict(DEFAULT_VALUES,condition_unit="cycles_per_degree",condition_values="2,8"))
    request=validate_setup(SetupRequest("synthetic_preview","new",CSF_SPEC.id,p.id,values,str(tmp_path/"data")),CSF_SPEC,p,mode="configuration")
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        captures=[]
        monkeypatch.setattr(app,"exit",lambda result=None:captures.append(result))
        async with app.run_test() as pilot:
            app.push_screen(ReviewScreen(request=request))
            await pilot.pause(.2)
            save_profile(config_root(ROOT),replace(p,viewing_distance_m=.55),expected_revision=2)
            app.screen.query_one("#run-simulation",Button).press()
            await pilot.pause(.2)
            assert isinstance(app.screen,ReviewScreen) and not captures
            assert "changed since review" in str(app.screen.query_one("#review-status",Static).render())
    asyncio.run(scenario())
    with pytest.raises(ValueError,match="changed since review"):
        run_scenario(experiment_id=CSF_SPEC.id,scenario_id="csf_baseline",data_root=tmp_path/"data",
            repo_root=ROOT,seeds=(1,2),monitor_profile_id=p.id,monitor_profile_hash=request.monitor_profile_hash)
    assert not list((tmp_path/"data").rglob("manifest.json"))  # A blocked UI may leave a diagnostic log, never acquisition.


def test_readiness_check_matches_exact_profile_revision(tmp_path,monkeypatch):
    p=calibrated_fixture(monkeypatch,tmp_path)
    updated=save_profile(config_root(ROOT),replace(p,viewing_distance_m=.55),expected_revision=2)
    assert profile_readiness(CSF_SPEC,updated,repo_root=ROOT)["geometry_check"] is None
    assert profile_readiness(CSF_SPEC,p,repo_root=ROOT)["geometry_check"] is not None


def test_contrast_numeric_risk_and_mode_specific_fail_closed(tmp_path,monkeypatch):
    from Events.adaptiveMethods import _update_probe_weber_contrast
    from Events.display_contrast import display_contrast_to_screen_intensity
    assert grating_command_bounds(1.,.374)==pytest.approx((-.126,.874))
    for n in (1,2,5):
        contrast=_update_probe_weber_contrast(1,1.,.35,.19208)
        assert contrast==pytest.approx(10**.35)
        assert display_contrast_to_screen_intensity(contrast,background_intensity=.374,maximum_intensity=1.)>1.
    for background in (.1,.374,.5,.8):
        limit=2*min(background,1-background)
        assert validate_grating_command(limit,background)[0] >= -1e-16
        with pytest.raises(ValueError,match="clip"):
            validate_grating_command(limit+1e-6,background)
    p=calibrated_fixture(monkeypatch,tmp_path)
    request=SetupRequest("P001","new",CSF_SPEC.id,p.id,dict(DEFAULT_VALUES))
    assert validate_setup(request,CSF_SPEC,p,mode="simulation").monitor_profile_id==p.id
    with pytest.raises(ValueError,match="not been qualified"):
        validate_setup(request,CSF_SPEC,p,mode="human")
    qualified=replace(p,qualified_experiments=(CSF_SPEC.id,))
    with pytest.raises(ValueError,match="Physical photometry"):
        validate_setup(request,CSF_SPEC,qualified,mode="human")
    # Fixture declarations satisfy the newly explicit CSF laboratory requirements;
    # this is test data, never a claim that hardware was measured by pytest.
    from psychophysics_lab.config.models import LuminanceCalibrationPoint
    qualified=replace(qualified,geometry_status="verified",timing_status="verified",
        calibration_status="verified",calibration_method="Laboratory instrument fixture",
        luminance_calibration=(LuminanceCalibrationPoint(.374,49.),LuminanceCalibrationPoint(1.,500.)))
    with pytest.raises(ValueError,match="clip"):
        validate_setup(request,CSF_SPEC,qualified,mode="human")
    safe=replace(request,experiment_values=dict(DEFAULT_VALUES,starting_probe_intensity=.7))
    assert validate_setup(safe,CSF_SPEC,qualified,mode="human").monitor_profile_id==qualified.id


def test_analysis_labels_censored_missing_staircases_and_keeps_legacy_units(tmp_path):
    from simulations.run import simulate
    from psychophysics_lab.analysis.thresholds import analyse_thresholds
    artifacts,_=simulate(repo_root=ROOT,data_root=tmp_path/"data",seed=7,values={"max_trials":30},analyse=False)
    result=analyse_thresholds(data_root=tmp_path/"data",run_directory=artifacts.run_directory,create_plot=False)
    summary=json.loads(result.summary_json.read_text())
    assert "Historical shader phase" in summary["condition_axis_label"]
    assert "INCOMPLETE" in summary["scientific_warning"] and "SYNTHETIC" in summary["scientific_warning"]


def test_missing_active_profile_is_visible_without_reference_fallback(tmp_path):
    from psychophysics_lab.config.local import save_preferences
    save_preferences(config_root(ROOT),active_monitor_profile_id="missing_lab_monitor")
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test() as pilot:
            await pilot.pause(.2)
            assert app.query_one("#monitor-profile",Select).value=="missing_lab_monitor"
            assert "unavailable" in str(app.query_one("#monitor-summary",Static).render())
            app.query_one("#configure",Button).press()
            await pilot.pause(.2)
            assert not isinstance(app.screen,ExperimentConfigScreen)
            assert "no fallback" in str(app.query_one("#setup-status",Static).render()).lower()
    asyncio.run(scenario())


def test_nonfinite_orientation_cannot_skip_sampling_check():
    from psychophysics_lab.stimuli.spatial_calibration import validate_requested_cpd
    p=load_monitor_profiles(ROOT)["legacy_reference_display"]
    with pytest.raises(ValueError,match="orientation"):
        validate_requested_cpd((999.,),resolve_spatial_geometry(p,(1920,1080)),orientation_rad=float("nan"))


def test_stale_ruler_measurement_rejected_in_calibration_page(tmp_path,monkeypatch):
    from psychophysics_lab.ui.setup import DisplayCheckScreen
    p=calibrated_fixture(monkeypatch,tmp_path)
    save_profile(config_root(ROOT),replace(p,viewing_distance_m=.55),expected_revision=2)
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test() as pilot:
            app.push_screen(DisplayCheckScreen())
            await pilot.pause(.2)
            app.screen.query_one("#geometry-measured",Input).value="45"
            app.screen.query_one("#record-geometry-measurement",Button).press()
            await pilot.pause(.2)
            assert "different profile revision" in str(app.screen.query_one("#geometry-status",Static).render())
    asyncio.run(scenario())


def test_cpd_scenario_report_uses_snapshot_units_and_no_legacy_relabel(tmp_path,monkeypatch):
    p=calibrated_fixture(monkeypatch,tmp_path)
    result=run_scenario(experiment_id=CSF_SPEC.id,scenario_id="csf_baseline",repo_root=ROOT,
        data_root=tmp_path/"data",seeds=(123,),monitor_profile_id=p.id,
        experiment_values={"condition_values":"2,4,8", "condition_unit":"cycles_per_degree",
            "number_conditions":3,"max_trials":120}, observer_parameters={"preferred_condition":2.})
    report=json.loads(result.report_file.read_text())
    assert report["experiment_evaluation"]["units"] == ["cycles_per_degree"]
    for point in report["experiment_evaluation"]["runs"][0]["conditions"]:
        assert point["condition_units"]=="cycles_per_degree" and "condition_legacy_units" not in point
    summary=json.loads(result.runs[0].analysis.summary_json.read_text())
    assert summary["condition_axis_label"]=="Spatial frequency (cycles/degree)"
