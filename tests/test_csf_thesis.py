"""Thesis protocol tests; no claim of physical/photometric equivalence."""
import csv
import json
import math
from pathlib import Path
from statistics import median, mean
from types import SimpleNamespace

import numpy as np
import pytest

from psychophysics_lab.experiments.contrast_sensitivity import SPEC, make_trial, change_contrast, procedure
from psychophysics_lab.adaptive import AdaptiveRun, StaircaseConfig, Step
from psychophysics_lab.researcher import RunContext
from psychophysics_lab.stimulus_library import ContrastSensitivityGrating, GaussianFixation
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("side,sign", [("left", -1), ("right", 1)])
@pytest.mark.parametrize("offset_deg", [0.25, 0.5, 1.0, 2.0])
def test_csf_timeline_respects_researcher_selected_grating_position(side, sign, offset_deg):
    # Both the location and phase durations belong to the selected run settings;
    # do not bake a thesis example's numeric values into a runtime contract.
    settings = SPEC.normalise_values(SPEC.field_defaults() | {
        "grating_offset_deg": offset_deg,
        "fixation_ms": 420,
        "grating_ms": 280,
    })
    phases = make_trial(settings, {"target": 0 if side == "left" else 1}).resolve(settings).phases
    assert [(p.name, p.duration_ms) for p in phases] == [
        ("fixation", settings["fixation_ms"]),
        ("grating", settings["grating_ms"]),
        ("answer", 0),
    ]
    assert [s.slot for s in phases[0].placements] == ["fixation"]
    assert [(s.slot, s.x_deg) for s in phases[1].placements] == [
        ("grating", sign * settings["grating_offset_deg"])
    ]
    assert [s.slot for s in phases[2].placements] == ["fixation"]
    assert phases[2].actions == ("left", "right")
    assert all(p.beep is None for p in phases)


@pytest.mark.parametrize("invalid", [0, -0.5, float("nan"), float("inf")])
def test_grating_offset_must_be_a_positive_finite_selected_distance(invalid):
    with pytest.raises(ValueError):
        SPEC.normalise_values(SPEC.field_defaults() | {"grating_offset_deg": invalid})


def test_gaussian_sigma_and_grating_frequency_are_in_degrees_and_cpd():
    values = {f.key: f.default for f in ContrastSensitivityGrating.PARAMETERS}
    values.update(contrast=.1, spatial_frequency_cpd=1.25, background=.3)
    x, y = np.array([[.2]]), np.array([[0.]])
    assert ContrastSensitivityGrating.render(values, x, y)[0, 0] == pytest.approx(.3+.05*math.exp(-.2**2/2))
    fixation = {f.key: f.default for f in GaussianFixation.PARAMETERS}
    fixation["background"] = .95
    assert GaussianFixation.render(fixation, np.zeros((1,1)), np.zeros((1,1)))[0,0] == 1.
    values.update(contrast=.9, background=.1)
    with pytest.raises(ValueError, match="no silent clipping"):
        ContrastSensitivityGrating.validate(values)


def test_table_4_4_has_no_hidden_introductory_one_down_phase():
    a = AdaptiveRun({1: StaircaseConfig(4, 1, 10)}, 100)
    state = {"contrast": .1, "maximum_contrast": 1., "log_up":.36, "log_down":.30294}
    steps = []
    for correct in (True,True,True,True,False):
        step, value = a.respond(1, correct, lambda step: change_contrast(state, {"correct":correct}, step))
        steps.append(step)
        state["contrast"] = value
    assert steps == [Step.HOLD, Step.HOLD, Step.HOLD, Step.DOWN, Step.UP]
    assert state["contrast"] == pytest.approx(.1*10**(-.30294+.36))
    # Bounded updates supersede the former abort-on-overshoot policy.
    assert change_contrast({"contrast":.9, "maximum_contrast":1., "log_up":.36, "log_down":.30294}, {"correct":False}, Step.UP) == 1.0


def test_mixed_virtual_responses_finish_staircases_and_use_the_thesis_point_estimator(tmp_path, monkeypatch):
    original = RunContext.trial
    seen = {}
    def scripted(run, *args, **kwargs):
        if run.spec.id == "contrast_sensitivity":
            identity = kwargs["state"]["staircase_id"]
            count = seen.get(identity, 0)
            seen[identity] = count+1
            run.observer_probability = None  # This test scripts responses, rather than using a psychometric observer.
            run.observer_parameters = {"accuracy": 0. if count % 5 == 4 else 1.}
        return original(run, *args, **kwargs)
    monkeypatch.setattr(RunContext, "trial", scripted)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path/"data", experiment_id="contrast_sensitivity",
        values={"frequencies_cpd":"2", "staircases_per_condition":2, "max_trials":500, "starting_contrast":.02}, analyse=False)
    assert artifacts.status == "completed"
    assert all(c.passed for c in validate_run(artifacts.run_directory))
    resolved = json.loads((artifacts.run_directory/"resolved_experiment.json").read_text())
    reversals = resolved["reversal_contrasts"]
    assert all(len(r) == 10 for r in reversals.values())
    expected = mean(median(r[-8:]) for r in reversals.values())
    assert resolved["condition_thresholds"]["2.0"]["threshold"] == expected
    assert resolved["condition_thresholds"]["2.0"]["sensitivity"] == pytest.approx(1/expected)
    rows = list(csv.DictReader(artifacts.trial_log_file.open(), delimiter="\t"))
    assert {row["target_alternative"] for row in rows} == {"0", "1"}
    assert all(row["response_key"].startswith("SIMULATED_") for row in rows)
    actions = json.loads((artifacts.run_directory/"trial_actions.json").read_text())["trials"]
    responses = [e["response"]["meaning"] for t in actions for e in t["events"] if e["kind"] == "response"]
    assert set(responses) == {"left", "right"}


