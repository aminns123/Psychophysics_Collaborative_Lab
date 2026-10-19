"""Calibration lifecycle regression tests; mocked screens prove no optical claims."""
from collections import deque
from dataclasses import replace
import asyncio
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from textual.widgets import Button, Input, Static, Select

from psychophysics_lab.config.local import config_root, save_profile, content_hash
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.readiness import diagnostic_matches_profile, profile_readiness
from psychophysics_lab.config.calibration_progress import calibration_progress
from psychophysics_lab.config.calibration_templates import example_luminance_document, demo_luminance_document, parse_luminance_measurements
from psychophysics_lab.core import geometry_check as geometry
from psychophysics_lab.core.display_tests import interval_summary, resolve_test
from psychophysics_lab.core.luminance_session import LocalLuminanceSession, LuminanceSessionRequest, summarise_readings
from psychophysics_lab.ui.setup import PsyCoLabSetupApp

ROOT = Path(__file__).resolve().parents[1]

def profile():
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    return replace(reference, id="test_lab", origin="local", revision=0,
                   physical_width_m=.610, physical_height_m=.350, viewing_distance_m=1., refresh_rate_hz=60.,
                   expected_resolution_px=(1920,1080),
                   display_binding={"device_id":"TEST_DISPLAY", "index":0,"x":0,"y":0,"width":1920,"height":1080},
                   measurement_sources={key:"manual" for key in ("physical_width_m","physical_height_m","viewing_distance_m")})

@pytest.mark.parametrize("factory", [list, deque])
@pytest.mark.parametrize("values", [[], [1.], [0., 1/60, 2/60, 5/60]])
def test_intervals_accept_lists_and_deques(factory, values):
    result = interval_summary(factory(values),60.)
    assert result["frames"] == len(values)
    assert result["software_timing_verified"] is False
    if len(values)>1:
        assert result["intervals_s"] == pytest.approx([1/60,1/60,3/60])
        assert result["median_interval_s"] == pytest.approx(1/60)
        assert result["maximum_interval_s"] == pytest.approx(3/60)
        assert result["suspected_missed_refreshes"] == 2

@pytest.mark.parametrize("values,rate", [([0,0],60),([1,0],60),([0,float('nan')],60),([0,1],0),([0,1],float('inf'))])
def test_timing_invalid_samples_fail_explicitly(values,rate):
    with pytest.raises(ValueError): interval_summary(deque(values),rate)

def test_long_timing_buffer_remains_bounded():
    recent=deque((n/60 for n in range(100000)),maxlen=6000)
    result=interval_summary(recent,60)
    assert result["frames"]==6000 and len(result["intervals_s"])==5999

def fake_pyglet(monkeypatch, *, key="ENTER", draw_error=False, no_flips=False):
    windows=[]
    scheduled=[]
    cleaned=[]
    keys=SimpleNamespace(ESCAPE=1,ENTER=2)
    class Window:
        def __init__(self, **kwargs):
            self.width,self.height=1920,1080
            self.closed=False
            self.events={}
            windows.append(self)
            assert kwargs["fullscreen"] and kwargs["vsync"]
            assert kwargs["screen"] == "SELECTED_SCREEN"
        def flip(self): pass
        def clear(self): pass
        def event(self, function):
            self.events[function.__name__]=function
            return function
        def close(self): self.closed=True
    def run():
        w=windows[-1]
        if draw_error: raise RuntimeError("mock GPU fault")
        for _ in range(0 if no_flips else 3):
            w.events["on_draw"]()
            w.flip()
        if key=="timeout":
            scheduled[-1](0)
        else:
            w.events["on_key_press"](getattr(keys,key),0)
    noop=lambda *args,**kwargs: None
    gl=SimpleNamespace(GL_QUADS=7,**{name:noop for name in ('glClearColor','glColor3f','glBegin','glVertex2f','glEnd')})
    module=SimpleNamespace(window=SimpleNamespace(Window=Window,key=keys),gl=gl,
        text=SimpleNamespace(Label=lambda *args,**kwargs:SimpleNamespace(draw=noop)),
        clock=SimpleNamespace(schedule_interval=lambda f,dt:scheduled.append(f),unschedule=lambda f:cleaned.append(f)),
        app=SimpleNamespace(run=run))
    monkeypatch.setitem(sys.modules,'pyglet',module)
    def output_window(screen, window_factory=None, **kwargs):
        return (window_factory or Window)(screen=screen, **kwargs), {
            'windows_report': {'status': 'unknown'}, 'application_obtained': {},
            'physical_precision_verified': False, 'message': 'Mock graphics only'}
    monkeypatch.setattr('psychophysics_lab.core.output_precision.create_output_window', output_window)
    monkeypatch.setattr(geometry,'select_screen',lambda p:('SELECTED_SCREEN',{'device_id':'TEST_DISPLAY'}))
    return windows,scheduled,cleaned

