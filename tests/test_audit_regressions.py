"""Regression coverage from the local Windows bug audit; no real acquisition."""
import asyncio
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from psychophysics_lab.config.models import MonitorProfile, SetupRequest
from psychophysics_lab.config.monitor import _profile_from_dict, load_monitor_profiles
from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.core.display import DisplayInfo, select_screen
from psychophysics_lab.core.display_tests import resolve_test
from psychophysics_lab.core.geometry_check import GeometryCheckRequest

ROOT = Path(__file__).resolve().parents[1]


def profile(**changes):
    return replace(MonitorProfile('legacy_reference_display', 'Reference', .61, .35, 60, 1), **changes)


class Screen:
    def __init__(self, name, x=0, width=1920, rate=60):
        self.x, self.y, self.width, self.height = x, 0, width, 1080
        self.name, self.rate = name, rate

    def get_device_name(self):
        return self.name

    def get_mode(self):
        return SimpleNamespace(rate=self.rate)


def mock_display(monkeypatch, screens, default):
    calls = []
    display = SimpleNamespace(get_screens=lambda: screens, get_default_screen=lambda: default)
    def get_display():
        calls.append(True)
        return display
    monkeypatch.setitem(sys.modules, 'pyglet', SimpleNamespace(canvas=SimpleNamespace(get_display=get_display)))
    return calls


def test_default_screen_is_matched_to_enumerated_handle(monkeypatch):
    screens = [Screen('secondary', -1920), Screen('primary')]
    calls = mock_display(monkeypatch, screens, Screen('primary'))
    screen, identity = select_screen(profile())
    assert screen is screens[1]
    assert identity['index'] == 1
    assert identity['binding_status'] == 'legacy_default_unverified'
    assert len(calls) == 1


def test_default_without_device_id_uses_unique_geometry(monkeypatch):
    screens = [Screen(None, -1920), Screen(None)]
    mock_display(monkeypatch, screens, Screen(None))
    assert select_screen(profile())[0] is screens[1]


@pytest.mark.parametrize('screens,default', [
    ([], Screen('primary')),
    ([Screen('other')], Screen('missing')),
    ([Screen(None), Screen(None)], Screen(None)),
])
def test_default_missing_or_ambiguous_fails_closed(monkeypatch, screens, default):
    mock_display(monkeypatch, screens, default)
    with pytest.raises(ValueError, match='display|monitor|screen'):
        select_screen(profile())


def test_explicit_binding_survives_reordered_handles(monkeypatch):
    screens = [Screen('B'), Screen('A', -1920)]
    mock_display(monkeypatch, screens, Screen('A', -1920))
    binding = asdict(DisplayInfo(1, 1920, 0, 1920, 1080, 60, 'B'))
    selected, identity = select_screen(profile(id='local', origin='local', display_binding=binding))
    assert selected is screens[0]
    assert identity['binding_status'] == 'explicit'


@pytest.mark.parametrize('change', [{'device_id': 'missing'}, {'width': 1280, 'device_id': None}])
def test_explicit_binding_never_falls_back(monkeypatch, change):
    mock_display(monkeypatch, [Screen('A')], Screen('A'))
    binding = asdict(DisplayInfo(0, 0, 0, 1920, 1080, 60, 'A')) | change
    with pytest.raises(ValueError, match='missing|ambiguous'):
        select_screen(profile(id='local', display_binding=binding))


def test_explicit_mode_mismatch_rejected(monkeypatch):
    mock_display(monkeypatch, [Screen('A', rate=75)], Screen('A', rate=75))
    binding = asdict(DisplayInfo(0, 0, 0, 1920, 1080, 60, 'A'))
    with pytest.raises(ValueError, match='refresh'):
        select_screen(profile(display_binding=binding))


@pytest.mark.parametrize('payload', [[], None, 2, {'luminance_calibration': [None]}, {'luminance_calibration': {}}, {'qualified_experiments': 'legacy_contrast_sensitivity'}])
def test_malformed_profile_has_validation_error(payload):
    if isinstance(payload, dict):
        payload = profile().to_dict() | payload
    with pytest.raises(ValueError):
        _profile_from_dict(payload)


def test_bad_local_profile_does_not_break_reference_loading():
    directory = config_root(ROOT) / 'profiles' / 'bad'
    directory.mkdir(parents=True)
    (directory / 'revision_000001.json').write_text('[]', encoding='utf-8')
    with pytest.warns(RuntimeWarning, match='unavailable'):
        assert 'legacy_reference_display' in load_monitor_profiles(ROOT)