def test_response_safety_ceiling_does_not_fabricate_a_completed_csf(tmp_path):
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path/"data", experiment_id="contrast_sensitivity",
        values={"max_trials":4}, analyse=False)
    assert artifacts.status == "max_trials_reached"
    resolved = json.loads((artifacts.run_directory/"resolved_experiment.json").read_text())
    assert resolved["condition_thresholds"] == {}
    assert all(c.passed for c in validate_run(artifacts.run_directory))


def test_direct_human_call_is_blocked_before_opening_a_display(tmp_path):
    run = RunContext(SPEC.field_defaults(), SimpleNamespace(id="unused"), SPEC, tmp_path)
    with pytest.raises(ValueError, match="qualified before human acquisition"):
        procedure(run)


@pytest.mark.parametrize("value", [float("nan"), -1, 2, True])
def test_bad_background_is_rejected_before_display_creation(tmp_path, value):
    run = RunContext({}, SimpleNamespace(id="unused"), SPEC, tmp_path, synthetic=True)
    with pytest.raises(ValueError, match="Background"):
        run.initialise(expected_trials=1, resolution={"test":True}, background_intensity=value)
    assert run.status == "created" and not (tmp_path/"runtime_display.json").exists()


def test_shared_presenter_clears_to_the_experiments_background(monkeypatch):
    import sys
    from test_action_presentation import fake_presentation
    from psychophysics_lab.researcher import CollectResponse
    display, _, _ = fake_presentation(monkeypatch)
    display.background_intensity = .3
    colours = []
    monkeypatch.setattr(sys.modules["pyglet"].gl, "glClearColor", lambda *c: colours.append(c))
    display.play_phase(CollectResponse(actions=("left","right")), {})
    assert colours == [(.3,.3,.3,1)]


def test_tui_selected_adaptive_values_control_the_run(tmp_path, monkeypatch):
    import asyncio
    from textual.widgets import Input
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen

    selected = {"n_down":2, "n_up":2, "logUNIT_UP":.1, "logUNIT_DW":.05,
                "reversal_termination":4, "threshold_reversals":2,
                "initial_one_down_limit":0, "staircases_per_condition":1,
                "max_trials":100, "frequencies_cpd":"2", "starting_contrast":.02,
                "grating_offset_deg":1.75}
    async def collect():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path/"tui_data")
        async with app.run_test(size=(100, 40)) as pilot:
            app.push_screen(ExperimentConfigScreen(data_root=tmp_path/"tui_data",
                participant_id="T001", session_mode="new", experiment=SPEC,
                monitor_profile_id="legacy_reference_display", defaults=SPEC.field_defaults()))
            await pilot.pause()
            for key, value in selected.items():
                app.screen.query_one("#field-"+key.replace("_", "-"), Input).value = str(value)
            values = app.screen._collect()
            return values, app.screen.stimulus_snapshots
    values, snapshots = asyncio.run(collect())
    assert all(s["file_identity"] == "library_defaults" for s in snapshots.values())
    assert all(values[k] == v for k, v in selected.items())
    original = RunContext.trial
    presented = []
    def scripted(run, *args, **kwargs):
        presented.append(kwargs["state"]["contrast"])
        run.observer_probability = None  # This test scripts responses, rather than using a psychometric observer.
        run.observer_parameters = {"accuracy":1. if (len(presented)-1) % 4 < 2 else 0.}
        return original(run, *args, **kwargs)
    monkeypatch.setattr(RunContext, "trial", scripted)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path/"data", experiment_id=SPEC.id,
                            values=values, stimulus_snapshots=snapshots, analyse=False)
    assert artifacts.status == "completed"
    assert presented[:5] == pytest.approx([.02, .02, .02*10**(-.05), .02*10**(-.05), .02*10**.05])
    resolved = json.loads((artifacts.run_directory/"resolved_experiment.json").read_text())
    assert resolved["adaptive_rule"] == {"algorithm":"consecutive_up_down", "n_down":2, "n_up":2,
        "log_up":.1, "log_down":.05, "reversal_limit":4, "initial_one_down_limit":0, "max_trials":100}
    reversals = resolved["reversal_contrasts"]["1"]
    assert len(reversals) == 4
    assert resolved["threshold_reversals"] == 2
    assert resolved["target_offset_deg"] == pytest.approx(selected["grating_offset_deg"])
    assert resolved["condition_thresholds"]["2.0"]["threshold"] == median(reversals[-2:])
    assert all(c.passed for c in validate_run(artifacts.run_directory))
    with pytest.raises(ValueError, match="Threshold reversal count"):
        SPEC.normalise_values(values | {"threshold_reversals":5})