@pytest.mark.parametrize("key", ['ESCAPE','ENTER','timeout'])
@pytest.mark.parametrize("kind", ['size','spatial','temporal_binary','temporal_sine'])
def test_fullscreen_exit_report_and_cleanup(tmp_path,monkeypatch,key,kind):
    p=save_profile(config_root(ROOT),profile())
    windows,scheduled,cleaned=fake_pyglet(monkeypatch,key=key)
    request=geometry.GeometryCheckRequest(p.id,'physical_mm',100.,test_kind=kind,duration_s=1e-12 if key=='timeout' else 0.)
    artifacts=geometry.run_geometry_check(request,repo_root=ROOT)
    payload=json.loads(artifacts.report_file.read_text(encoding='utf-8'))
    assert payload['status']=='completed'
    assert payload['resolved_test']['termination_reason']==key.lower()
    assert payload['resolved_test']['frame_timing']['total_flips']==3
    assert payload['resolved_test']['frame_timing']['software_timing_verified'] is False
    assert windows[-1].closed and cleaned==scheduled
    stage={'size':'geometry','spatial':'spatial','temporal_binary':'timing','temporal_sine':'timing'}[kind]
    state=calibration_progress(p,config_root(ROOT))[stage]
    assert state['software_completed'] and not state['ready']

@pytest.mark.parametrize('failure',['gpu','no_frames'])
def test_failed_fullscreen_does_not_claim_completion(tmp_path,monkeypatch,failure):
    p=save_profile(config_root(ROOT),profile())
    windows,scheduled,cleaned=fake_pyglet(monkeypatch,draw_error=failure=='gpu',no_flips=failure=='no_frames')
    with pytest.raises((RuntimeError,ValueError)):
        geometry.run_geometry_check(geometry.GeometryCheckRequest(p.id,'physical_mm',100),repo_root=ROOT)
    report=geometry.latest_geometry_report(config_root(ROOT),p.id)
    assert json.loads(report.read_text(encoding='utf-8'))['status']=='error'
    assert calibration_progress(p,config_root(ROOT))['geometry']['state']=='failed'
    assert windows[-1].closed and cleaned==scheduled
    with pytest.raises(ValueError,match='completed'):
        geometry.record_geometry_measurement(data_root=config_root(ROOT),report_file=report,measured_length_mm=100,profile=p)

def test_photometry_export_failure_preserves_authoritative_reading(tmp_path,monkeypatch):
    import psychophysics_lab.core.luminance_session as lum
    session=LocalLuminanceSession(tmp_path,profile(),LuminanceSessionRequest(profile().id))
    original=lum.atomic_write_json
    def fail_pilot(path,data):
        if path==session.pilot_json_file: raise OSError('export disk fault')
        original(path,data)
    monkeypatch.setattr(lum,'atomic_write_json',fail_pilot)
    with pytest.warns(RuntimeWarning,match='Raw readings saved'):
        session.record(.5,'100')
    assert session.session['readings']==json.loads(session.session_file.read_text())['readings']
    assert len(session.session['readings'])==1
    monkeypatch.setattr(lum,'atomic_write_json',original)
    session.record(.5,'102')
    assert summarise_readings(session.session['readings'])[0]['n']==2
    assert json.loads(session.pilot_json_file.read_text())['measurements'][0]['luminance_cdm2']==101

