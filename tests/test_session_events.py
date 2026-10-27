"""Session readiness uses real run ownership, never trial/observer state."""
from dataclasses import replace
import csv
import json
from pathlib import Path

import pytest
from psychophysics_lab.researcher import (ConfigField, Show, WaitForKey, CollectResponse,
    SessionTimeline, TrialTimeline, RecordState, Beep, RunContext, ParticipantAbort)
from psychophysics_lab.core.timeline import as_trial_timeline
from psychophysics_lab.core.trial_execution import VirtualPresentation
from psychophysics_lab.experiments._internal import registry
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def read(a, name):
    return json.loads((a.run_directory / name).read_text(encoding='utf-8'))


def rows(a):
    with a.trial_log_file.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def install_opening(monkeypatch, identity='contrast_sensitivity', *, events=None):
    original = registry.get_experiment(identity)
    opening = events if events is not None else [
        WaitForKey('ready', key='start_key', slot='fixation', instructions='Press the selected start key.'),
        Show('settle', slot='fixation', duration='initial_fixation_ms'),
    ]
    spec = replace(original, fields=original.fields + (
        ConfigField('start_key', 'Readiness key', 'text', 'SPACE'),
        ConfigField('initial_fixation_ms', 'Initial settling fixation', 'int', 37, minimum=1, units='ms'),
    ), session_start=opening)
    monkeypatch.setitem(registry._REGISTRY, identity, spec)
    return spec


def run(tmp_path, identity='contrast_sensitivity', method='adaptive', **extra):
    values = dict(frequencies_cpd='2', positions_deg='0', aspect_ratios='1', ring_increment=.03,
                  contrast_method=method, max_trials=8, staircases_per_condition=1,
                  threshold_reversals=2, reversal_termination=2, fixed_contrasts='0,.01', fixed_repetitions=2)
    fields = registry.get_experiment(identity).field_defaults()
    return simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=identity, seed=53, analyse=False,
                    observer=TeachingObserver(accuracy=.65), values={k:v for k,v in values.items() if k in fields} | extra)[0]


@pytest.mark.parametrize('identity', ['contrast_sensitivity', 'ellipse_major_axis'])
@pytest.mark.parametrize('method', ['adaptive', 'constant_stimuli'])
def test_opening_once_and_complete_trial_adaptation_and_estimation_equivalence(tmp_path, monkeypatch, identity, method):
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kwargs: None)
    old = run(tmp_path, identity, method)
    install_opening(monkeypatch, identity)
    new = run(tmp_path, identity, method, start_key='ENTER', initial_fixation_ms=73)
    assert rows(new) == rows(old)  # includes first/last condition, contrast, keys, steps, reversals, status
    assert read(new, 'trial_actions.json') == read(old, 'trial_actions.json')
    for name in ('adaptive_history.json', 'primary_thresholds.json', 'adaptive_session.json'):
        if (old.run_directory/name).exists():
            assert read(new, name) == read(old, name)
    trace = read(new, 'session_events.json')
    assert trace['status'] == 'completed'
    assert [e['name'] for e in trace['events']] == ['ready', 'settle']
    assert trace['events'][0]['readiness']['key'] == 'ENTER'
    assert trace['events'][0]['readiness']['elapsed_s'] == 0
    assert trace['events'][1]['virtual_offset_ms'] == 73
    assert all('response' not in e for e in trace['events'])
    assert all('software_started_s' in e and 'software_finished_s' in e for e in trace['events'])
    assert read(new, 'manifest.json')['files']['session_events'] == 'session_events.json'
    failures = [(c.name,c.detail) for c in validate_run(new.run_directory) if not c.passed]
    assert not failures, failures


