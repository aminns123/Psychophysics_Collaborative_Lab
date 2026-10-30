"""Real shared controls: universal Configure, scientific Review, independent lab."""
import asyncio
import json
import shutil
from pathlib import Path
import pytest
from textual.widgets import Button, Input, Select, Collapsible
from psychophysics_lab import extensions as ext
from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ExperimentParametersScreen, ReviewScreen
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def independent_lab(tmp_path, monkeypatch):
    list_experiments()
    ext.unload()
    lab = tmp_path/'independent_lab'
    shutil.copytree(ROOT/'tests/fixtures/review_independent_lab', lab)
    monkeypatch.setattr('psychophysics_lab.development.user_data_root', lambda repo: tmp_path/'development')
    ext.configure(ROOT, lab, trusted=True)
    assert not ext.load(ROOT)
    from psychophysics_lab.development import execute_user_action
    assert execute_user_action(ROOT, 'test', 'auditlab__alternating_flash', {}) == 0
    ext.publish(ROOT, 'experiment', 'auditlab__alternating_flash')
    yield lab
    ext.unload()

@pytest.mark.parametrize('identity,key,value', [
    ('contrast_sensitivity', 'grating_sigma_deg', .35),
    ('ellipse_centre', 'ring_radius_deg', .8),
    ('ellipse_major_axis', 'major_axis_y_deg', .2),
    ('auditlab__alternating_flash', 'gap_from_fixation_deg', 1.1),
])
def test_configure_universal_review_generic_edit_validation_sources(tmp_path, independent_lab, identity, key, value):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(130, 50)) as pilot:
            app.query_one('#participant', Input).value = 'BOUNDARY_TEST'
            app.query_one('#experiment', Select).value = identity
            await pilot.pause()
            app.screen.query_one('#configure', Button).press()
            await pilot.pause()
            config = app.screen
            assert type(config) is ExperimentConfigScreen
            assert not config.query(StimulusParametersPanel)
            assert not config.query('#field-'+key.replace('_','-'))
            assert all(str(c.title) in {'Universal setup', 'Local presets'} for c in config.query(Collapsible))
            config.query_one('#review', Button).press()
            await pilot.pause()
            review = app.screen
            assert isinstance(review, ReviewScreen)
            if identity.startswith('ellipse'):
                assert review.configuration_error
                assert review.query_one('#run-simulation', Button).disabled
            review.query_one('#review-edit-inputs', Button).press()
            await pilot.pause()
            editor = app.screen
            assert type(editor) is ExperimentParametersScreen
            if identity.startswith('ellipse'):
                editor.query_one('#field-ring-increment', Input).value = '.03'
            editor.query_one('#field-'+key.replace('_','-'), Input).value = str(value)
            editor.query_one('#review', Button).press()
            await pilot.pause()
            assert app.screen is review
            assert not review.configuration_error
            assert review.request.experiment_values[key] == value
            groups = {r[0] for r in review._review_rows}
            assert {'Conditions', 'Responses', 'Session start (once)', 'Trial', 'Saved data'} <= groups
            assert any(r[1] == 'Stimulus' for r in review._review_rows)
            assert len(review._review_rows) == len(set(review._review_rows))
            if identity == 'auditlab__alternating_flash':
                assert ('Recorded measurements', 'flash_hold_ms (ms)', '80') in [r[:3] for r in review._review_rows]
                assert float(next(r[2] for r in review._review_rows if r[:2] == ('Trial', 'flash duration'))) == 80
                assert any('toward_left' in r[2] and 'toward_right' in r[2] for r in review._review_rows)
                source_rows = [(r, t) for r, t in zip(review._review_rows, review._file_targets)
                               if r[0] in {'Conditions', 'Recorded measurements'}]
                assert source_rows and all(t['path'].name == 'auditlab__alternating_flash.py'
                                          and t['line'] > 1 for _, t in source_rows)
            row = next(i for i, a in enumerate(review._row_authorities) if a['field'] == key)
            assert review._file_targets[row]['kind'] == 'experiment_json'
            review._edit_review_parameter(row)
            await pilot.pause()
            assert type(app.screen) is ExperimentParametersScreen
            field = app.screen.query_one('#field-'+key.replace('_','-'), Input)
            assert field.has_focus
            field.value = '-100'
            app.screen.query_one('#review', Button).press()
            await pilot.pause()
            assert type(app.screen) is ExperimentParametersScreen
            assert field.value == '-100'
            assert review.request.experiment_values[key] == value
            app.screen.query_one('#back', Button).press()
            await pilot.pause()
            assert app.screen is review
            assert review.request.experiment_values[key] == value
            if identity == 'auditlab__alternating_flash':
                from simulations.run import simulate
                from scripts.validate_run import validate_run
                from psychophysics_lab.data.reader import load_run
                outputs = [simulate(repo_root=ROOT, data_root=tmp_path/'executed', experiment_id=identity,
                           values=review.request.experiment_values, stimulus_snapshots=review.request.stimulus_snapshots,
                           seed=17, analyse=False)[0] for _ in range(2)]
                assert outputs[0].trial_log_file.read_bytes() == outputs[1].trial_log_file.read_bytes()
                for result in outputs:
                    assert result.status == 'completed' and result.accepted_trials == 4
                    assert len(load_run(result.run_directory)['trials']['trial_index']) == 4
                    assert all(check.passed for check in validate_run(result.run_directory))
                    records = json.loads((result.run_directory/'trial_presentations.json').read_text())['trials']
                    assert [r['measurements']['flash_x_deg'] for r in records] == [-value, value, -value, value]
                    assert all(r['measurements']['flash_hold_ms'] == 80 for r in records)
                source = independent_lab/'experiments/auditlab__alternating_flash.py'
                source.write_bytes(source.read_bytes() + b'\n# Deliberate private source-change invalidation test\n')
                assert ext.status(ROOT, 'experiment', identity) == 'draft'
    asyncio.run(scenario())