def test_photometry_raw_failure_rolls_back_only_unsaved_reading(tmp_path,monkeypatch):
    import psychophysics_lab.core.luminance_session as lum
    session=LocalLuminanceSession(tmp_path,profile(),LuminanceSessionRequest(profile().id))
    session.record(.5,'100')
    def fail(*args): raise OSError('raw disk fault')
    monkeypatch.setattr(lum,'atomic_write_json',fail)
    with pytest.raises(OSError): session.record(.5,'102')
    assert session.session['readings']==json.loads(session.session_file.read_text())['readings']

def test_photometry_partial_session_is_not_complete(tmp_path):
    session=LocalLuminanceSession(tmp_path,profile(),LuminanceSessionRequest(profile().id))
    session.record(.5,'10')
    assert session.finish().status=='incomplete'
    with pytest.raises(ValueError,match='ended'): session.record(.5,'11')

def test_calibration_researcher_workflow_persistence_and_revision_policy(tmp_path,monkeypatch):
    from psychophysics_lab.config.monitor import _profile_from_dict
    from psychophysics_lab.config.preflight import validate_setup
    from psychophysics_lab.config.models import SetupRequest
    from psychophysics_lab.experiments._internal.registry import get_experiment
    root=config_root(ROOT)
    p=save_profile(root,profile())
    fake_pyglet(monkeypatch)
    ruler=geometry.run_geometry_check(geometry.GeometryCheckRequest(p.id,'physical_mm',100),repo_root=ROOT)
    assert calibration_progress(p,root)['geometry']['state']=='awaiting_measurement'
    geometry.run_geometry_check(geometry.GeometryCheckRequest(p.id,'physical_mm',100,test_kind='spatial'),repo_root=ROOT)
    assert geometry.latest_geometry_report(root,p.id,ruler_only=True)==ruler.report_file
    measured=geometry.record_geometry_measurement(data_root=root,report_file=ruler.report_file,measured_length_mm=101,profile=p)
    assert measured['measurement']['error_percent']==pytest.approx(1.)
    assert calibration_progress(p,root)['geometry']['state']=='awaiting_review'
    assert p.geometry_status!='verified'
    geometry.run_geometry_check(geometry.GeometryCheckRequest(p.id,'physical_mm',100,test_kind='temporal_binary'),repo_root=ROOT)
    document=example_luminance_document(p)
    document.update(photometer_model_and_method='Test fixture meter',measurement_date='2026-10-13',notes='Mock readings for isolated tests; no laboratory claim.',measurements=[{'screen_intensity':.5,'luminance_cdm2':50.},{'screen_intensity':1.,'luminance_cdm2':200.}])
    with pytest.raises(ValueError,match='FAKE'): parse_luminance_measurements(demo_luminance_document(p),p)
    imported=parse_luminance_measurements(document,p)
    p=save_profile(root,_profile_from_dict(p.to_dict()|imported),expected_revision=p.revision)
    assert load_monitor_profiles(ROOT)[p.id]==p
    assert calibration_progress(p,root)['luminance']['state']=='awaiting_review'
    assert calibration_progress(p,root)['geometry']['measurement_recorded']
    with pytest.raises(ValueError,match='revision'): parse_luminance_measurements(document,p)
    before=p
    p=save_profile(root,replace(p,notes='Metadata only',geometry_status='verified'),expected_revision=p.revision)
    assert diagnostic_matches_profile(json.loads(ruler.report_file.read_text()),p)
    assert calibration_progress(p,root)['geometry']['ready']
    spec=get_experiment('contrast_sensitivity')
    request=SetupRequest('test_subject','new',spec.id,p.id,spec.field_defaults())
    with pytest.raises(ValueError,match='qualified'): validate_setup(request,spec,p,mode='human')
    # Headless validation requires no instrument verification.
    validate_setup(request,spec,p,mode='simulation')
    readiness=profile_readiness(spec,p,repo_root=ROOT)
    assert readiness['calibration_stages']==calibration_progress(p,root)
    changed=save_profile(root,replace(p,viewing_distance_m=1.1,qualified_experiments=(spec.id,)),expected_revision=p.revision)
    assert changed.geometry_status=='manual_unverified' and not changed.qualified_experiments
    assert calibration_progress(changed,root)['geometry']['state']=='stale'
    with pytest.raises(ValueError,match='stale'):
        geometry.record_geometry_measurement(data_root=root,report_file=ruler.report_file,measured_length_mm=100,profile=changed)
    assert load_monitor_profiles(ROOT)[p.id]==changed

