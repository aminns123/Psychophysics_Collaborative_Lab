import asyncio
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from textual.widgets import Button, Input, Select, Static
from textual.containers import VerticalScroll

from psychophysics_lab.config.models import MonitorProfile, SetupRequest
from psychophysics_lab.config.monitor import _profile_from_dict, load_monitor_profiles
from psychophysics_lab.config.local import config_root, save_profile, content_hash, save_preferences
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.core.display import DisplayInfo, resolve_binding, screen_info
from psychophysics_lab.core.display_tests import temporal_plan, frame_command, resolve_test, interval_summary
from psychophysics_lab.core.geometry_check import GeometryCheckRequest, run_geometry_check, record_geometry_measurement
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.experiments._internal.spec import ConfigField
from psychophysics_lab.ui.editor import editor_command, open_source
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]

def profile():
    return MonitorProfile("bench", "Bench monitor", .61, .35, 59.94, 1,
                          expected_resolution_px=(1920,1080), origin="local",
                          display_binding={"index":1,"x":1920,"y":0,"width":1920,"height":1080,"device_id":"monitor-B"},
                          qualified_experiments=("legacy_contrast_sensitivity",))

@pytest.mark.parametrize("value", [float('nan'),float('inf'),float('-inf'),True,"NaN"])
def test_numeric_configuration_rejects_invalid_numbers(value):
    with pytest.raises(ValueError):
        ConfigField("value","Value","float",default=1).coerce(value)

def test_integer_field_does_not_truncate():
    with pytest.raises(ValueError): ConfigField("n","N","int").coerce(1.8)

@pytest.mark.parametrize("field", ["physical_width_m","physical_height_m","viewing_distance_m","refresh_rate_hz","pyglet_wakeup_rate_hz"])
def test_profile_rejects_nonfinite_geometry(field):
    with pytest.raises(ValueError): replace(profile(), **{field: math.nan}).validate()

def test_refresh_fraction_and_revision_history_are_preserved(tmp_path):
    root = config_root(ROOT)
    before = {p.name: p.read_bytes() for p in (ROOT/"configs"/"monitors").glob('*.json')}
    first = save_profile(root, profile())
    second = save_profile(root, replace(first, viewing_distance_m=1.1), expected_revision=1)
    assert first.refresh_rate_hz == 59.94
    assert second.profile_uuid == first.profile_uuid and second.revision == 2
    assert (root/"profiles"/"bench"/"revision_000001.json").exists()
    assert load_monitor_profiles(ROOT)["bench"].viewing_distance_m == 1.1
    assert before == {p.name: p.read_bytes() for p in (ROOT/"configs"/"monitors").glob('*.json')}
    with pytest.raises(ValueError): save_profile(root, first, expected_revision=1)
    with pytest.raises(ValueError): save_profile(root, replace(first,id="legacy_reference_display"))

def test_configuration_root_must_be_separate_from_source_and_data(tmp_path, monkeypatch):
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR',str(ROOT/'nested'))
    with pytest.raises(ValueError): config_root(ROOT)
    monkeypatch.setenv('PSYCOLAB_CONFIG_DIR',str(tmp_path/'data'/'config'))
    with pytest.raises(ValueError): config_root(ROOT,tmp_path/'data')

def test_display_binding_reordering_and_missing_monitor():
    binding = profile().display_binding
    found = DisplayInfo(0,0,0,1920,1080,59.94,"monitor-B")
    other = DisplayInfo(1,1920,0,1920,1080,60,"monitor-A")
    assert resolve_binding(binding,[found,other]) == found
    with pytest.raises(ValueError): resolve_binding(binding,[other])
    with pytest.raises(ValueError): resolve_binding(binding,[found,replace(found,index=2)])
    legacy = {k:v for k,v in binding.items() if k!='device_id'}
    with pytest.raises(ValueError): resolve_binding(legacy,[found,replace(other,x=2000)])

def test_windows_display_identity_uses_pyglet_api():
    screen = SimpleNamespace(x=0,y=0,width=1920,height=1080,get_mode=lambda:SimpleNamespace(rate=59.94),get_device_name=lambda:"monitor-B")
    assert screen_info(screen,0).device_id == "monitor-B"
    assert screen_info(screen,0).refresh_hz == 59.94