@pytest.mark.parametrize('identity', ['contrast_sensitivity', 'ellipse_major_axis'])
def test_completed_reversal_threshold_and_initial_one_down_are_preserved(tmp_path, monkeypatch, identity):
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kwargs: None)
    chosen = dict(max_trials=128, n_down=1, n_up=1, initial_one_down_limit=2,
                  reversal_termination=4, threshold_reversals=2)
    old = run(tmp_path, identity, **chosen)
    install_opening(monkeypatch, identity)
    new = run(tmp_path, identity, **chosen)
    assert old.status == new.status == 'completed'
    assert rows(old) == rows(new)
    assert read(old, 'adaptive_history.json') == read(new, 'adaptive_history.json')
    assert read(old, 'primary_thresholds.json') == read(new, 'primary_thresholds.json')
    assert rows(new)[-1]['run_status'] == 'completed'


def test_flat_composition_runs_through_canonical_trial_recording(tmp_path, monkeypatch):
    from psychophysics_lab.experiments import contrast_sensitivity as module
    original = module.trial_events
    calls = []
    # The same scientifically declared events, now returned as a composable list.
    def flat_events(*args):
        calls.append(True)
        return list(original(*args))
    monkeypatch.setattr(module, 'trial_events', flat_events)
    artifact = run(tmp_path)
    assert artifact.accepted_trials > 0
    assert len(calls) == artifact.accepted_trials
    assert all(c.passed for c in validate_run(artifact.run_directory))


@pytest.mark.parametrize('events', [
    [CollectResponse(actions=('left','right'))], [RecordState('state')],
    [[Show('nested', duration=1)]], [lambda: None],
    [Show('same', duration=1), WaitForKey('same', key='SPACE')],
])
def test_invalid_session_declarations_rejected(events):
    with pytest.raises((ValueError, TypeError)):
        SessionTimeline(events)


@pytest.mark.parametrize('key', ['ESCAPE', 'escape', '', 'F999', 'not a field', 1, None])
def test_invalid_readiness_declarations_rejected(key):
    with pytest.raises((ValueError, TypeError)):
        WaitForKey('ready', key=key)


@pytest.mark.parametrize('key', ['SPACE', 'ENTER', 'LEFT', '1', 'A'])
def test_supported_literal_keys(key):
    assert SessionTimeline([WaitForKey('ready', key=key)]).resolve({}).phases[0].key == key


def test_field_resolution_slot_checks_and_trial_composition():
    opening = SessionTimeline([WaitForKey('ready', key='start_key', slot='fixation')])
    with pytest.raises(ValueError, match='Unknown readiness'):
        opening.resolve({})
    with pytest.raises(ValueError, match='reserved'):
        opening.resolve({'start_key':'ESCAPE'})
    with pytest.raises(ValueError, match='undeclared'):
        opening.validate_slots({'target'})
    with pytest.raises(ValueError, match='SessionTimeline'):
        TrialTimeline([WaitForKey('ready', key='SPACE'), CollectResponse(actions=('left','right'))])
    sequence = [Show('fixation', duration=12)] + [CollectResponse(actions=('left','right'))]
    assert as_trial_timeline(sequence).to_dict() == TrialTimeline(sequence).to_dict()
    for invalid in (opening, [sequence], (e for e in sequence)):
        with pytest.raises((ValueError,TypeError)):
            as_trial_timeline(invalid)
    assert SessionTimeline([]).to_dict()['phases'] == []


def test_existing_trial_subclass_can_keep_its_required_constructor_argument():
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class LaboratoryTimeline(TrialTimeline):
        laboratory_note: str
    sequence = LaboratoryTimeline((Show('fixation', duration='fixation_ms'),
                                   CollectResponse(actions=('left','right'))), 'retained local extension')
    resolved = sequence.resolve({'fixation_ms':12})
    assert type(resolved) is TrialTimeline and resolved.phases[0].duration_ms == 12