def test_geometry_axes_and_off_axis_numerical_examples():
    p=profile()
    req=geometry.GeometryCheckRequest(p.id,'physical_mm',100.,orientation='horizontal',x_position=50.)
    bar,plan=resolve_test(p,req,(1920,1080))
    assert bar.length_px==315
    assert bar.realised_length_mm==pytest.approx(100.078125)
    centre=plan['realised_position_mm'][0]/1000
    expected=math.degrees(math.atan(centre+bar.realised_length_mm/2000)-math.atan(centre-bar.realised_length_mm/2000))
    assert plan['off_axis_extent_deg']==pytest.approx(expected)
    bar,_=resolve_test(p,replace(req,orientation='vertical'),(1920,1080))
    assert bar.length_px==309 and bar.realised_length_mm==pytest.approx(100.1388888889)

def test_tui_shows_completed_and_measured_progress_after_refresh(tmp_path,monkeypatch):
    p=save_profile(config_root(ROOT),profile())
    fake_pyglet(monkeypatch)
    artifacts=geometry.run_geometry_check(geometry.GeometryCheckRequest(p.id,'physical_mm',100),repo_root=ROOT)
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one('#nav-display',Button).press()
            await pilot.pause()
            screen=app.screen
            assert screen.query_one('#geometry-monitor',Select).value==p.id
            assert 'AWAITING MEASUREMENT' in str(screen.query_one('#calibration-review-detail',Static).render())
            screen.query_one('#geometry-measured',Input).value='101'
            screen.query_one('#record-geometry-measurement',Button).press()
            await pilot.pause()
            assert 'AWAITING REVIEW' in str(screen.query_one('#calibration-review-detail',Static).render())
            # Saved observations remain amber until physical verification.
            assert screen.query_one('#cal-stage-geometry',Button).variant=='warning'
            assert '1.00%' in str(screen.query_one('#latest-geometry',Static).render())
    asyncio.run(scenario())

def test_missing_photometry_export_recovers_without_overwriting_edits(tmp_path,monkeypatch):
    import psychophysics_lab.core.luminance_session as lum
    session=LocalLuminanceSession(tmp_path,profile(),LuminanceSessionRequest(profile().id))
    session.record(.5,'100')
    session.record(1.,'200')
    session.finish()
    session.pilot_json_file.unlink()
    path=lum.recover_luminance_pilot(session.session_file)
    assert json.loads(path.read_text())['measurements'][0]['luminance_cdm2']==100.
    text=path.read_text()
    path.write_text(text.replace('REPLACE_WITH_REAL_METER_AND_MEASUREMENT_METHOD','Researcher edit'))
    lum.recover_luminance_pilot(session.session_file)
    assert 'Researcher edit' in path.read_text()

def test_interrupted_photometry_marks_error_and_preserves_observations(tmp_path,monkeypatch):
    import psychophysics_lab.core.luminance_session as lum
    p=save_profile(config_root(ROOT),profile())
    def fail(profile,request,session):
        session.record(.5,'100')
        raise RuntimeError('GPU disconnected')
    monkeypatch.setattr(geometry,'_draw_luminance_session',fail)
    with pytest.raises(RuntimeError,match='disconnected'):
        lum.run_interactive_luminance(LuminanceSessionRequest(p.id),repo_root=ROOT)
    raw=next((config_root(ROOT)/'calibration_sessions'/p.id).glob('*/session.json'))
    payload=json.loads(raw.read_text())
    assert payload['status']=='error' and len(payload['readings'])==1
    assert payload['finished_utc'] is not None

