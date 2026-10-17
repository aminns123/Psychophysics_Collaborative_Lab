"""Condition-list parity and introductory 1-down semantics, in real pipeline."""
from pathlib import Path
import csv
import json

import pytest

from psychophysics_lab.adaptive.staircase import AdaptiveRun, StaircaseConfig, Step
from psychophysics_lab._reference_csf.experiment_definition import (
    parse_condition_values, CSF_SPEC
)
from simulations.csf import DEFAULT_VALUES
from simulations.run import simulate
from simulations.scenarios import run_scenario

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("entered,expected", [
    ("63,126,252", (63.,126.,252.)),
    (" 2.5 , 20 ", (2.5,20.)),
    ("1", (1.,)),
])
def test_strict_condition_list_parser(entered,expected):
    assert parse_condition_values(entered) == expected


@pytest.mark.parametrize("entered", [
    "", "1,", ",1", "1,,2", "1,1", "1,1.0", "nan", "inf", "-1", "0",
    "abc", "1;2", "1e99",
])
def test_condition_list_rejects_invalid_nonfinite_duplicate_or_empty(entered):
    with pytest.raises(ValueError):
        parse_condition_values(entered)


def test_explicit_condition_count_must_equal_list_and_preserve_order():
    spec = CSF_SPEC
    base = dict(DEFAULT_VALUES, number_conditions=3, condition_values="252,63,126",
                staircases_per_condition=2)
    normal = spec.normalise_values(base)
    assert normal["number_conditions"] == 3
    assert normal["condition_values"] == "252,63,126"
    human = spec.build_legacy_setup(
        participant_id="PTEST", values=normal, monitor_profile=__import__(
            "psychophysics_lab.config.monitor", fromlist=["load_monitor_profiles"]
        ).load_monitor_profiles(ROOT)["legacy_reference_display"],
    )
    assert human["number_conditions"] == 3
    assert human["condition_values"] == "252,63,126"
    with pytest.raises(ValueError, match="Number of conditions"):
        spec.normalise_values(dict(base, number_conditions=2))


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


def test_headless_pipeline_records_selected_conditions_and_initial_phase(tmp_path):
    data = tmp_path / "external_data"
    artifacts, analysis = simulate(
        data_root=data, repo_root=ROOT, seed=77,
        values={"number_conditions":3, "condition_values":"63,126,252",
                "staircases_per_condition":2, "initial_one_down_limit":4,
                "max_trials":160, "reversal_termination":3},
    )
    run = artifacts.run_directory
    with (run/"trials.tsv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    assert rows
    config = json.loads((run/"experiment_config.json").read_text())
    vals = config["normalised_experiment_values"]
    assert vals["condition_values"] == "63,126,252"
    assert vals["number_conditions"] == 3
    assert vals["initial_one_down_limit"] == 4
    runtime = json.loads((run/"state"/"conditions.final.json").read_text())
    assert runtime["condition_list"] == [63.,126.,252.]*2
    session = json.loads((run/"adaptive_session.json").read_text())
    assert len(session["staircases"]) == 6
    assert {str(row["stimulus_condition"]) for row in rows} == {"63.0","126.0","252.0"}
    for staircase in session["staircases"].values():
        assert staircase["config"]["initial_one_down_limit"] == 4
        assert staircase["initial_one_down_responses"] <= 4
    assert (run/"analysis"/"staircases.png").is_file()


def test_named_scenario_same_fields_and_reports_are_local(tmp_path):
    result = run_scenario(
        experiment_id="contrast_sensitivity", scenario_id="csf_short_censored",
        data_root=tmp_path/"data", repo_root=ROOT, seeds=(53,),
        experiment_values={"number_conditions":1, "condition_values":"63",
                           "staircases_per_condition":3, "initial_one_down_limit":2},
    )
    assert result.passed
    run = result.runs[0].artifacts.run_directory
    config = json.loads((run/"experiment_config.json").read_text())
    assert config["normalised_experiment_values"]["number_conditions"] == 1
    assert config["normalised_experiment_values"]["staircases_per_condition"] == 3
    assert (run/"scenario_report.json").is_file()