def test_preflight_catches_changed_profiles_and_verified_luminance_mismatch():
    spec = get_experiment('legacy_contrast_sensitivity')
    values=spec.field_defaults() | {'Max_monitor_Luminance':500,'Background_Luminance':49,'Background_Screen_intensity':.374}
    request=SetupRequest('S001','new',spec.id,'bench',values)
    checked=validate_setup(request,spec,profile(),mode="configuration")
    with pytest.raises(ValueError,match='changed since review'):
        validate_setup(checked,spec,replace(profile(),viewing_distance_m=1.1),mode="configuration")
    verified=_profile_from_dict(profile().to_dict() | {'calibration_status':'verified','luminance_calibration':[{'screen_intensity':.374,'luminance_cdm2':49},{'screen_intensity':1.,'luminance_cdm2':500}]})
    with pytest.raises(ValueError,match='calibrated pair'):
        validate_setup(replace(request,experiment_values=values|{'Background_Screen_intensity':.38}),spec,verified,mode='configuration')

def test_quantisation_is_explicit_and_sine_is_a_distinct_plan():
    quantised=temporal_plan(60,8,'temporal_binary')
    assert quantised['realised_hz']==7.5 and not quantised['exactly_representable']
    exact=temporal_plan(60,10,'temporal_binary')
    assert exact['on_frames']==exact['off_frames']==3 and exact['exactly_representable']
    assert [frame_command(exact,i) for i in range(6)] == [1,1,1,0,0,0]
    sine=temporal_plan(60,8,'temporal_sine')
    assert sine['realised_hz']==8 and 'on_frames' not in sine
    assert frame_command(sine,0)==1
    assert temporal_plan(59.94,7.5,'temporal_binary')['realised_hz']==pytest.approx(7.4925)
    with pytest.raises(ValueError): temporal_plan(60,31,'temporal_binary')
    with pytest.raises(ValueError): temporal_plan(60,30,'temporal_sine')

def test_position_uses_tangent_and_off_axis_endpoints_and_checks_clipping():
    request=GeometryCheckRequest('bench','visual_angle_deg',5,test_kind='position',x_position=10,position_units='degrees')
    bar,plan=resolve_test(profile(),request,(1920,1080))
    assert plan['position_mm'][0]==pytest.approx(1000*math.tan(math.radians(10)))
    assert plan['off_axis_extent_deg'] < bar.realised_visual_angle_deg
    with pytest.raises(ValueError,match='beyond'):
        resolve_test(profile(),replace(request,x_position=80),(1920,1080))
    with pytest.raises(ValueError,match='Nyquist'):
        resolve_test(profile(),replace(request,test_kind='spatial',spatial_cpd=100),(1920,1080))

def test_frame_timing_reports_missed_intervals_without_certification():
    result=interval_summary([0,1/60,3/60,4/60],60)
    assert result['suspected_missed_refreshes']==1
    assert not result['software_timing_verified']

def test_editor_uses_explicit_project_and_real_file_without_shell(tmp_path,monkeypatch):
    repo=tmp_path/'Project with spaces & punctuation'
    repo.mkdir()
    first=repo/'first.py';second=repo/'second.py'
    first.write_text('x=1');second.write_text('x=2')
    calls=[]
    monkeypatch.setattr('psychophysics_lab.ui.editor.subprocess.Popen',lambda args,**kwargs:calls.append((args,kwargs)))
    open_source(repo,first,4,executable='code')
    open_source(repo,second,8,executable='code')
    assert calls[0][0][1]==calls[1][0][1]==str(repo)
    assert calls[0][0][-1]==str(first)+':4'
    assert calls[1][0][-1]==str(second)+':8'
    assert all('shell' not in kwargs and '--reuse-window' not in args for args,kwargs in calls)
    outside=tmp_path/'outside.py';outside.write_text('x=0')
    with pytest.raises(ValueError): editor_command(repo,outside,executable='code')

