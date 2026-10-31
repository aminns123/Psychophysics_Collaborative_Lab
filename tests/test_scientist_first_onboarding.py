"""The recommended local examples execute unchanged science through public APIs."""
import asyncio
from dataclasses import replace
from datetime import datetime
import hashlib
import importlib
import json
from pathlib import Path
import types

import pytest
from textual.widgets import Button
from psychophysics_lab import extensions as ext
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.ui.setup import PsyCoLabSetupApp
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run
from test_laboratory_extensions import lab, enable, ready

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT/'tests/fixtures/onboarding_develop_649b705'


@pytest.mark.parametrize('identity,method', [
    ('demolab__left_right', None), ('demolab__line_strength', 'adaptive'),
    ('demolab__line_strength', 'constant_stimuli')])
@pytest.mark.parametrize('seed,accuracy', [(0, 0.), (19, .65), (137, 1.)])
@pytest.mark.parametrize('opening', [False, True])
def test_starter_scientific_records_match_frozen_develop(lab, tmp_path, monkeypatch, identity, method, seed, accuracy, opening):
    ready(lab)
    if identity.endswith('strength'):
        from psychophysics_lab.development import execute_user_action
        assert execute_user_action(ROOT, 'test', identity, {}) == 0
        ext.publish(ROOT, 'experiment', identity)
    current = registry.get_experiment(identity)
    module = importlib.import_module(current.procedure.__module__)
    raw = (FROZEN/(identity+'.py')).read_bytes().replace(b'\r\n', b'\n')
    expected = json.loads((FROZEN/'baseline.json').read_text())['source_sha256_lf'][identity]
    assert hashlib.sha256(raw).hexdigest() == expected
    original = types.ModuleType(module.__name__)
    original.__file__ = module.__file__
    exec(compile(raw, original.__file__, 'exec'), original.__dict__)
    # Apply the same namespace/display normalization as the real extension loader.
    # Both versions retain the real lab source boundary, trust and fingerprints.
    original.SPEC = replace(original.SPEC, origin_namespace=current.origin_namespace,
                            display_name=current.display_name)
    assert current.fields == original.SPEC.fields
    assert current.response_paradigm == original.SPEC.response_paradigm
    assert current.calibration_requirements == original.SPEC.calibration_requirements
    assert current.stimulus_defaults == original.SPEC.stimulus_defaults
    runs = []
    for spec in (original.SPEC, current, current):
        if not opening:
            spec = replace(spec, session_start=[])
        values = {'trial_count': 7}
        if method:
            values.update(contrast_method=method, fixed_contrasts='0,.1,.5', fixed_repetitions=3)
        with monkeypatch.context() as patch:
            patch.setitem(registry._REGISTRY, identity, spec)
            artifact, _ = simulate(repo_root=ROOT, data_root=tmp_path/'science',
                experiment_id=identity, values=values, seed=seed, observer=TeachingObserver(accuracy), analyse=False)
        assert all(c.passed for c in validate_run(artifact.run_directory))
        runs.append(artifact)
    assert len({r.trial_log_file.read_bytes() for r in runs}) == 1
    for name in ('trial_actions.json', 'trial_events.jsonl', 'adaptive_history.json',
                 'adaptive_session.json', 'resolved_experiment.json'):
        paths = [r.run_directory/name for r in runs]
        assert len({p.exists() for p in paths}) == 1
        if paths[0].exists():
            assert len({p.read_bytes() for p in paths}) == 1, name
    sessions = []
    for artifact in runs:
        path = artifact.run_directory/'session_events.json'
        assert path.exists() == opening
        if opening:
            session = json.loads(path.read_text(encoding='utf-8'))
            # Real wall-clock recording times differ even in virtual sessions.
            # Validate these exact fields; compare every other field unchanged.
            assert datetime.fromisoformat(session.pop('started_utc')).utcoffset() is not None
            for node in (session, *session['events']):
                start = node.pop('software_started_s')
                finish = node.pop('software_finished_s')
                assert 0 <= start <= finish
            sessions.append(session)
    assert not sessions or sessions[0] == sessions[1] == sessions[2]


def test_build_experiments_links_to_executable_scientist_first_learning_path(tmp_path, monkeypatch):
    opened = []
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        monkeypatch.setattr(app, 'inspect_source', lambda path: opened.append(path))
        async with app.run_test(size=(120, 45)) as pilot:
            app.open_hub_page('experiments')
            await pilot.pause()
            for identity in ('read-example-experiment', 'read-method-example', 'read-local-starters'):
                app.screen.query_one('#'+identity, Button).press()
                await pilot.pause()
                assert opened[-1].is_file()
            for path in opened[:2]:
                source = path.read_text(encoding='utf-8')
                assert source.index('# PART A1') < source.index('def trial_events') < source.index('# PART A2')
                assert source.index('# PART A1') < source.index('def trial_measurements') < source.index('# PART A2')
                assert source.index('# PART A2') < source.index('def interpret_response') < source.index('# PART B')
    asyncio.run(scenario())
