"""Frozen develop source versus migrated callbacks through the SAME real runner."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import types

import pytest
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.data.reader import load_run
from psychophysics_lab.researcher import TrialTimeline
from scripts.validate_run import validate_run
from simulations.run import simulate
from simulations.registry import TeachingObserver

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/issue165_wave2'
NAMES = ('orientation_task', 'orientation_adaptive')


def frozen(name):
    # Baseline captures use LF hashes; Git may check the same Python source out
    # as CRLF on Windows. Normalize only line endings, never scientific content.
    raw = (FIXTURES / (name + '.py')).read_bytes().replace(b'\r\n', b'\n')
    manifest = json.loads((FIXTURES / 'baseline.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == manifest['source_sha256'][name]
    # Keep the public callback module identity: only source layout is migrating.
    module = types.ModuleType('psychophysics_lab.experiments.' + name)
    module.__file__ = str(ROOT / 'src/psychophysics_lab/experiments' / (name + '.py'))
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


@pytest.mark.parametrize('name,method', [
    ('orientation_task', 'original'), ('orientation_task', 'adaptive'),
    ('orientation_task', 'constant_stimuli'), ('orientation_adaptive', 'adaptive'),
    ('orientation_adaptive', 'constant_stimuli')])
@pytest.mark.parametrize('seed,accuracy,opening', [(0, 0., False), (19, .65, True), (137, 1., True)])
def test_real_saved_science_matches_frozen_develop(tmp_path, monkeypatch, name, method, seed, accuracy, opening):
    registry.list_experiments()
    current = registry.get_experiment(name)
    original = frozen(name).SPEC
    assert current.fields == original.fields
    assert current.response_paradigm == original.response_paradigm
    assert current.calibration_requirements == original.calibration_requirements
    assert current.monitor_capabilities == original.monitor_capabilities
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kw: None)
    runs = []
    for spec in (original, current, current):
        if not opening:
            spec = replace(spec, session_start=[])
        monkeypatch.setitem(registry._REGISTRY, name, spec)
        values = dict(contrast_method=method, trial_count=7, fixed_contrasts='0,.1,1',
                      fixed_repetitions=3, max_trials=30, fixation_ms=37, stimulus_ms=51, interval_ms=23)
        run, _ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=name,
            values=values, seed=seed,
            observer=TeachingObserver(accuracy), analyse=False)
        runs.append(run)
        assert all(c.passed for c in validate_run(run.run_directory))
        assert len(load_run(run.run_directory)['trials']) == 20
        assert (run.run_directory / 'session_events.json').exists() == opening
    old, new, repeat = runs
    assert (old.status, old.accepted_trials) == (new.status, new.accepted_trials) == (repeat.status, repeat.accepted_trials)
    assert old.trial_log_file.read_bytes() == new.trial_log_file.read_bytes() == repeat.trial_log_file.read_bytes()
    for filename in ('trial_actions.json', 'adaptive_history.json', 'adaptive_session.json', 'primary_thresholds.json', 'resolved_experiment.json'):
        paths = [r.run_directory / filename for r in runs]
        assert len({p.exists() for p in paths}) == 1
        if paths[0].exists():
            assert json.loads(paths[0].read_text()) == json.loads(paths[1].read_text()) == json.loads(paths[2].read_text())
    # Journal observations include effective stimuli, requested measurements and state.
    journals = [[json.loads(line) for line in (r.run_directory/'trial_events.jsonl').read_text().splitlines()] for r in runs]
    assert journals[0] == journals[1] == journals[2]


@pytest.mark.parametrize('name,method', [
    ('orientation_task', 'original'), ('orientation_task', 'adaptive'),
    ('orientation_task', 'constant_stimuli'), ('orientation_adaptive', 'adaptive'),
    ('orientation_adaptive', 'constant_stimuli')])
@pytest.mark.parametrize('failure', ['ready_abort', 'trial_abort', 'timeout'])
def test_incomplete_runs_preserve_identical_observations(tmp_path, monkeypatch, name, method, failure):
    from psychophysics_lab.core.trial_execution import VirtualPresentation
    from psychophysics_lab.researcher import ParticipantAbort
    original_play = VirtualPresentation.play_phase
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures', lambda **kw: None)
    current = registry.get_experiment(name)
    runs = []
    for spec in (frozen(name).SPEC, current):
        seen = [0]
        def play(self, phase, event, **kw):
            if phase.kind == 'key_wait' and failure == 'ready_abort':
                raise ParticipantAbort('Wave 2 readiness abort')
            if phase.kind == 'response':
                seen[0] += 1
                if failure == 'trial_abort' and seen[0] == 3:
                    raise ParticipantAbort('Wave 2 third response abort')
            return original_play(self, phase, event, **kw)
        monkeypatch.setattr(VirtualPresentation, 'play_phase', play)
        monkeypatch.setitem(registry._REGISTRY, name, spec)
        destination = tmp_path / str(len(runs))
        try:
            run, _ = simulate(repo_root=ROOT, data_root=destination, experiment_id=name, seed=19,
                values=dict(contrast_method=method, trial_count=5, fixed_contrasts='0,.1',
                            fixed_repetitions=3, response_timeout_ms=1 if failure=='timeout' else 0),
                observer=TeachingObserver(.65), analyse=False)
        except TimeoutError:
            assert failure == 'timeout'
            manifest = next(destination.rglob('manifest.json'))
            assert json.loads(manifest.read_text())['status'] == 'error'
            run = types.SimpleNamespace(status='error', accepted_trials=0,
                run_directory=manifest.parent, trial_log_file=manifest.parent/'trials.tsv')
        runs.append(run)
    old, new = runs
    assert (old.status, old.accepted_trials) == (new.status, new.accepted_trials)
    assert old.accepted_trials == (2 if failure == 'trial_abort' else 0)
    assert old.trial_log_file.read_bytes() == new.trial_log_file.read_bytes()
    for filename in ('trial_actions.json', 'adaptive_history.json', 'adaptive_session.json', 'trial_events.jsonl'):
        paths = [r.run_directory / filename for r in runs]
        assert paths[0].exists() == paths[1].exists()
        if paths[0].exists(): assert paths[0].read_bytes() == paths[1].read_bytes()


@pytest.mark.parametrize('name', NAMES)
def test_seeded_plans_events_and_invalid_bounds_match(name):
    import importlib
    old, new = frozen(name), importlib.import_module('psychophysics_lab.experiments.' + name)
    for count in (1, 6, 7):
        for seed in (0, 1, 123):
            values = new.SPEC.normalise_values(dict(trial_count=count, random_seed=seed))
            assert old.make_conditions(values) == new.make_conditions(values)
            assert old.make_fixed_schedule(values, seed) == new.make_fixed_schedule(values, seed)
    for condition in ({'target':0,'orientation_deg':-15.}, {'target':1,'orientation_deg':15.}):
        assert TrialTimeline(old.trial_events(values, condition)).resolve(values).to_dict() == TrialTimeline(new.trial_events(values, condition)).resolve(values).to_dict()
    for overrides in ({'trial_count':0}, {'fixation_ms':0}, {'contrast_method':'adaptive','trial_count':31,'max_trials':30}, {'contrast_method':'constant_stimuli','fixed_contrasts':'nan'}):
        for spec in (old.SPEC, new.SPEC):
            with pytest.raises(ValueError): spec.normalise_values(overrides)


@pytest.mark.parametrize('contrast', [0., 5e-324, 1e-200, .1, 1.])
def test_original_adaptive_bounds_and_representable_floor_are_identical(contrast):
    from psychophysics_lab.experiments import orientation_adaptive as current
    from psychophysics_lab.researcher import Step
    old = frozen('orientation_adaptive')
    state = {'contrast': contrast, 'down_factor': .8, 'up_factor': 1.25}
    for step in (Step.DOWN, Step.HOLD, Step.UP):
        assert old.next_contrast(state, {}, step) == current.next_contrast(state, {}, step)


@pytest.mark.parametrize('name,method', [
    ('orientation_task','original'), ('orientation_task','adaptive'),
    ('orientation_task','constant_stimuli'), ('orientation_adaptive','adaptive'),
    ('orientation_adaptive','constant_stimuli')])
def test_review_scientific_plan_matches_reference(tmp_path, monkeypatch, name, method):
    import sys
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from psychophysics_lab.ui.settings_review import describe_settings
    current_module = sys.modules['psychophysics_lab.experiments.'+name]
    old = frozen(name)
    values = current_module.SPEC.normalise_values({'contrast_method': method, 'trial_count': 7,
        'random_seed': 137, 'fixed_contrasts':'0,.1,1','fixed_repetitions':3})
    descriptions = []
    for module in (old, current_module):
        with monkeypatch.context() as patch:
            patch.setitem(sys.modules, module.__name__, module)
            snapshots = resolve_stimuli(module.SPEC, values, repo_root=ROOT)
            d = describe_settings(module.SPEC, values, snapshots)
            # Source line positions legitimately move; compare every scientific
            # plan component and preserve full recorded-data comparisons above.
            descriptions.append({k:d[k] for k in ('stimuli','overrides','conditions',
                'resolution','phases','session_phases','phase_inputs','inactive_fields')})
    assert descriptions[0] == descriptions[1]