@pytest.mark.parametrize('field,value',[('physical_width_m',.62),('physical_height_m',.36),('viewing_distance_m',1.1),('expected_resolution_px',(1600,900)),('refresh_rate_hz',75.),('display_binding',{'device_id':'OTHER','index':1,'x':1920,'y':0,'width':1920,'height':1080})])
def test_physical_changes_reject_evidence_and_clear_qualification(field,value):
    p=replace(profile(),profile_uuid='profile-a',revision=2,geometry_status='verified',timing_status='verified',qualified_experiments=('legacy_contrast_sensitivity',))
    payload={'status':'completed','monitor_profile':p.to_dict(),'monitor_profile_sha256':content_hash(p.to_dict())}
    assert diagnostic_matches_profile(payload,replace(p,revision=3,notes='Only metadata'))
    assert not diagnostic_matches_profile(payload,replace(p,**{field:value}))
    root=config_root(ROOT)
    saved=save_profile(root,p)
    revised=save_profile(root,replace(saved,**{field:value}),expected_revision=saved.revision)
    assert revised.qualified_experiments==()

def test_same_geometry_other_profile_identity_cannot_reuse_evidence():
    p=profile()
    payload={'status':'completed','monitor_profile':p.to_dict(),'monitor_profile_sha256':content_hash(p.to_dict())}
    assert not diagnostic_matches_profile(payload,replace(p,id='different'))
    assert not diagnostic_matches_profile(payload,replace(p,profile_uuid='different-instance'))

def test_recovery_reports_one_failure_without_terminal_traceback(tmp_path,monkeypatch,capsys):
    import psychophysics_lab.app as launcher
    root=tmp_path/'checkout'
    root.mkdir()
    workspace=tmp_path/'data'
    request=geometry.GeometryCheckRequest('legacy_reference_display','physical_mm',100)
    sequence=iter([request,None])
    monkeypatch.setattr(launcher,'find_repo_root',lambda:root)
    monkeypatch.setattr(launcher,'default_data_root',lambda _:workspace)
    monkeypatch.setattr(launcher,'preferred_data_root',lambda _r,default:default)
    monkeypatch.setattr(launcher,'remember_data_root',lambda *args:None)
    monkeypatch.setattr('psychophysics_lab.ui.setup.run_setup_tui',lambda **kwargs:next(sequence))
    def fail(*args,**kwargs): raise RuntimeError('mock failed diagnostic')
    monkeypatch.setattr(geometry,'run_geometry_check',fail)
    reports=[]
    def log(exc,**kwargs):
        reports.append(exc)
        return tmp_path/'fault.log'
    monkeypatch.setattr(launcher,'write_crash_report',log)
    assert launcher._main([])==0
    captured=capsys.readouterr()
    assert len(reports)==1 and 'Traceback' not in captured.err
    assert 'recovery from 1 failed operation' in captured.out
    assert str(tmp_path/'fault.log') in captured.out


def test_photometry_derived_calculation_failure_keeps_raw_reading(tmp_path,monkeypatch):
    session=LocalLuminanceSession(tmp_path,profile(),LuminanceSessionRequest(profile().id))
    def broken_export(): raise ValueError('derived summary failure')
    monkeypatch.setattr(session,'_pilot',broken_export)
    with pytest.warns(RuntimeWarning,match='Raw readings saved'):
        session.record(.5,'100')
    assert len(session.session['readings'])==1
    assert session.session['readings']==json.loads(session.session_file.read_text())['readings']


def test_photometry_lock_failure_does_not_retain_unsaved_observation(tmp_path,monkeypatch):
    import psychophysics_lab.core.luminance_session as lum
    session=LocalLuminanceSession(tmp_path,profile(),LuminanceSessionRequest(profile().id))
    session.record(.5,'100')
    def unavailable(*args,**kwargs): raise OSError('calibration lock unavailable')
    monkeypatch.setattr(lum,'file_lock',unavailable)
    with pytest.raises(OSError,match='lock unavailable'): session.record(.5,'102')
    assert session.session['readings']==json.loads(session.session_file.read_text())['readings']