@pytest.mark.parametrize('failure', ['abort', 'prepare', 'device', 'bad_readiness'])
def test_pre_first_trial_failures_preserve_partial_session_and_cleanup(tmp_path, monkeypatch, failure):
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kwargs: None)
    install_opening(monkeypatch)
    original = VirtualPresentation.play_phase
    def interrupted(self, phase, event, **kw):
        if phase.kind == 'key_wait':
            if failure == 'abort':
                raise ParticipantAbort('Escape at readiness')
            if failure == 'bad_readiness':
                event['readiness'] = {'key':'RIGHT', 'elapsed_s':0}
                return None
        return original(self, phase, event, **kw)
    monkeypatch.setattr(VirtualPresentation, 'play_phase', interrupted)
    if failure == 'prepare':
        monkeypatch.setattr(VirtualPresentation, 'prepare', lambda *a: (_ for _ in ()).throw(OSError('output preparation failed')))
    if failure == 'device':
        original_init = RunContext._initialise
        def no_device(self, **kw):
            if self.spec.session_start.phases:
                raise OSError('output device missing')
            return original_init(self, **kw)
        monkeypatch.setattr(RunContext, '_initialise', no_device)
    closed = []
    close = RunContext.close
    def observe_close(self):
        closed.append(self)
        return close(self)
    monkeypatch.setattr(RunContext, 'close', observe_close)
    if failure == 'abort':
        result = run(tmp_path)
        assert result.status == 'aborted_by_user'
    else:
        with pytest.raises((OSError,ValueError)):
            run(tmp_path)
    manifest_path = next(tmp_path.rglob('manifest.json'))
    manifest = json.loads(manifest_path.read_text())
    trace = json.loads((manifest_path.parent/'session_events.json').read_text())
    assert manifest['accepted_trials'] == 0
    assert manifest['status'] == ('aborted_by_user' if failure=='abort' else 'error')
    assert trace['status'] == ('aborted' if failure=='abort' else 'error')
    assert len(trace['events']) == (1 if failure in {'abort','bad_readiness'} else 0)
    assert closed and closed[0].accepted_trials == 0
    checks = validate_run(manifest_path.parent)
    failures = [(c.name,c.detail) for c in checks if not c.passed]
    if failure == 'device':
        # No display was opened and no resolved experiment could be produced.
        # Retain this diagnostic; never fabricate successful runtime evidence.
        assert any('missing files' in detail for _, detail in failures)
        assert next(c for c in checks if c.name.startswith('Once-only session')).passed
    else:
        assert not failures, failures


def test_twice_only_guard_and_no_scientific_answer_or_rng(tmp_path, monkeypatch):
    spec = install_opening(monkeypatch)
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from types import SimpleNamespace
    values = spec.normalise_values({})
    context = RunContext(values, SimpleNamespace(id='virtual'), spec, tmp_path, synthetic=True,
                         data_kind='synthetic', stimulus_snapshots=resolve_stimuli(spec, values, repo_root=ROOT))
    context.initialise(expected_trials=2, resolution={'task':'session-only software check'})
    assert context.accepted_trials == 0 and not hasattr(context, '_rng')
    before = (tmp_path/'session_events.json').read_bytes()
    with pytest.raises(ValueError, match='once'):
        context.initialise(expected_trials=2, resolution={'task':'again'})
    assert (tmp_path/'session_events.json').read_bytes() == before
    assert not (tmp_path/'trials.tsv').exists()
    context.close()


def test_virtual_beep_requests_and_ready_policy_are_independent_of_response():
    from psychophysics_lab.core.trial_execution import execute_timeline
    sequence = SessionTimeline([Show('start', duration=20, beep=Beep()),
                                WaitForKey('ready', key='SPACE', beep=Beep())])
    events = []
    result = execute_timeline(sequence, VirtualPresentation(), events, lambda *a: None)
    assert result is None
    assert [e['audio']['trigger'] for e in events] == ['display_onset', 'accepted_readiness']
    assert events[1]['virtual_onset_ms'] == events[1]['virtual_offset_ms'] == 20


