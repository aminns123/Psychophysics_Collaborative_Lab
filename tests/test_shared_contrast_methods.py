"""Method selection is public and reusable outside the CSF experiment.

The fake study deliberately uses *probe increment* and a named elliptical
condition. No CSF frequency or grating assumptions are allowed in the policy.
"""
from collections import Counter
from contextlib import contextmanager
from types import SimpleNamespace
import random

import pytest

from psychophysics_lab.methods.contrast import (
    AdaptiveContrastMethod,
    ConstantContrastMethod,
    fixed_level_schedule,
    parse_fixed_strengths,
    run_contrast_experiment,
    select_contrast_method,
)


@pytest.mark.parametrize("raw", ["", ",", "0.1,,0.2", "nan", "inf", "abc",
                                    ".2,.2", "-.01", "1.01"])
def test_fixed_strengths_reject_invalid_input(raw):
    with pytest.raises(ValueError):
        parse_fixed_strengths(raw, minimum=0, maximum=1)


def test_fixed_strengths_explicit_scientific_bounds():
    assert parse_fixed_strengths("0,0.02,0.05", maximum=0.05) == (0, 0.02, 0.05)
    with pytest.raises(ValueError, match="between"):
        parse_fixed_strengths("0.06", maximum=0.05)


def test_method_factory_constructs_only_selected_policy():
    created = []
    value = select_contrast_method(
        "constant_stimuli",
        {"adaptive": lambda: created.append("adaptive"),
         "constant_stimuli": lambda: created.append("fixed")},
    )
    assert value is None
    assert created == ["fixed"]
    with pytest.raises(ValueError, match="Unsupported"):
        select_contrast_method("invalid", {"adaptive": lambda: object()})


def test_fixed_schedule_supports_generic_named_conditions_without_mutation():
    conditions = [
        {"value": "x=0;ratio=1.2", "x_deg": 0.0, "aspect_ratio": 1.2,
         "ring": True, "id": 1, "repeat": 1},
        {"value": "x=0;ratio=2.0", "x_deg": 0.0, "aspect_ratio": 2.0,
         "ring": True, "id": 2, "repeat": 1},
    ]
    snapshot = [dict(c) for c in conditions]
    a = fixed_level_schedule(conditions, [0.01, 0.02], 4, seed=77,
                             condition_field="value", strength_field="contrast")
    b = fixed_level_schedule(conditions, [0.01, 0.02], 4, seed=77,
                             condition_field="value", strength_field="contrast")
    assert a == b
    assert a != fixed_level_schedule(conditions, [0.01, 0.02], 4, seed=78)
    assert conditions == snapshot
    assert len(a) == 16
    for row in a:
        assert row["ring"] is True
        assert "id" not in row
        assert row["contrast"] in (0.01, 0.02)
    for value in ("x=0;ratio=1.2", "x=0;ratio=2.0"):
        for strength in (0.01, 0.02):
            filtered = [v for v in a if v["value"] == value and v["contrast"] == strength]
            assert len(filtered) == 4
            assert Counter(v["target"] for v in filtered) == {0: 2, 1: 2}


def test_original_csf_numeric_schedule_rng_sequence_is_preserved():
    # Reference pseudocode from the accepted CSF implementation before
    # selection moved behind the public shared method interface.
    old = []
    rng = random.Random("17:constant-stimuli")
    for frequency in (2., 4., 8.):
        for level in (0.02, 0.04):
            targets = [0, 1] * 3
            rng.shuffle(targets)
            for repeat, target in enumerate(targets, 1):
                old.append({"frequency_cpd": frequency, "contrast": level,
                            "repeat": repeat, "target": target, "value": frequency})
    rng.shuffle(old)
    assert fixed_level_schedule(
        [2., 4., 8.], [0.02, 0.04], 6, seed=17,
    ) == old


class FakeRun:
    def __init__(self, *, method="constant_stimuli"):
        self.values = {"contrast_method": method}
        self.responses = SimpleNamespace(keys=("F", "J"))
        self.seed = 6
        self.initial = None
        self.resolved = None
        self.finished = False
        self.trials = []

    def initialise(self, **kwargs):
        self.initial = kwargs

    @contextmanager
    def trial(self, timeline, **kwargs):
        self.trials.append(kwargs)
        target = kwargs["target"]
        yield SimpleNamespace(response={"alternative": target, "correct": True})

    def save_resolution(self, **kwargs):
        self.resolved = kwargs

    def complete(self):
        self.finished = True


def test_generic_constant_method_runs_non_csf_study_and_records_accuracy():
    run = FakeRun()
    schedule = fixed_level_schedule(
        [{"value": "ratio=2", "aspect_ratio": 2, "x_deg": 0}],
        [0.04, 0.08], 3, seed=run.seed,
        condition_field="value", strength_field="probe_increment",
    )
    policy = lambda: ConstantContrastMethod(
        run, schedule=schedule,
        resolution={"trial_selection_method": "constant_stimuli"},
        condition_field="value", strength_field="probe_increment",
        record=lambda _run, selection: {
            "state": {"contrast": selection["probe_increment"]},
            "record_from_state": {"presented_display_contrast": "contrast"},
        },
    )
    run_contrast_experiment(
        run, methods={"constant_stimuli": policy},
        prepare_stimuli=lambda _run, selection, _state: {
            "probe": {"contrast": selection["probe_increment"],
                      "aspect_ratio": selection["aspect_ratio"]}},
        make_trial=lambda _settings, selection: "trial-timeline",
        interpret_response=lambda selection, response: response,
    )
    assert run.initial == {"expected_trials": 6,
                           "resolution": {"trial_selection_method": "constant_stimuli"}}
    assert run.finished and len(run.trials) == 6
    assert {v["condition"] for v in run.trials} == {"ratio=2"}
    assert {v["parameters_by_slot"]["probe"]["contrast"] for v in run.trials} == {.04, .08}
    assert len(run.resolved["observed_level_accuracy"]) == 2
    assert all(row["accepted_trials"] == 3 and row["proportion_correct"] == 1.
               for row in run.resolved["observed_level_accuracy"])
    assert all("staircase_id" not in trial for trial in run.trials)


def test_adaptive_adapter_preserves_existing_callback_order_and_state():
    run = FakeRun(method="adaptive")
    events = []
    def conditions(_settings):
        events.append("conditions")
        return [{"value": 1, "target": 0, "contrast": 0.1}]
    def initialise(_run, selections):
        events.append("initialise")
        return {"trial_count": 0}
    def finished(_run, selections, state):
        return state["trial_count"] == 1
    def select(_run, selections, state):
        events.append("select")
        return selections[0]
    def record(_run, selection, state):
        events.append("record")
        return {"state": {"contrast": selection["contrast"]}}
    def update(_run, selection, state, response, trial):
        events.append("update")
        return {"trial_count": state["trial_count"] + 1}
    def finish(_run, selections, state):
        events.append("complete")
        _run.complete()
    policy = lambda: AdaptiveContrastMethod(
        run, make_conditions=conditions, initialise=initialise,
        select=select, record=record, update=update, finished=finished,
        finish=finish,
    )
    run_contrast_experiment(
        run, methods={"adaptive": policy},
        prepare_stimuli=lambda _run, selection, state: {
            "target": {"contrast": selection["contrast"]}},
        make_trial=lambda _settings, selection: "trial-timeline",
        interpret_response=lambda selection, response: response,
    )
    assert run.finished
    assert events == ["conditions", "initialise", "select", "record", "update", "complete"]
