"""User-reported ceiling crash, near-fixation geometry, cues and visible units."""
import asyncio
import csv
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from textual.widgets import Label

from psychophysics_lab.adaptive import AdaptiveRun, StaircaseConfig, Step
from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.core.presentation import render_values
from psychophysics_lab.researcher import RunContext
from psychophysics_lab.stimuli.registry import get_stimulus
from scripts.validate_run import validate_run
from simulations.run import simulate

ROOT = Path(__file__).resolve().parents[1]
MODERN = ('contrast_sensitivity', 'line_position_baseline', 'line_position_flanker',
          'ellipse_centre', 'ellipse_major_axis')


@pytest.mark.parametrize('name', MODERN)
def test_outward_steps_hold_and_can_move_inward_without_changing_normal_steps(name):
    module = importlib.import_module('psychophysics_lab.experiments.' + name)
    values = dict(contrast=.49, maximum_contrast=.75, log_up=.36, log_down=.30294)
    assert module.change_contrast(values, {}, Step.UP) == .75
    values['contrast'] = .75
    assert module.change_contrast(values, {}, Step.UP) == .75
    assert module.change_contrast(values, {}, Step.HOLD) == .75
    assert module.change_contrast(values, {}, Step.DOWN) == pytest.approx(.75 * 10**(-.30294))
    # Both extreme exponents avoid intermediate overflow or an absorbing zero.
    values.update(contrast=.1, log_up=1e100, log_down=1e100)
    assert module.change_contrast(values, {}, Step.UP) == .75
    values['contrast'] = module.change_contrast(values, {}, Step.DOWN)
    assert values['contrast'] == sys.float_info.min
    assert module.change_contrast(values, {}, Step.UP) == .75


def test_boundary_holds_are_accepted_responses_without_fabricated_reversals():
    algorithm = AdaptiveRun({1: StaircaseConfig(1, 1, 10)}, 20)
    value = .49
    for correct in (False, False, False, False, True):
        _, value = algorithm.respond(1, correct, lambda step: bounded_log_step(
            value, -.3 if step == Step.DOWN else .36, maximum=.75))
    assert algorithm.total_trials == 5
    assert algorithm.states[1].reversal_count == 0
    assert value < .75
    _, value = algorithm.respond(1, False, lambda step: bounded_log_step(value, .36, maximum=.75))
    assert value == .75 and algorithm.states[1].reversal_count == 1


@pytest.mark.parametrize('name', MODERN)
def test_run_continues_at_ceiling_saves_answers_and_flags_boundary_affected_result(tmp_path, monkeypatch, name):
    # Deliberately make every response wrong to force a persistent ceiling hold.
    original = RunContext.trial
    def wrong_answers(run, *args, **kwargs):
        run.observer_probability = None
        run.observer_parameters = {'accuracy': 0.0}
        return original(run, *args, **kwargs)
    monkeypatch.setattr(RunContext, 'trial', wrong_answers)
    values = dict(starting_contrast=.3, staircases_per_condition=1, max_trials=8)
    if name.startswith('line_'):
        # Reproduce the user's actual settings, including intentional overlap.
        values.update(positions_deg='0.0', starting_contrast=.49, background_intensity=.25,
                      probe_vertical_offset_deg=.01, fixation_ms=1000, stimulus_ms=1000,
                      auditory_cues=True)
        if name.endswith('flanker'): values['flanker_cpd'] = 2.
    elif name.startswith('ellipse_'):
        values['ring_increment'] = .1
    identity = 'contrast_sensitivity' if name == 'contrast_sensitivity' else name
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path/'data', experiment_id=identity,
                            values=values, analyse=False)
    assert artifacts.status == 'max_trials_reached'
    with artifacts.trial_log_file.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert len(rows) == 8 and all(r['correct'] == '0' for r in rows)
    assert all(r['reversal'] == '0' for r in rows)
    result = json.loads((artifacts.run_directory/'primary_thresholds.json').read_text())
    assert result['boundary_affected_staircases']
    assert result['boundary_warning'] and not result['condition_thresholds']
    assert all(check.passed for check in validate_run(artifacts.run_directory))
    if name.startswith('line_'):
        assert {float(row['next_display_contrast']) for row in rows} == {.75}  # At x=0 the probe does not overlap the flanker ending at x=-0.5.
        traces = json.loads((artifacts.run_directory/'trial_actions.json').read_text())['trials']
        for trial in traces:
            tones = [e['audio'] for e in trial['events'] if 'audio' in e]
            assert [t['trigger'] for t in tones] == ['display_onset', 'accepted_response']
            assert all('no sound generated' in tone['output'] for tone in tones)


@pytest.mark.parametrize('name', ['line_position_baseline', 'line_position_flanker'])
def test_line_cues_are_optional_explicit_and_do_not_encode_answer(name):
    module = importlib.import_module('psychophysics_lab.experiments.' + name)
    values = module.SPEC.field_defaults()
    for enabled in (False, True):
        phases = module.make_trial(values | {'auditory_cues': enabled, 'cue_hz': 880, 'cue_ms': 70}, {}).phases
        assert phases[0].beep is None
        for phase in phases[1:]:
            assert bool(phase.beep) == enabled
            if enabled:
                assert (phase.beep.frequency_hz, phase.beep.duration_ms) == (880, 70)


def test_baseline_uses_full_physical_intensity_headroom_and_does_not_restrict_overlap():
    from psychophysics_lab.experiments.line_position_baseline import SPEC, prepare_stimuli
    values = SPEC.field_defaults() | {'starting_probe_intensity': 1., 'background_intensity': .25,
                                    'positions_deg': '0.0', 'probe_vertical_offset_deg': .01}
    assert SPEC.normalise_values(values)['starting_probe_intensity'] == 1.
    stimulus = get_stimulus('detection_scene')
    defaults = {f.key: f.default for f in stimulus.parameters}
    class Run:
        def __init__(self): self.values = values
        def stimulus_parameters(self, slot, **overrides): return defaults | overrides
    above = prepare_stimuli(Run(), {'x_deg': 0, 'contrast': .75, 'target': 0}, {})
    below = prepare_stimuli(Run(), {'x_deg': 0, 'contrast': .75, 'target': 1}, {})
    assert above['first']['probe_y_deg'] == .01 and below['first']['probe_y_deg'] == -.01
    a = render_values(stimulus, above['first'], pixels=(524, 520))
    b = render_values(stimulus, below['first'], pixels=(524, 520))
    assert np.max(abs(a-b)) > 0
    assert np.allclose(a, b[::-1])
    # No absent flanker forces a >0 background; fixation itself is capped at white.
    for background in (0., .95):
        pixels = render_values(stimulus, defaults | {'background': background, 'contrast': min(.02,1-background)})
        assert pixels.min() >= 0 and pixels.max() <= 1


def test_experiment_form_displays_declared_units(tmp_path):
    from psychophysics_lab.experiments.line_position_baseline import SPEC
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(110, 42)) as pilot:
            app.push_screen(ExperimentConfigScreen(data_root=tmp_path/'data', participant_id='T_UNITS',
                session_mode='new', experiment=SPEC, monitor_profile_id='legacy_reference_display', defaults=SPEC.field_defaults()))
            await pilot.pause()
            labels = '\n'.join(str(label.render()) for label in app.screen.query(Label))
            assert 'ms' in labels and 'degrees' in labels and 'digital intensity' in labels
            assert 'log10 units' in labels
    asyncio.run(scenario())