@pytest.mark.parametrize('size',[(80,24),(140,48)])
def test_navigation_does_not_move_with_scroll_content_page_or_resize(tmp_path,size):
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=size) as pilot:
            baseline=app.screen.query_one('#nav-setup',Button).region.y
            assert baseline==1
            for page in ('experiments','stimuli','display','data','help','setup'):
                button=app.screen.query_one('#nav-'+page,Button)
                assert await pilot.click(button)
                await pilot.pause()
                nav=app.screen.query_one('#hub-nav')
                assert nav.region.y==baseline
                assert all(0<=b.region.x and b.region.right<=size[0] for b in nav.query(Button))
                body=app.screen.query(VerticalScroll).first()
                for static in body.query(Static):
                    if static.id not in {'experiment-summary','monitor-summary'}:
                        static.update('Long content\n'*200)
                        break
                body.scroll_end(animate=False)
                await pilot.pause()
                assert nav.region.y==baseline
            await pilot.resize_terminal(100,32)
            await pilot.pause()
            assert app.screen.query_one('#hub-nav').region.y==baseline
    asyncio.run(scenario())

def test_config_draft_survives_help_and_returns_with_fixed_review_action(tmp_path):
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(80,30)) as pilot:
            app.screen.query_one('#participant',Input).value='S001'
            assert await pilot.click(app.screen.query_one('#configure',Button))
            await pilot.pause()
            assert isinstance(app.screen,ExperimentConfigScreen)
            app.screen.query_one('#field-max-trials',Input).value='42'
            await pilot.click(app.screen.query_one('#nav-help',Button));await pilot.pause()
            await pilot.click(app.screen.query_one('#nav-setup',Button));await pilot.pause()
            await pilot.click(app.screen.query_one('#configure',Button));await pilot.pause()
            assert app.screen.query_one('#field-max-trials',Input).value=='42'
            review=app.screen.query_one('#review',Button)
            y=review.region.y
            app.screen.query_one('#config-body').scroll_end(animate=False);await pilot.pause()
            assert review.region.y==y==4
    asyncio.run(scenario())

def test_profile_editor_saves_locally_without_replacing_reference(tmp_path,monkeypatch):
    from psychophysics_lab.ui.profiles import ProfileScreen
    monkeypatch.setattr('psychophysics_lab.ui.profiles.enumerate_displays',lambda:[DisplayInfo(1,1920,0,1920,1080,59.94,'monitor-B')])
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(100,40)) as pilot:
            app.open_hub_page('display');await pilot.pause()
            app.screen.query_one('#edit-profile',Button).press();await pilot.pause()
            assert isinstance(app.screen,ProfileScreen)
            screen=app.screen
            screen.query_one('#profile-id',Input).value='test_local'
            screen.query_one('#profile-refresh_rate_hz',Input).value='59.94'
            screen.query_one('#profile-detect',Button).press();await pilot.pause()
            screen.query_one('#profile-save',Button).press();await pilot.pause()
            saved=load_monitor_profiles(ROOT)['test_local']
            assert saved.origin=='local' and saved.revision==1 and saved.refresh_rate_hz==59.94
            assert saved.display_binding['device_id']=='monitor-B'
    asyncio.run(scenario())

def test_diagnostic_report_and_measurements_stay_in_local_configuration(tmp_path,monkeypatch):
    save_profile(config_root(ROOT),profile())
    request=GeometryCheckRequest('bench','physical_mm',100)
    bar,plan=resolve_test(profile(),request,(1920,1080))
    monkeypatch.setattr('psychophysics_lab.core.geometry_check._draw_fullscreen',lambda p,r:((1920,1080),bar,plan))
    data=tmp_path/'acquisition'
    result=run_geometry_check(request,repo_root=ROOT,data_root=data)
    assert result.report_file.is_relative_to(config_root(ROOT)) and not data.exists()
    payload=json.loads(result.report_file.read_text())
    assert payload['monitor_profile_sha256']==content_hash(load_monitor_profiles(ROOT)['bench'].to_dict())
    record_geometry_measurement(data_root=config_root(ROOT),report_file=result.report_file,measured_length_mm=101)
    updated=record_geometry_measurement(data_root=config_root(ROOT),report_file=result.report_file,measured_length_mm=100)
    assert updated['measurement_history'][-1]['measured_length_mm']==101
    with pytest.raises(ValueError): record_geometry_measurement(data_root=config_root(ROOT),report_file=result.report_file,measured_length_mm=math.nan)

