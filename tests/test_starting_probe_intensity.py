"""Absolute probe inputs must feed real rendering, adaptation and saved data."""
import asyncio
import csv
import importlib
import json
from pathlib import Path

import numpy as np
import pytest
from textual.widgets import Input, Static, DataTable, Button

from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.core.presentation import render_values
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui.parameter_files import load_experiment_json
from psychophysics_lab.ui.settings_review import probe_intensity_rows
from psychophysics_lab.researcher import RunContext
from simulations.registry import TeachingObserver
from simulations.run import simulate

ROOT = Path(__file__).resolve().parents[1]
TASKS = ('line_position_baseline', 'line_position_flanker', 'ellipse_centre', 'ellipse_major_axis')


def values_for(identity, **overrides):
    values = {'starting_probe_intensity':.8, 'staircases_per_condition':1, 'max_trials':3,
              'n_down':1, 'logUNIT_DW':.3, 'initial_one_down_limit':0}
    if identity.startswith('line_'):
        values.update(positions_deg='0', probe_vertical_offset_deg=.5)
        if identity.endswith('flanker'):
            values['flanker_cpd'] = 2.
    else:
        values.update(ring_increment=.1, aspect_ratios='1')
        if identity == 'ellipse_major_axis':
            values['positions_deg'] = '0'
    return get_experiment(identity).normalise_values(values | overrides)


@pytest.mark.parametrize('identity', TASKS)
def test_absolute_input_reaches_actual_trials_updates_and_saved_strength(tmp_path, monkeypatch, identity):
    seen = []
    original = RunContext.trial
    def capture(run, *args, **kwargs):
        seen.append(kwargs['parameters_by_slot']['first']['contrast'])
        return original(run, *args, **kwargs)
    monkeypatch.setattr(RunContext, 'trial', capture)
    values = values_for(identity)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=identity,
        values=values, observer=TeachingObserver(accuracy=1.), analyse=False)
    with artifacts.trial_log_file.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert len(rows) == len(seen) == 3
    expected_by_staircase = {}
    for presented, row in zip(seen, rows):
        identity = row['staircase_id']
        expected = expected_by_staircase.get(identity, .8-.5)
        assert presented == pytest.approx(expected)
        assert float(row['presented_display_contrast']) == pytest.approx(expected)
        expected *= 10**(-.3)
        expected_by_staircase[identity] = expected
        assert float(row['next_display_contrast']) == pytest.approx(expected)


def test_white_start_is_accepted_drawn_white_and_holds_on_outward_steps(tmp_path):
    values = values_for('line_position_baseline', starting_probe_intensity=1.)
    spec = get_stimulus('detection_scene')
    parameters = {f.key:f.default for f in spec.parameters}
    parameters.update(background=.5, contrast=values['starting_probe_intensity']-.5,
                      probe_x_deg=2., probe_y_deg=1., probe_width_deg=1., probe_length_deg=1.)
    image = render_values(spec, parameters, pixels=(512,512))
    assert np.max(image) == pytest.approx(1.)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id='line_position_baseline',
        values=values, observer=TeachingObserver(accuracy=0.), analyse=False)
    with artifacts.trial_log_file.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert len(rows) == 3
    assert all(float(r['presented_display_contrast']) == .5 and float(r['next_display_contrast']) == .5 for r in rows)
    assert all(r['reversal'] == '0' for r in rows)


