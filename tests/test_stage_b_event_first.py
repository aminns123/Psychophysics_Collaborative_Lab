"""Stage B equivalence against latest merged main, including the real phase player."""
import ast
import csv
import hashlib
import importlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
from psychophysics_lab.researcher import RunContext, TrialTimeline, ParticipantAbort
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT/'tests/fixtures/stage_b_baseline_20261027.json').read_text())
MIGRATED = ('contrast_sensitivity', 'ellipse_major_axis')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def frozen_csf_validation_spelling(node):
    """Keep the frozen AST strict except #140's exact error-text correction."""
    for item in ast.walk(node):
        if (isinstance(item, ast.Constant) and item.value ==
                "Choose distinct finite spatial frequencies within 0.5-32 cycles/degree."):
            item.value = "Choose distinct finite spatial frequencies within 0.5â€“32 cycles/degree."
    return node


def read(directory, name):
    return json.loads((directory/name).read_text(encoding='utf-8'))


def rows(directory):
    with (directory/'trials.tsv').open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def select_opening(monkeypatch, identity, enabled):
    registry.get_experiment(identity)  # finish normal discovery before replacing a test spec
    module = importlib.import_module('psychophysics_lab.experiments.' + identity)
    if not enabled:
        monkeypatch.setattr(module, 'SESSION_START', [])
    spec = module.definition()
    monkeypatch.setattr(module, 'SPEC', spec)
    monkeypatch.setitem(registry._REGISTRY, identity, spec)
    return module, spec


@pytest.mark.parametrize('enabled', [False, True], ids=['empty-opening', 'approved-opening'])
@pytest.mark.parametrize('case', BASELINE['cases'], ids=lambda c:f"{c['identity']}-{c['method']}-{c['seed']}")
def test_complete_scientific_outputs_match_latest_main_in_both_opening_cases(tmp_path, monkeypatch, case, enabled):
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kw: None)
    _, spec = select_opening(monkeypatch, case['identity'], enabled)
    a,_ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=spec.id, values=case['values'],
                   seed=case['seed'], analyse=False, observer=TeachingObserver(accuracy=.65))
    assert (a.status, a.accepted_trials) == (case['status'], case['accepted'])
    assert digest(rows(a.run_directory)) == case['rows_sha256']
    for name, expected in case['files_sha256'].items():
        assert digest(read(a.run_directory, name)) == expected, name
    if enabled:
        session = read(a.run_directory, 'session_events.json')
        assert session['status'] == 'completed'
        assert [(p['kind'], p['duration_ms']) for p in session['plan']['phases']] == [('key_wait',0),('show',1000)]
        assert [e['name'] for e in session['events']] == ['ready','settle']
        assert session['events'][0]['readiness']['key'] == 'SPACE'
        assert session['events'][0]['readiness']['elapsed_s'] == 0
        assert session['events'][1]['virtual_offset_ms'] == 1000
        assert not any('response' in e for e in session['events'])
    else:
        assert not (a.run_directory/'session_events.json').exists()
    failures = [(c.name,c.detail) for c in validate_run(a.run_directory) if not c.passed]
    assert not failures, failures