def test_extension_adapter_runs_without_csf_configuration_or_hardware(tmp_path,monkeypatch):
    import psychophysics_lab.experiments._internal.registry as registry
    from _legacy_adapter_fixture import SPEC
    monkeypatch.setitem(registry._REGISTRY,SPEC.id,SPEC)
    request=SetupRequest('S001','new',SPEC.id,'legacy_reference_display',{'example_level':.7})
    result=run_request(request,repo_root=ROOT,data_root=tmp_path/'data')
    assert result.status=='returned' and result.accepted_trials==1
    manifest=json.loads(result.manifest_file.read_text())
    context=json.loads((result.run_directory/'trial_context.json').read_text())
    assert context['monitor_profile_sha256']==manifest['monitor_profile_sha256']
    assert 'random_provenance' in manifest
    assert all(c.passed for c in validate_run(result.run_directory)), [c for c in validate_run(result.run_directory) if not c.passed]

def test_primary_setup_error_is_preserved_with_final_manifest(tmp_path,monkeypatch):
    import psychophysics_lab.core.runner as runner
    values=get_experiment('legacy_contrast_sensitivity').field_defaults()|{'Max_monitor_Luminance':500,'Background_Luminance':49,'Background_Screen_intensity':.374,'condition_unit':'legacy_shader_radians','starting_probe_intensity':.7}
    error=RuntimeError('intentional initial config write failure')
    original=runner.atomic_write_json
    def failing(path,payload):
        if path.name=='experiment_config.json': raise error
        return original(path,payload)
    monkeypatch.setattr(runner,'atomic_write_json',failing)
    with pytest.raises(RuntimeError) as caught:
        run_request(SetupRequest('S001','new','legacy_contrast_sensitivity','legacy_reference_display',values),repo_root=ROOT,data_root=tmp_path/'data')
    assert caught.value is error
    manifests=list((tmp_path/'data').rglob('manifest.json'))
    assert len(manifests)==1
    final=json.loads(manifests[0].read_text())
    assert final['status']=='error' and 'finished_utc' in final
    assert 'intentional initial config write failure' in final['error']


def test_read_only_field_is_enforced_at_api_boundary():
    fixed = ConfigField("value", "Protected value", "int", default=2, editable=False)
    assert fixed.coerce(2) == 2
    with pytest.raises(ValueError, match="fixed specification"):
        fixed.coerce(3)

def test_concurrent_index_writers_do_not_lose_rows(tmp_path):
    import subprocess
    data = tmp_path / "shared_synthetic_data"
    script = "from pathlib import Path; import sys; from psychophysics_lab.data.index import upsert_run_index; upsert_run_index(Path(sys.argv[1]), {'run_uuid':sys.argv[2], 'participant_id':sys.argv[2]})"
    jobs = [subprocess.Popen([sys.executable, "-B", "-c", script, str(data), "worker_"+str(i)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(4)]
    for job in jobs:
        stdout, stderr = job.communicate(timeout=30)
        assert job.returncode == 0, stderr.decode(errors="replace")
    import csv
    with (data / "runs_index.csv").open(newline="", encoding="utf-8") as handle:
        assert {row["run_uuid"] for row in csv.DictReader(handle)} == {"worker_"+str(i) for i in range(4)}

def test_diagnostic_closes_window_if_resolution_plan_fails(monkeypatch):
    import psychophysics_lab.core.geometry_check as geometry
    windows = []
    unscheduled = []
    class FakeWindow:
        width, height = 1920, 1080
        def __init__(self, **kwargs):
            self.closed = False
            windows.append(self)
        def close(self): self.closed = True
        def flip(self): pass
    fake = SimpleNamespace(window=SimpleNamespace(Window=FakeWindow),gl=SimpleNamespace(),clock=SimpleNamespace(unschedule=unscheduled.append))
    monkeypatch.setitem(sys.modules,"pyglet",fake)
    monkeypatch.setattr(geometry,"select_screen",lambda p:(object(),{}))
    monkeypatch.setattr('psychophysics_lab.core.output_precision.create_output_window',
                        lambda screen, window_factory=None, **kw:
                            ((window_factory or FakeWindow)(**kw), {}))
    request = GeometryCheckRequest("bench","physical_mm",1000)
    with pytest.raises(ValueError): geometry._draw_fullscreen(profile(),request)
    assert windows[0].closed and len(unscheduled)==1