def test_off_axis_extent_uses_rendered_pixel_position():
    request = GeometryCheckRequest('legacy_reference_display', 'physical_mm', 100,
                                   test_kind='spatial', x_position=40.1)
    bar, plan = resolve_test(profile(), request, (100, 100))
    left, _, right, _ = plan['rectangle_px']
    expected = math.degrees(math.atan((right-50)*.61/100) - math.atan((left-50)*.61/100))
    assert plan['off_axis_extent_deg'] == pytest.approx(expected, abs=1e-12)
    assert plan['spatial']['cycles_across_patch'] == pytest.approx(expected)


def test_diagnostic_checks_actual_fullscreen_resolution(monkeypatch):
    import psychophysics_lab.core.geometry_check as geometry
    closed = []
    class Window:
        width, height = 1280, 720
        def __init__(self, **kwargs): pass
        def close(self): closed.append(True)
    fake = SimpleNamespace(window=SimpleNamespace(Window=Window), gl=SimpleNamespace(),
                           clock=SimpleNamespace(unschedule=lambda callback: None))
    monkeypatch.setitem(sys.modules, 'pyglet', fake)
    monkeypatch.setattr(geometry, 'select_screen', lambda p: (object(), {}))
    # Only the fullscreen geometry behaviour is under test. Mock the centrally
    # negotiated graphics window; format negotiation has dedicated tests.
    monkeypatch.setattr('psychophysics_lab.core.output_precision.create_output_window',
                        lambda screen, window_factory=None, **kw:
                            ((window_factory or Window)(**kw), {}))
    with pytest.raises(ValueError, match='resolution'):
        geometry._draw_fullscreen(profile(expected_resolution_px=(1920,1080)),
                                  GeometryCheckRequest('legacy_reference_display','physical_mm',100))
    assert closed


def test_profile_detection_preserves_existing_monitor_binding(tmp_path, monkeypatch):
    from textual.widgets import Button, Select
    from psychophysics_lab.ui.profiles import ProfileScreen
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    monitors = [DisplayInfo(0,0,0,1920,1080,60,'A'), DisplayInfo(1,1920,0,1920,1080,60,'B')]
    monkeypatch.setattr('psychophysics_lab.ui.profiles.enumerate_displays', lambda: monitors)
    saved = save_profile(config_root(ROOT), profile(id='local', origin='local', display_binding=asdict(monitors[1]), qualified_experiments=('contrast_sensitivity',)))
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            app.push_screen(ProfileScreen(profile=saved))
            await pilot.pause()
            app.screen.query_one('#profile-detect', Button).press()
            await pilot.pause()
            assert app.screen.query_one('#profile-binding', Select).value == 1
    asyncio.run(scenario())


@pytest.mark.parametrize('values', [None, [], 'invalid', 5])
def test_malformed_workspace_request_is_ignored(values):
    from psychophysics_lab.data.workspace import request_from_workspace_state
    raw = asdict(SetupRequest('S001','new','contrast_sensitivity','legacy_reference_display',{}))
    raw['experiment_values'] = values
    assert request_from_workspace_state({'last_request': raw}) is None


def test_preflight_checks_experiment_identity():
    from psychophysics_lab.config.preflight import validate_setup
    from psychophysics_lab.experiments._internal.registry import get_experiment
    spec = get_experiment('contrast_sensitivity')
    values = spec.field_defaults()
    request = SetupRequest('S001','new','different_experiment','legacy_reference_display',values)
    with pytest.raises(ValueError, match='experiment identity'):
        validate_setup(request, spec, profile())


def test_analysis_rejects_running_run_without_writing(tmp_path):
    from psychophysics_lab.analysis.thresholds import analyse_thresholds
    run = tmp_path/'run'; run.mkdir()
    (run/'manifest.json').write_text(json.dumps({'status':'configured','run_uuid':'test'}))
    (run/'trials.tsv').write_text('stimulus_condition\tstaircase_id\treversal\tnext_display_contrast\n63\t0\t1\t0.5\n')
    with pytest.raises(ValueError, match='final'):
        analyse_thresholds(data_root=tmp_path, run_directory=run, create_plot=False)
    assert not (tmp_path/'analysis').exists()


def test_setup_keeps_compatible_monitor_selection(tmp_path):
    from textual.widgets import Select
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    saved = save_profile(config_root(ROOT), profile(id='local', origin='local', qualified_experiments=('legacy_contrast_sensitivity',)))
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            selector = app.screen.query_one('#monitor-profile', Select)
            selector.value = saved.id
            await pilot.pause()
            app._refresh_experiment_context()
            await pilot.pause()
            assert selector.value == saved.id
    asyncio.run(scenario())


