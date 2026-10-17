"""Subjective spatial evidence, isolated records and mocked fullscreen returns."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.config.local import config_root, save_profile, preferences, save_preferences
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.calibration_progress import calibration_progress
from psychophysics_lab.config.spatial_observation import record_observation, observations, read_report
from psychophysics_lab.core.geometry_check import GeometryCheckRequest, run_geometry_check
from psychophysics_lab.core.display_tests import resolve_test
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, DisplayCheckScreen

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def display():
    reference = load_monitor_profiles(ROOT)['legacy_reference_display']
    return save_profile(config_root(ROOT), replace(reference, id='spatial_lab', origin='local',
        expected_resolution_px=(1920, 1080), display_binding={'device_id': 'MOCK', 'index': 0, 'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
        measurement_sources={k: 'manual' for k in ('physical_width_m','physical_height_m','viewing_distance_m')}))


def present(monkeypatch, display, **settings):
    def draw(profile, request):
        bar, plan = resolve_test(profile, request, (1920,1080))
        return (1920,1080), bar, plan
    monkeypatch.setattr('psychophysics_lab.core.geometry_check._draw_fullscreen', draw)
    request = GeometryCheckRequest(display.id, 'visual_angle_deg', 5, test_kind='spatial', **settings)
    return run_geometry_check(request, repo_root=ROOT).report_file


def assess(display, report, **answer):
    return record_observation(config_root(ROOT), report, display,
                              **({'assessment':'consistent','abnormality':'none'} | answer))


def test_presentation_does_not_complete_and_observation_is_immutable(monkeypatch, display):
    root=config_root(ROOT)
    report=present(monkeypatch, display)
    original=report.read_bytes()
    state=calibration_progress(display,root)['spatial']
    assert state['software_completed'] and not state['completed']
    assert state['state']=='awaiting_observation'
    from psychophysics_lab.config.readiness import profile_readiness
    from psychophysics_lab._reference_csf.experiment_definition import CSF_SPEC
    from psychophysics_lab.ui.calibration_guide import guide_statuses
    assert guide_statuses(profile_readiness(CSF_SPEC,display,repo_root=ROOT),display,{})[2][0]=='partial'
    record=assess(display,report,observed_count=5)
    state=calibration_progress(display,root)['spatial']
    assert state['completed'] and not state['verified']
    assert guide_statuses(profile_readiness(CSF_SPEC,display,repo_root=ROOT),display,{})[2][0]=='recorded'
    assert not state['physical_spatial_frequency_certified']
    assert record['diagnostic_uuid']==json.loads(original)['diagnostic_uuid']
    assert report.read_bytes()==original
    assert assess(display,report,observed_count=5)==record
    assert len(list((report.parent/'spatial_observations').glob('*.json')))==1
    assert len(list((root/'profiles'/display.id).glob('revision_*.json')))==1


@pytest.mark.parametrize('assessment,abnormality', [('uncertain','none'),('discrepancy','none'),
    ('not_assessed','none'),('consistent','aliasing'),('consistent','not_assessed')])
def test_unsuccessful_observations_never_turn_spatial_green(monkeypatch, display, assessment, abnormality):
    report=present(monkeypatch,display)
    assess(display,report,assessment=assessment,abnormality=abnormality,observed_count=2.7)
    assert not calibration_progress(display,config_root(ROOT))['spatial']['completed']


@pytest.mark.parametrize('change', [dict(viewing_distance_m=1.2), dict(physical_width_m=.7),
    dict(physical_height_m=.4), dict(expected_resolution_px=(1280,720)), dict(display_binding={'device_id':'OTHER'})])
def test_physical_change_invalidates_observation(monkeypatch,display,change):
    report=present(monkeypatch,display); assess(display,report)
    changed=replace(display,**change)
    assert calibration_progress(changed,config_root(ROOT))['spatial']['state']=='stale'
    with pytest.raises(ValueError,match='stale'):
        assess(changed,report)


def test_metadata_revision_preserves_evidence_and_failed_attempt_preserves_prior(monkeypatch,display):
    report=present(monkeypatch,display); assess(display,report)
    changed=save_profile(config_root(ROOT),replace(display,notes='Only metadata'),expected_revision=display.revision)
    assert calibration_progress(changed,config_root(ROOT))['spatial']['completed']
    monkeypatch.setattr('psychophysics_lab.core.geometry_check._draw_fullscreen',lambda *args: (_ for _ in ()).throw(RuntimeError('GPU failed')))
    with pytest.raises(RuntimeError):
        run_geometry_check(GeometryCheckRequest(display.id,'visual_angle_deg',5,test_kind='spatial'),repo_root=ROOT)
    state=calibration_progress(changed,config_root(ROOT))['spatial']
    assert state['completed'] and 'latest attempt failed' in state['message']


def test_separate_presentations_and_observations_and_exact_report_link(monkeypatch,display):
    first=present(monkeypatch,display); a=assess(display,first)
    second=present(monkeypatch,display,spatial_cpd=2)
    assert not calibration_progress(display,config_root(ROOT))['spatial']['completed']
    b=assess(display,second,assessment='discrepancy')
    c=assess(display,second)
    assert a['diagnostic_uuid']!=b['diagnostic_uuid']
    assert b['observation_uuid']!=c['observation_uuid']
    assert len(observations(second,json.loads(second.read_text())))==2
    assert calibration_progress(display,config_root(ROOT))['spatial']['completed']
    payload=json.loads(second.read_text()); payload['request']['spatial_cpd']=3
    second.write_text(json.dumps(payload))
    assert observations(second,payload)==[]
    with pytest.raises(ValueError):
        assess(replace(display,id='another_display'),first)


@pytest.mark.parametrize('orientation,offset', [('horizontal',0),('horizontal',100),('vertical',0)])
def test_nominal_cycles_use_resolved_extent_without_peak_tolerance(monkeypatch,display,orientation,offset):
    report=present(monkeypatch,display,orientation=orientation,x_position=offset)
    payload=json.loads(report.read_text())
    plan=payload['resolved_test']
    assert plan['spatial']['cycles_across_patch']==pytest.approx(plan['off_axis_extent_deg'])
    if not offset: assert plan['spatial']['cycles_across_patch']==pytest.approx(5,abs=.02)
    # A discrepancy is retained, never coerced towards the predicted count.
    answer=assess(display,report,assessment='discrepancy',observed_count=19.5,count_kind='bright_maxima')
    assert answer['observed_count']==19.5


@pytest.mark.parametrize('count',[float('nan'),float('inf'),-1,True])
def test_invalid_counts_rejected(monkeypatch,display,count):
    with pytest.raises(ValueError): assess(display,present(monkeypatch,display),observed_count=count)


@pytest.mark.parametrize('stage,kind', [('geometry','size'),('spatial','spatial'),('timing','temporal_sine'),
                                     ('luminance','luminance_session'),('luminance','luminance_patch')])
@pytest.mark.parametrize('failed',[False,True])
def test_fullscreen_navigation_roundtrip_is_same_stage(tmp_path,display,stage,kind,failed):
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(130,45)) as pilot:
            app.open_hub_page('display'); await pilot.pause()
            screen=app.screen
            screen.query_one('#geometry-monitor',Select).value=display.id
            screen._go_to_stage(stage)
            screen.query_one('#geometry-value',Input).value='4.2'
            screen._save_fullscreen_navigation(kind)
        message='Diagnostic failed: see local log' if failed else 'Software presentation finished'
        restart=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data',geometry_summary=message)
        async with restart.run_test(size=(130,45)) as pilot:
            await pilot.pause()
            assert isinstance(restart.screen,DisplayCheckScreen)
            screen=restart.screen
            assert screen.active_calibration_stage==stage
            assert screen.query_one('#geometry-monitor',Select).value==display.id
            assert screen.query_one('#geometry-value',Input).value=='4.2'
            assert message in str(screen.query_one('#geometry-status',Static).render())
            assert preferences(config_root(ROOT))['calibration_navigation'] is None
            assert len(list((config_root(ROOT)/'profiles'/display.id).glob('revision_*.json')))==1
            screen.query_one('#calibration-next',Button).press(); await pilot.pause()
            assert isinstance(restart.screen,DisplayCheckScreen)
    asyncio.run(scenario())


def test_spatial_tui_observation_records_then_deliberately_advances(tmp_path,monkeypatch,display):
    report=present(monkeypatch,display)
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(130,45)) as pilot:
            app.open_hub_page('display'); await pilot.pause()
            screen=app.screen; screen._go_to_stage('spatial')
            assert screen.query_one('#cal-stage-spatial',Button).variant=='error'
            screen.query_one('#spatial-assessment',Select).value='consistent'
            screen.query_one('#spatial-abnormality',Select).value='none'
            screen.query_one('#spatial-observed-count',Input).value='5'
            screen.query_one('#record-spatial-observation',Button).press(); await pilot.pause()
            assert screen.active_calibration_stage=='spatial'
            assert screen.query_one('#cal-stage-spatial',Button).variant=='success'
            assert len(observations(report,json.loads(report.read_text())))==1
            screen.query_one('#calibration-next',Button).press(); await pilot.pause()
            assert screen.active_calibration_stage=='luminance'
    asyncio.run(scenario())


@pytest.mark.parametrize('stage,button,kind',[('geometry','launch-geometry','size'),
    ('spatial','launch-spatial','spatial'),('timing','launch-temporal','temporal_binary'),
    ('luminance','launch-patch','luminance_patch'),('luminance','launch-luminance-session','luminance_session')])
def test_real_launch_handler_records_context_before_exiting(tmp_path,monkeypatch,display,stage,button,kind):
    monkeypatch.setattr('psychophysics_lab.core.display.preflight_fullscreen_display',lambda profile: None)
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            app.open_hub_page('display'); await pilot.pause()
            page=app.screen; page._go_to_stage(stage)
            actions=[]
            monkeypatch.setattr(app,'exit',lambda request: actions.append(request))
            page.query_one('#'+button,Button).press(); await pilot.pause()
            assert len(actions)==1
            saved=preferences(config_root(ROOT))['calibration_navigation']
            assert saved['stage']==stage and saved['diagnostic_kind']==kind
            assert saved['profile']==display.id
    asyncio.run(scenario())


@pytest.mark.parametrize('button',['calibration-return','calibration-finish'])
def test_review_destination_survives_fullscreen_until_explicit_return(tmp_path,display,button):
    from dataclasses import asdict
    from psychophysics_lab.config.models import SetupRequest
    from psychophysics_lab._reference_csf.experiment_definition import CSF_SPEC
    from psychophysics_lab.ui.setup import ReviewScreen
    request=SetupRequest('H001','new',CSF_SPEC.id,display.id,CSF_SPEC.field_defaults() | {
        'Max_monitor_Luminance':500., 'Background_Luminance':49.,
        'Background_Screen_intensity':.25, 'starting_probe_intensity':.55},str(tmp_path/'data'))
    snapshot=display.to_dict()
    save_preferences(config_root(ROOT),calibration_review_return={'request':asdict(request),'snapshot':snapshot},
        calibration_navigation={'section':'calibrate','profile':display.id,'stage':'spatial',
                                'settings':{},'diagnostic_kind':'spatial','return_to_review':True})
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data',geometry_summary='Software test finished')
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
            assert app.screen.active_calibration_stage=='spatial'
            review=app.screen_stack[-2]
            assert isinstance(review,ReviewScreen) and review.reviewed_profile_snapshot==snapshot
            if button=='calibration-finish': app.screen._go_to_stage('review')
            app.screen.query_one('#'+button,Button).press(); await pilot.pause()
            assert app.screen is review
            assert preferences(config_root(ROOT))['calibration_review_return'] is None
    asyncio.run(scenario())


@pytest.mark.parametrize('kind',['spatial','temporal_binary','luminance_session'])
@pytest.mark.parametrize('failure',[None,RuntimeError,KeyboardInterrupt])
def test_application_loop_returns_without_advancing_on_success_failure_or_abort(tmp_path,monkeypatch,display,kind,failure):
    import psychophysics_lab.app as launcher
    from psychophysics_lab.core.luminance_session import LuminanceSessionRequest
    from types import SimpleNamespace
    stage={'spatial':'spatial','temporal_binary':'timing','luminance_session':'luminance'}[kind]
    save_preferences(config_root(ROOT),calibration_active_stage=stage)
    action=(LuminanceSessionRequest(display.id,0,.05,data_root=str(tmp_path/'data')) if kind=='luminance_session'
            else GeometryCheckRequest(display.id,'visual_angle_deg',5,test_kind=kind,data_root=str(tmp_path/'data')))
    prompts=[]
    def tui(**kwargs):
        prompts.append(kwargs)
        return action if len(prompts)==1 else None
    def diagnostic(*args,**kwargs):
        if failure: raise failure('mock interrupted diagnostic')
        return SimpleNamespace(report_file=tmp_path/'diagnostic.json',resolution_px=(1920,1080),
            intended_length_mm=100.,realised_length_mm=100.,realised_visual_angle_deg=5.,
            status='completed',readings_count=0,measured_commands=0,session_file=tmp_path/'session.json',
            pilot_json_file=tmp_path/'pilot.json',export_warning=None)
    monkeypatch.setattr(launcher,'find_repo_root',lambda:ROOT)
    monkeypatch.setattr(launcher,'default_data_root',lambda _:tmp_path/'data')
    monkeypatch.setattr(launcher,'preferred_data_root',lambda _r,default:default)
    monkeypatch.setattr(launcher,'remember_data_root',lambda *args:None)
    monkeypatch.setattr(launcher,'write_crash_report',lambda *args,**kwargs:tmp_path/'error.log')
    monkeypatch.setattr('psychophysics_lab.ui.setup.run_setup_tui',tui)
    monkeypatch.setattr('psychophysics_lab.core.geometry_check.run_geometry_check',diagnostic)
    monkeypatch.setattr('psychophysics_lab.core.luminance_session.run_interactive_luminance',diagnostic)
    assert launcher._main([])==0 and len(prompts)==2
    assert prompts[1]['geometry_summary']
    assert preferences(config_root(ROOT))['calibration_active_stage']==stage
    if failure: assert str(tmp_path/'error.log') in prompts[1]['geometry_summary']


def test_calibration_draft_with_old_report_path_does_not_crash_or_restore_dynamic_select(tmp_path, display):
    """Reproduces Windows InvalidSelectValueError from check_005 saved report."""
    stale_path = 'diagnostics/display_geometry/' + display.id + '/2026-10-14/check_005/geometry_check.json'
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / 'data')
        # A prior UI revision could save *all* Select values in display_draft.
        app.display_draft = {
            'spatial-report': stale_path,
            'geometry-monitor': display.id,
            'geometry-value': '4.2',
        }
        async with app.run_test(size=(110, 40)) as pilot:
            app.open_hub_page('display')
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, DisplayCheckScreen)
            assert screen.query_one('#geometry-value', Input).value == '4.2'
            assert screen.query_one('#geometry-monitor', Select).value == display.id
            assert screen.query_one('#spatial-report', Select).value != stale_path
            # Leaving the page only remembers actual diagnostic input fields.
            app.open_hub_page('setup')
            await pilot.pause()
            assert 'spatial-report' not in app.display_draft
            app.open_hub_page('display')
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
    asyncio.run(scenario())


def test_dynamic_report_selection_is_never_saved_as_fullscreen_navigation(tmp_path, display):
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / 'data')
        async with app.run_test(size=(110, 40)) as pilot:
            app.open_hub_page('display')
            await pilot.pause()
            app.screen._go_to_stage('spatial')
            app.screen._save_fullscreen_navigation('spatial')
            settings = preferences(config_root(ROOT))['calibration_navigation']['settings']
            assert 'spatial-report' not in settings
            assert 'geometry-value' in settings
    asyncio.run(scenario())


def test_removed_monitor_in_calibration_draft_uses_available_default(tmp_path):
    """Previously saved Select choices must never crash a new monitor setup."""
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / 'data')
        app.display_draft = {'geometry-monitor': 'no-longer-connected-monitor'}
        async with app.run_test(size=(110, 40)) as pilot:
            app.open_hub_page('display')
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            assert app.screen.query_one('#geometry-monitor', Select).value in app.monitor_profiles
    asyncio.run(scenario())