@pytest.mark.parametrize('damage', ['changed', 'missing'])
def test_universal_setup_does_not_approve_changed_stimulus_file(tmp_path, damage):
    from psychophysics_lab.config.stimulus_parameters import document_for, load_parameters
    from psychophysics_lab.stimuli.registry import get_stimulus
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(130, 50)) as pilot:
            spec = get_experiment('contrast_sensitivity')
            path = tmp_path/'grating.json'
            stimulus = get_stimulus(spec.stimulus_defaults['grating'])
            path.write_text(json.dumps(document_for(stimulus)), encoding='utf-8')
            selected = load_parameters(path, stimulus)
            key = ('FILE_TEST', spec.id, 'legacy_reference_display')
            app.stimulus_drafts[(*key, 'grating')] = (selected, path)
            if damage == 'changed':
                path.write_text('{invalid', encoding='utf-8')
            else:
                path.unlink()
            config = ExperimentConfigScreen(data_root=app.data_root, participant_id=key[0],
                session_mode='new', experiment=spec, monitor_profile_id=key[2], defaults=spec.field_defaults())
            await app.push_screen(config)
            await pilot.pause()
            config.query_one('#review', Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            assert app.screen.configuration_error
            assert all(app.screen.query_one('#'+identity, Button).disabled for identity in
                       ('run', 'run-simulation', 'run-presentation-test', 'run-researcher-override'))
            assert app.return_value is None
            assert app.stimulus_drafts[(*key, 'grating')] == (selected, path)
    asyncio.run(scenario())


@pytest.mark.parametrize('identity', ['contrast_sensitivity', 'ellipse_major_axis'])
def test_refresh_universal_setup_preserves_scientific_draft_and_stimulus_source(tmp_path, identity):
    from psychophysics_lab.ui import refresh
    from psychophysics_lab.config.stimulus_parameters import document_for, load_parameters
    from psychophysics_lab.stimuli.registry import get_stimulus
    async def scenario():
        spec = get_experiment(identity)
        key = ('REFRESH_BOUNDARY', identity, 'legacy_reference_display')
        slot = next(iter(spec.stimulus_slots))
        stimulus = get_stimulus(spec.stimulus_defaults[slot])
        path = tmp_path/'selected stimulus.json'
        path.write_text(json.dumps(document_for(stimulus)), encoding='utf-8')
        selected = load_parameters(path, stimulus)
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(130, 50)) as pilot:
            app.stimulus_drafts[(*key, slot)] = (selected, path)
            config = ExperimentConfigScreen(data_root=app.data_root, participant_id=key[0],
                session_mode='new', experiment=spec, monitor_profile_id=key[2], defaults=spec.field_defaults())
            await app.push_screen(config)
            await pilot.pause()
            state = refresh.capture_state(app)
            assert state['page'] == 'configuration'
            assert state['stimuli'][slot] == selected
            assert state['sources']['stimuli'][slot] == str(path)
        resumed = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data', refresh_state=state)
        async with resumed.run_test(size=(130, 50)) as pilot:
            await pilot.pause()
            assert type(resumed.screen) is ExperimentConfigScreen
            assert not resumed.screen.query(StimulusParametersPanel)
            assert resumed.stimulus_drafts[(*key, slot)][1] == path
            assert resumed.screen._field_values(allow_incomplete=True) == spec.field_defaults()
    asyncio.run(scenario())