@pytest.mark.parametrize('corruption', ['key', 'response', 'duplicate', 'timestamps'])
def test_session_validator_rejects_resealed_semantic_tampering(tmp_path, monkeypatch, corruption):
    import hashlib
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kwargs: None)
    install_opening(monkeypatch)
    a = run(tmp_path)
    path = a.run_directory/'session_events.json'
    trace = read(a, path.name)
    if corruption == 'key':
        trace['events'][0]['readiness']['key'] = 'RIGHT'
    elif corruption == 'response':
        trace['events'][0]['response'] = {'alternative': 0}
    elif corruption == 'duplicate':
        trace['events'].extend(trace['events'])
    else:
        trace['events'][0]['software_started_s'] = trace['software_started_s'] - 1
    path.write_text(json.dumps(trace), encoding='utf-8')
    manifest = read(a, 'manifest.json')
    manifest['output_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (a.run_directory/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    check = next(c for c in validate_run(a.run_directory) if c.name.startswith('Once-only session'))
    assert not check.passed


def test_invalid_selected_readiness_fails_before_backend_or_trial(tmp_path, monkeypatch):
    install_opening(monkeypatch)
    opened = []
    monkeypatch.setattr(VirtualPresentation, 'prepare', lambda *a: opened.append(True))
    with pytest.raises(ValueError, match='reserved'):
        run(tmp_path, start_key='ESCAPE')
    assert not opened and not list(tmp_path.rglob('manifest.json'))


def test_opt_in_session_rows_route_to_existing_configure_editors(tmp_path, monkeypatch):
    import asyncio
    from textual.widgets import Button, Input
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen
    spec = install_opening(monkeypatch)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(120, 45)) as pilot:
            screen = ExperimentConfigScreen(data_root=app.data_root, participant_id='EVENT_API',
                session_mode='new', experiment=spec, monitor_profile_id='legacy_reference_display',
                defaults=spec.normalise_values({}))
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one('#review', Button).press()
            await pilot.pause()
            review = app.screen
            assert isinstance(review, ReviewScreen), str(screen.query_one('#config-status').renderable)
            row = next(i for i,r in enumerate(review._review_rows) if r[:2] == ('Session start (once)', 'ready key'))
            assert review._row_authorities[row]['field'] == 'start_key'
            review._edit_review_parameter(row)
            await pilot.pause()
            config = app.screen
            widget = config.query_one('#field-start-key', Input)
            assert widget.has_focus
            widget.value = 'ENTER'
            config.query_one('#review', Button).press()
            await pilot.pause()
            assert app.screen is review and review._review_rows[row][2] == 'ENTER'
            timing = next(i for i,r in enumerate(review._review_rows) if r[:2] == ('Session start (once)', 'settle duration'))
            assert review._row_authorities[timing]['field'] == 'initial_fixation_ms'
            assert any(r[0] == 'Trial' for r in review._review_rows)
    asyncio.run(scenario())


@pytest.mark.parametrize('identity', ['contrast_sensitivity', 'ellipse_major_axis'])
@pytest.mark.parametrize('method', ['adaptive', 'constant_stimuli'])
def test_existing_bounded_presentation_test_path_also_runs_opening_once(tmp_path, monkeypatch, identity, method):
    # Reuse the established test's real presentation-test boundary, isolated
    # display profile, injected software window and human-folder sentinel.
    from test_researcher_test_workflow import test_real_presentation_mode_isolated_and_bounded_without_qualifying_acquisition
    spec = install_opening(monkeypatch, identity)
    spec = replace(spec, default_config='', fields=tuple(
        replace(f, default=method) if f.key == 'contrast_method' else f for f in spec.fields))
    monkeypatch.setitem(registry._REGISTRY, identity, spec)
    from psychophysics_lab.config.local import config_root
    output = config_root(ROOT).parent/'psycolab_presentation_tests'
    before = set(output.rglob('session_events.json'))
    test_real_presentation_mode_isolated_and_bounded_without_qualifying_acquisition(tmp_path, monkeypatch, identity)
    traces = list(set(output.rglob('session_events.json')) - before)
    assert len(traces) == 1
    trace = json.loads(traces[0].read_text())
    assert trace['status'] == 'completed' and [e['name'] for e in trace['events']] == ['ready', 'settle']
    assert trace['data_kind'] == 'uncalibrated_presentation_test' and not trace['synthetic']
    manifest = json.loads((traces[0].parent/'manifest.json').read_text())
    assert manifest['accepted_trials'] == 2 and manifest['status'] == 'test_finished'