@pytest.mark.parametrize('identity', TASKS)
def test_old_increment_json_is_explicitly_converted_without_rewriting(tmp_path, identity):
    spec = get_experiment(identity)
    old = values_for(identity)
    old.pop('starting_probe_intensity')
    old.update(background_intensity=.25, starting_contrast=.3)
    path = tmp_path/'old.json'
    path.write_text(json.dumps({'schema_version':1, 'experiment_id':identity, 'values':old}), encoding='utf-8')
    before = path.read_bytes()
    migrated = load_experiment_json(path, spec)
    assert path.read_bytes() == before
    assert migrated['starting_probe_intensity'] == .55
    assert 'starting_contrast' not in migrated
    assert migrated['starting_probe_intensity'] - migrated['background_intensity'] == pytest.approx(.3)
    with pytest.raises(ValueError, match='disagree'):
        spec.normalise_values(old | {'starting_probe_intensity':.9})
    with pytest.raises(ValueError, match='too small'):
        spec.normalise_values(old | {'starting_contrast':1e-30})


def test_step_scale_explains_real_updates_and_does_not_invent_steps_to_background():
    spec = get_experiment('line_position_baseline')
    values = values_for(spec.id, starting_probe_intensity=1., logUNIT_DW=np.log10(2))
    rows = {label:(value, note) for _, label, value, note in probe_intensity_rows(spec,values)}
    assert rows['Starting difference from background'][0] == '0.5'
    assert rows['Relative digital contrast'][0] == '1'
    assert 'intensity 0.75; difference 0.25' == rows['After one decrease'][0]
    assert rows['After one increase'][0] == 'intensity 1; difference 0.5'
    assert rows['Exact background'][0] == 'No finite number of log decreases'
    assert rows['Decreases to <= 1% of starting difference'][0] == '7'
    assert 'not trials' in rows['Decreases to <= 1% of starting difference'][1]
    black = probe_intensity_rows(spec, values | {'background_intensity':0})
    assert any(value == 'undefined at black background' for _,_,value,_ in black)
    equal = probe_intensity_rows(spec, values | {'starting_probe_intensity':.5})
    assert any(value == 'Already at background' for _,_,value,_ in equal)


def test_live_tui_and_review_show_absolute_input_and_derived_step_scale(tmp_path):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen
    async def scenario():
        spec = get_experiment('line_position_baseline')
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path)
        async with app.run_test(size=(130,50)) as pilot:
            screen = ExperimentConfigScreen(data_root=tmp_path, participant_id='INTENSITY', session_mode='new',
                experiment=spec, monitor_profile_id='legacy_reference_display', defaults=values_for(spec.id))
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one('#field-starting-probe-intensity', Input).value = '1.0'
            screen.query_one('#field-logUNIT-DW', Input).value = str(np.log10(2))
            await pilot.pause()
            message = str(screen.query_one('#contrast-live-validation', Static).render())
            assert 'Starting difference from background: 0.5' in message
            assert 'intensity 0.75; difference 0.25' in message
            assert 'No finite number' in message
            assert screen._collect()['starting_probe_intensity'] == 1.
            screen.query_one('#review', Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            table = app.screen.query_one('#resolved-settings-table', DataTable)
            rendered = str([table.get_row_at(i) for i in range(table.row_count)])
            assert 'Relative digital contrast' in rendered
            assert 'Decreases to <= 1%' in rendered and 'No finite number' in rendered
            assert app.screen.request.experiment_values['starting_probe_intensity'] == 1.
    asyncio.run(scenario())


@pytest.mark.parametrize('identity', TASKS)
def test_subnormal_start_does_not_turn_a_down_step_into_an_increase(identity):
    # The existing log rule retains sys.float_info.min as a recoverable floor.
    # Reject a new absolute input below it rather than silently jumping upward.
    with pytest.raises(ValueError, match='numeric floor'):
        values_for(identity, background_intensity=0., starting_probe_intensity=5e-324)


def test_exact_background_remains_a_valid_control_and_saves_responses(tmp_path):
    values = values_for('line_position_baseline', starting_probe_intensity=.5)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id='line_position_baseline',
        values=values, observer=TeachingObserver(accuracy=0.), analyse=False)
    with artifacts.trial_log_file.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert len(rows) == 3 and float(rows[0]['presented_display_contrast']) == 0
    assert float(rows[0]['next_display_contrast']) > 0
