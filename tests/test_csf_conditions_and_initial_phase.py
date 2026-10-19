"""Condition-list parity and introductory 1-down semantics, in real pipeline."""
from pathlib import Path
import csv
import json

import pytest

from psychophysics_lab.adaptive.staircase import AdaptiveRun, StaircaseConfig, Step
from simulations.run import simulate
from simulations.scenarios import run_scenario

ROOT = Path(__file__).resolve().parents[1]








def test_initial_one_down_ends_on_first_wrong_per_staircase_without_cross_talk():
    run = AdaptiveRun({
        0: StaircaseConfig(3, 1, 9, initial_one_down_limit=5),
        1: StaircaseConfig(3, 1, 9, initial_one_down_limit=5),
    }, 40)

    # First correct is immediately DOWN on staircase zero, regardless of 3-down later.
    assert run.initial_one_down_active(0)
    assert run.expected_step(0, True) == Step.DOWN
    assert run.respond(0, True, lambda step: 5 - (step == Step.DOWN))[0] == Step.DOWN
    assert run.states[0].initial_one_down_responses == 1
    assert run.initial_one_down_active(1)

    assert run.expected_step(0, False) == Step.UP
    assert run.respond(0, False, lambda step: 8)[0] == Step.UP
    assert run.states[0].initial_one_down_end_reason == "first_incorrect"
    assert not run.initial_one_down_active(0)
    assert run.initial_one_down_active(1)
    # Now THREE consecutive correct responses required to step DOWN on staircase 0.
    assert run.respond(0, True, lambda step: 8)[0] == Step.HOLD
    assert run.respond(0, True, lambda step: 8)[0] == Step.HOLD
    assert run.respond(0, True, lambda step: 7)[0] == Step.DOWN
    assert run.states[0].initial_one_down_responses == 2
    assert run.states[1].initial_one_down_responses == 0


def test_initial_one_down_cap_switches_to_requested_rule_on_next_response():
    run = AdaptiveRun({0: StaircaseConfig(2, 2, 10, initial_one_down_limit=2)}, 20)
    assert run.respond(0, True, lambda step: 4)[0] == Step.DOWN
    assert run.respond(0, True, lambda step: 3)[0] == Step.DOWN
    assert run.states[0].initial_one_down_end_reason == "response_limit"
    assert run.states[0].initial_one_down_responses == 2
    assert run.expected_step(0, True) == Step.HOLD
    assert run.respond(0, True, lambda step: 3)[0] == Step.HOLD
    assert run.respond(0, True, lambda step: 2)[0] == Step.DOWN


def test_first_incorrect_uses_selected_n_up_not_forced_one_up():
    run = AdaptiveRun({0: StaircaseConfig(3, 2, 10, initial_one_down_limit=5)}, 15)
    assert run.respond(0, False, lambda step: 8)[0] == Step.HOLD
    assert run.states[0].initial_one_down_end_reason == "first_incorrect"
    assert not run.initial_one_down_active(0)
    assert run.respond(0, False, lambda step: 9)[0] == Step.UP


def test_disabling_initial_one_down_retains_historical_rules():
    run = AdaptiveRun({0: StaircaseConfig(2, 1, 9, initial_one_down_limit=0)}, 20)
    assert not run.initial_one_down_active(0)
    assert run.respond(0, True, lambda step: 4)[0] == Step.HOLD
    assert run.respond(0, True, lambda step: 3)[0] == Step.DOWN


def test_failed_numeric_update_does_not_advance_introductory_state():
    run = AdaptiveRun({0: StaircaseConfig(3, 1, 9, initial_one_down_limit=5)}, 20)
    with pytest.raises(RuntimeError):
        run.respond(0, True, lambda step: (_ for _ in ()).throw(RuntimeError("update failed")))
    assert run.states[0].trial_count == 0
    assert run.states[0].initial_one_down_responses == 0
    assert run.initial_one_down_active(0)