@pytest.mark.parametrize('identity', MIGRATED)
def test_scientific_function_bodies_are_unchanged_and_trial_definition_is_unique(identity):
    module = importlib.import_module('psychophysics_lab.experiments.'+identity)
    source = Path(module.__file__).read_text(encoding='utf-8')
    functions = {n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    for name, expected in BASELINE['functions'][identity].items():
        if name not in {'make_trial','procedure','definition'}:
            node = functions[name]
            if identity == 'contrast_sensitivity' and name == 'validate_settings':
                node = frozen_csf_validation_spelling(node)
            assert digest(ast.dump(node, include_attributes=False)) == expected, name
    assert 'trial_events' in functions and 'make_trial' not in functions
    assert module.make_trial.__wrapped__ is module.trial_events
    values = module.SPEC.normalise_values({'ring_increment':.03} if identity=='ellipse_major_axis' else {})
    assert isinstance(module.trial_events(values, {'target':0}), list)
    assert isinstance(module.make_trial(values, {'target':0}), TrialTimeline)
    assert module.make_trial(values, {'target':0}).phases == tuple(module.trial_events(values, {'target':0}))


@pytest.mark.parametrize('identity', MIGRATED)
@pytest.mark.parametrize('background', [.2,.8])
def test_session_only_fixation_has_no_probe_and_tracks_selected_background(identity, background):
    spec = registry.get_experiment(identity)
    values = spec.normalise_values({'background_intensity':background} | (
        {'ring_increment':.03,'starting_probe_intensity':background+.01} if identity=='ellipse_major_axis' else {}))
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    assert {p.slot for p in spec.session_start.phases} == {'ready_fixation'}
    document = snapshots['ready_fixation']['document']
    assert document['stimulus_id'] == 'gaussian_fixation'
    assert document['parameters']['background'] == background
    assert 'probe_present' not in document['parameters']
    if identity=='ellipse_major_axis':
        assert {s:spec.stimulus_slots[s] for s in ('fixation','first','second')} == dict.fromkeys(('fixation','first','second'),'detection_scene')


def test_all_official_openings_use_the_approved_stage_c_start():
    # Other compatibility tests register standalone protocols too; the frozen
    # inventory identifies the official ten, independent of test registry order.
    saved = json.loads((ROOT/'tests/fixtures/stage_c_baseline_20261027.json').read_text())
    identities = [item['id'] for item in saved['inventory']]
    assert len(identities) == 10
    for identity in identities:
        spec = registry.get_experiment(identity)
        assert [(p.kind,p.duration_ms) for p in spec.session_start.phases] == [('key_wait',0),('show',1000)]
        assert spec.session_start.phases[0].key == 'SPACE'
        assert 'ready_fixation' in spec.stimulus_slots, spec.id


def software_window(monkeypatch, *, escape=False):
    from test_action_presentation import fake_presentation
    display, _, handlers = fake_presentation(monkeypatch)
    clock = {'now':0.}
    monkeypatch.setattr('psychophysics_lab.core.presentation.time.perf_counter', lambda:clock['now'])
    def dispatch():
        clock['now'] += .01
        # Distinct release/press cycles; held-readiness filtering is separately
        # covered by the accepted Stage A software-window regression.
        display.held.clear()
        event = getattr(display, '_last_visual_event', {})
        if event.get('kind') in {'key_wait','response'}:
            key = ('ESCAPE' if escape else event['key']) if event['kind']=='key_wait' else display.responses.keys[0]
            handlers['on_key_press'](key,0)
    display.window.dispatch_events = dispatch
    display.window.close = lambda:None
    display.metadata = {'physical_display_used':True, 'test_fixture':True, 'photon_timing_verified':False}
    def factory(profile, responses, **kwargs):
        display.profile, display.responses = profile, responses
        return display
    monkeypatch.setattr('psychophysics_lab.core.presentation.Presentation', factory)
    monkeypatch.setattr('psychophysics_lab.core.tone.request_beep', lambda beep,trigger: {'trigger':trigger, 'output':'injected audio command only'})
    return display


@pytest.mark.parametrize('identity', MIGRATED)
@pytest.mark.parametrize('method', ['adaptive','constant_stimuli'])
def test_actual_phase_player_preserves_first_last_trial_and_scientific_state(tmp_path, monkeypatch, identity, method):
    from psychophysics_lab.config.monitor import load_monitor_profiles
    scientific = []
    states = []
    opening = None
    for enabled in (False, True):
        with monkeypatch.context() as patch:
            module = importlib.import_module('psychophysics_lab.experiments.'+identity)
            spec = module.SPEC if enabled else replace(module.SPEC, session_start=[])
            display = software_window(patch)
            profile = replace(load_monitor_profiles(ROOT)['legacy_reference_display'], expected_resolution_px=display.resolution)
            values = dict(contrast_method=method,max_trials=8,frequencies_cpd='2',positions_deg='0',aspect_ratios='1',
                          ring_increment=.03,ring_conditions='base_only',staircases_per_condition=1,
                          fixed_contrasts='0,.01',fixed_repetitions=2,fixation_ms=1,grating_ms=1,stimulus_ms=1,isi_ms=1)
            values = spec.normalise_values({k:v for k,v in values.items() if k in spec.field_defaults()})
            directory = tmp_path/str(enabled)
            directory.mkdir()
            context = RunContext(values, profile, spec, directory, seed=53, data_kind='uncalibrated_presentation_test',
                                 stimulus_snapshots=resolve_stimuli(spec, values, repo_root=ROOT))
            try:
                spec.procedure(context)
            finally:
                context.close()
            assert context.accepted_trials == (8 if method=='adaptive' else 4)
            scientific.append([{k:v for k,v in row.items() if k not in {'recorded_utc','event_time_s'}} for row in rows(directory)])
            states.append({
                'trials': [{key:trial[key] for key in ('trial_index','condition','target','plan',
                    'resolved_stimuli','initial_state','final_state','status')}
                    for trial in read(directory,'trial_actions.json')['trials']],
                'adaptive': read(directory,'adaptive_history.json') if (directory/'adaptive_history.json').exists() else None,
                'primary': read(directory,'primary_thresholds.json') if (directory/'primary_thresholds.json').exists() else None,
            })
            if enabled:
                opening = read(directory,'session_events.json')
                assert opening['status']=='completed' and len(opening['events'])==2
                assert opening['events'][0]['readiness']['key']=='SPACE'
            else:
                assert not (directory/'session_events.json').exists()
    assert scientific[0] == scientific[1]
    assert states[0] == states[1]
    assert not any('response' in e for e in opening['events'])


@pytest.mark.parametrize('identity', MIGRATED)
def test_escape_in_actual_readiness_player_aborts_zero_trial_manifest(tmp_path, monkeypatch, identity):
    from psychophysics_lab.config.local import config_root, save_profile
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.config.models import SetupRequest
    from psychophysics_lab.core.presentation_testing import PresentationTestRequest, run_presentation_test
    monkeypatch.setattr('psychophysics_lab.core.display.preflight_fullscreen_display', lambda p:None)
    display = software_window(monkeypatch, escape=True)
    reference = load_monitor_profiles(ROOT)['legacy_reference_display']
    profile = save_profile(config_root(ROOT), replace(reference,id='stage_b_display',origin='local',
        expected_resolution_px=display.resolution,display_binding={'index':0,'x':0,'y':0,'width':1000,'height':600}))
    spec = registry.get_experiment(identity)
    values = spec.normalise_values({'ring_increment':.03} if identity=='ellipse_major_axis' else {})
    result = run_presentation_test(PresentationTestRequest(SetupRequest('TEST','new',identity,profile.id,values),trial_limit=2),repo_root=ROOT)
    assert result.status=='aborted_by_user' and result.accepted_trials==0
    assert not rows(result.run_directory)
    assert read(result.run_directory,'session_events.json')['status']=='aborted'
    assert all(c.passed for c in validate_run(result.run_directory))


@pytest.mark.parametrize('identity', MIGRATED)
@pytest.mark.parametrize('legacy', ['absent','conflicting'])
def test_review_and_acquisition_read_the_same_python_event_function(tmp_path, monkeypatch, identity, legacy):
    from psychophysics_lab.ui.settings_review import describe_settings
    module = importlib.import_module('psychophysics_lab.experiments.'+identity)
    original = module.trial_events
    calls = []
    def authored(settings,condition):
        calls.append(condition['target'])
        events = original(settings,condition)
        return [replace(events[0],duration_ms=17)] + events[1:]
    monkeypatch.setattr(module,'trial_events',authored)
    # A conflicting legacy hook proves Review/acquisition are not describing
    # or executing an independent old procedure.
    if legacy == 'absent':
        monkeypatch.delattr(module,'make_trial')
    else:
        monkeypatch.setattr(module,'make_trial',lambda *a: (_ for _ in ()).throw(AssertionError('legacy event hook used')))
    values = module.SPEC.normalise_values({'max_trials':2} | ({'ring_increment':.03} if identity=='ellipse_major_axis' else {}))
    description = describe_settings(module.SPEC,values,resolve_stimuli(module.SPEC,values,repo_root=ROOT))
    assert description['trial_event_function']=='trial_events' and description['phases'][0]['duration_ms']==17
    a,_ = simulate(repo_root=ROOT,data_root=tmp_path,experiment_id=identity,values=values,analyse=False)
    traces = read(a.run_directory,'trial_actions.json')['trials']
    assert all(t['plan']['phases'][0]['duration_ms']==17 for t in traces)
    assert len(calls)==1+a.accepted_trials


def test_ambiguous_trial_factories_fail_before_method_or_scientific_state_creation():
    from types import SimpleNamespace
    from psychophysics_lab.methods.contrast import run_contrast_experiment
    created = []
    with pytest.raises(ValueError, match='not both'):
        run_contrast_experiment(SimpleNamespace(values={}),
            methods={'adaptive':lambda:created.append(True)}, prepare_stimuli=lambda *a:None,
            interpret_response=lambda *a:None, trial_events=lambda *a:[], make_trial=lambda *a:[])
    assert not created


@pytest.mark.parametrize('identity', MIGRATED)
def test_generic_configure_edit_preserves_bound_background_and_selected_appearance(tmp_path, monkeypatch, identity):
    import asyncio
    from textual.widgets import Button, Input
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen
    spec = registry.get_experiment(identity)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(120,50)) as pilot:
            config = ExperimentConfigScreen(data_root=app.data_root,participant_id='STAGE_B_UI',session_mode='new',
                experiment=spec,monitor_profile_id='legacy_reference_display',
                defaults=spec.normalise_values({'ring_increment':.03} if identity=='ellipse_major_axis' else {}))
            app.push_screen(config)
            await pilot.pause()
            config.query_one('#review',Button).press()
            await pilot.pause()
            review = app.screen
            assert isinstance(review,ReviewScreen)
            before = dict(review.request.stimulus_snapshots['ready_fixation']['document']['parameters'])
            row = next(i for i,a in enumerate(review._row_authorities) if a['field']=='background_intensity')
            review._edit_review_parameter(row)
            await pilot.pause()
            app.screen.query_one('#field-background-intensity',Input).value='.2'
            app.screen.query_one('#review',Button).press()
            await pilot.pause()
            assert app.screen is review
            after = review.request.stimulus_snapshots['ready_fixation']['document']['parameters']
            assert after == before | {'background':.2}
            assert review.request.experiment_values['background_intensity']==.2
    asyncio.run(scenario())