@pytest.mark.parametrize("status", ["aborted_by_user", "error"])
def test_final_run_failure_retains_original_canonical_rows_and_derived_diagnostics(tmp_path,status):
    # Retired event-handler tests depended on an abandoned GL presenter.
    # The supported public contract is the preserved run-owned canonical file.
    from test_pipeline_repairs import saved_run
    from psychophysics_lab.analysis.previews import create_run_figures
    run=saved_run(tmp_path,status=status,kind="human",complete=False)
    before=(run/"trials.tsv").read_bytes()
    report=create_run_figures(data_root=tmp_path,run_directory=run)
    assert (run/"manifest.json").is_file()
    assert (run/"analysis/staircases.png").is_file()
    assert report["status"] in ("partial", "staircases_only")
    assert (run/"trials.tsv").read_bytes()==before


def test_keyboard_interrupt_run_is_not_reported_as_returned(tmp_path, monkeypatch):
    import _legacy_adapter_fixture as example
    import psychophysics_lab.experiments._internal.registry as registry
    from psychophysics_lab.core.runner import run_request
    monkeypatch.setitem(registry._REGISTRY, example.SPEC.id, example.SPEC)
    def interrupt(*args): raise KeyboardInterrupt()
    monkeypatch.setattr(example, 'run_experiment', interrupt)
    with pytest.raises(KeyboardInterrupt):
        run_request(SetupRequest('S001','new',example.SPEC.id,'legacy_reference_display',{'example_level':.5}),
                    repo_root=ROOT, data_root=tmp_path/'data')
    manifest = json.loads(next((tmp_path/'data').rglob('manifest.json')).read_text())
    assert manifest['status'] == 'error'
    assert 'KeyboardInterrupt' in manifest['error']
    assert manifest['accepted_trials'] == 0


def test_display_binding_rejects_missing_device_before_physical_acquisition(monkeypatch):
    # Actual display resolution/binding errors are not overridable calibration
    # declarations. The active renderer must fail closed instead of guessing.
    from psychophysics_lab.core.display import select_screen
    screen=Screen("present")
    mock_display(monkeypatch,[screen],screen)
    binding=asdict(DisplayInfo(0,0,0,1920,1080,60,"missing"))
    with pytest.raises(ValueError,match="missing|screen|display"):
        select_screen(profile(id="local",origin="local",display_binding=binding))


def test_trial_log_rejects_existing_incompatible_header(tmp_path):
    from psychophysics_lab.data.trials import TrialLog
    path = tmp_path/'trials.tsv'
    original = 'legacy\tother\n1\t2\n'
    path.write_text(original)
    with pytest.raises(ValueError, match='header'):
        TrialLog(path)
    assert path.read_text() == original


def test_relative_environment_data_path_is_independent_of_cwd(tmp_path, monkeypatch):
    from psychophysics_lab.paths import default_data_root, resolve_data_root
    monkeypatch.setenv('PSYCOLAB_DATA_DIR', 'relative-data')
    monkeypatch.chdir(tmp_path)
    assert default_data_root(ROOT) == resolve_data_root('relative-data', ROOT)


def test_profile_binding_device_id_must_be_text():
    payload = profile().to_dict() | {'display_binding':asdict(DisplayInfo(0,0,0,1920,1080,60,123))}
    with pytest.raises(ValueError, match='device'):
        _profile_from_dict(payload)


def test_malformed_preset_is_not_offered_to_tui():
    from psychophysics_lab.config.local import load_presets
    directory = config_root(ROOT)/'presets'/'contrast_sensitivity'
    directory.mkdir(parents=True)
    (directory/'bad.json').write_text(json.dumps({'experiment_id':'contrast_sensitivity','values':5}))
    assert load_presets(config_root(ROOT),'contrast_sensitivity') == {}


@pytest.mark.parametrize('device_id,valid', [(r'\\.\DISPLAY1',True), (r'\\.\DISPLAY12',True), (r'\\server\share',False), ('/home/example/data',False)])
def test_validator_distinguishes_windows_monitor_id_from_file_path(tmp_path, device_id, valid):
    from scripts.validate_run import validate_run
    (tmp_path/'manifest.json').write_text(json.dumps({'device_id':device_id}))
    # Provide metadata files needed by this individual check; other checks are intentionally irrelevant here.
    for name in ('experiment_config','monitor_profile','runtime_display','resolved_experiment'):
        (tmp_path/(name+'.json')).write_text('{}')
    result = next(c for c in validate_run(tmp_path) if c.name == 'Portable canonical JSON metadata')
    assert result.passed is valid, result.detail


def test_current_stimulus_parameter_overrides_leave_shared_defaults_unchanged():
    from psychophysics_lab.stimulus_library import ContrastSensitivityGrating
    base={f.key:f.default for f in ContrastSensitivityGrating.PARAMETERS}
    original=dict(base)
    selected=ContrastSensitivityGrating.validate_parameters(base | {
        "spatial_frequency_cpd":6.5, "sigma_deg":1.3
    })
    assert selected["spatial_frequency_cpd"]==6.5
    assert selected["sigma_deg"]==1.3
    assert base==original
    assert ContrastSensitivityGrating.validate_parameters(base)["sigma_deg"]==original["sigma_deg"]


def test_launch_state_nonobject_is_treated_as_missing(tmp_path, monkeypatch):
    from scripts import launcher_setup
    state = tmp_path/'setup.json'; state.write_text('[]')
    monkeypatch.setattr(launcher_setup,'STATE',state)
    assert launcher_setup._load_state() == {}


def test_diagnostic_interrupt_is_recorded(tmp_path, monkeypatch):
    import psychophysics_lab.core.geometry_check as geometry
    def interrupt(*args): raise KeyboardInterrupt()
    monkeypatch.setattr(geometry,'_draw_fullscreen',interrupt)
    with pytest.raises(KeyboardInterrupt):
        geometry.run_geometry_check(GeometryCheckRequest('legacy_reference_display','physical_mm',40),repo_root=ROOT,data_root=tmp_path/'data')
    payload = json.loads(next(config_root(ROOT).rglob('geometry_check.json')).read_text())
    assert payload['status'] == 'error' and 'KeyboardInterrupt' in payload['error']


def test_concurrent_profile_edits_keep_one_revision_and_reject_stale_writer(tmp_path):
    import subprocess
    saved = save_profile(config_root(ROOT), profile(id='race_profile',origin='local'))
    script = "from pathlib import Path; import sys; from psychophysics_lab.config.monitor import load_monitor_profiles; from psychophysics_lab.config.local import config_root,save_profile; from psychophysics_lab.paths import find_repo_root; r=find_repo_root(); p=load_monitor_profiles(r)['race_profile']; from dataclasses import replace; save_profile(config_root(r),replace(p,notes='competing explicit edit'),expected_revision=1)"
    jobs = [subprocess.Popen([sys.executable,'-B','-c',script],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
    results = []
    for job in jobs:
        out, err = job.communicate(timeout=30)
        results.append((job.returncode,err.decode(errors='replace')))
    assert sorted(code for code,_ in results) == [0,1], results
    assert any('Profile changed' in err for _,err in results)
    revisions = sorted((config_root(ROOT)/'profiles'/saved.id).glob('revision_*.json'))
    assert [json.loads(p.read_text())['revision'] for p in revisions] == [1,2]


@pytest.mark.parametrize("field", ["fixation_ms", "grating_ms"])
def test_current_csf_positive_stimulus_phase_duration_is_required(field):
    from psychophysics_lab.experiments.contrast_sensitivity import SPEC, make_trial
    with pytest.raises(ValueError):
        SPEC.normalise_values(SPEC.field_defaults() | {field:0})
    values=SPEC.normalise_values(SPEC.field_defaults() | {field:1})
    trial=make_trial(values,{"target":0}).resolve(values)
    assert trial.phases[-1].name=="answer"
    assert trial.phases[-1].duration_ms==0


def test_loading_workspace_with_removed_experiment_uses_current_selection(tmp_path):
    from textual.widgets import Select
    from psychophysics_lab.data.workspace import save_workspace_state
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    data = tmp_path/'data'
    save_workspace_state(data,SetupRequest('S001','new','removed_experiment','legacy_reference_display',{}),status='returned')
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=data)
        async with app.run_test() as pilot:
            app._refresh_data_root()
            await pilot.pause()
            assert app.screen.query_one('#experiment',Select).value == 'example_experiment'
    asyncio.run(scenario())


def test_tui_rejects_config_data_overlap_before_creating_directory(tmp_path):
    from textual.widgets import Input
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            forbidden = app.local_config_root/'nested-data'
            app.screen.query_one('#data-root',Input).value = str(forbidden)
            with pytest.raises(ValueError,match='separate'):
                app._selected_data_root(create=True)
            assert not forbidden.exists()
    asyncio.run(scenario())
