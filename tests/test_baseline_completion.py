"""Release audit: complete real saved staircases; independent numerical oracle.

No frozen references are regenerated. Synthetic observers check software, not
human psychometrics or a display. Data remain in pytest's disposable workspace.
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean, median

import pytest

from psychophysics_lab.data.reader import load_run
from psychophysics_lab.experiments._internal.registry import get_experiment
from simulations.registry import TeachingObserver
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = (
    "contrast_sensitivity", "contrast_sensitivity_windowed", "line_position_baseline",
    "line_position_flanker", "ellipse_centre", "ellipse_major_axis",
    "orientation_adaptive", "orientation_task", "probe_above_below", "example_experiment",
)
CASES = [(identity, method, seed) for identity in OFFICIAL
         for method in (("adaptive", "constant_stimuli", "original")
                        if identity in {"orientation_task", "probe_above_below", "example_experiment"}
                        else ("adaptive", "constant_stimuli"))
         for seed in (1729, 2**53 + 121, 2**63 - 17)]


def settings(identity, method, seed):
    background = .35 if seed == 1729 else .72
    candidate = {
        "contrast_method": method, "max_trials": 1024, "trial_count": 8,
        "fixed_contrasts": "0,.012,.04", "fixed_repetitions": 4,
        "background_intensity": background, "starting_contrast": .05,
        "starting_probe_intensity": background + .02, "starting_strength": .07,
        "staircases_per_condition": 2, "frequencies_cpd": "2,5",
        "positions_deg": "-.15,.25", "aspect_ratios": ".65,.9",
        "probe_vertical_offset_deg": .3, "flanker_cpd": 3., "ring_increment": .025,
        "n_down": 2, "n_up": 1, "initial_one_down_limit": 0,
        "reversal_termination": 4, "threshold_reversals": 2,
        "logUNIT_UP": .21, "logUNIT_DW": .13,
        "down_factor": .7, "up_factor": 1.4,
    }
    defaults = get_experiment(identity).field_defaults()
    return {key: value for key, value in candidate.items() if key in defaults}


def read_json(run, name):
    return json.loads((run / name).read_text(encoding="utf-8"))


def assert_independent_primary(rows, primary):
    """Derive movement turns and reducers from accepted observations alone."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["staircase_id"]].append(row)
    estimates = {}
    rule = primary["primary_estimator"]
    for identity, history in grouped.items():
        last_direction, reversal_count, correct_streak = 0, 0, 0
        turns = []
        for index, row in enumerate(history):
            assert int(row["staircase_trial_index"]) == index + 1
            assert int(row["correct"]) == (row["target_alternative"] == row["participant_response"])
            before, after = map(float, (row["presented_display_contrast"], row["next_display_contrast"]))
            if index:
                assert before == float(history[index - 1]["next_display_contrast"])
            correct_streak = correct_streak + 1 if row["correct"] == "1" else 0
            requested = 1 if row["correct"] == "0" else (-1 if correct_streak == 2 else 0)
            if correct_streak == 2:
                correct_streak = 0
            # A clipped update may hold; a hold must not fabricate a turn.
            direction = (after > before) - (after < before)
            assert direction in (0, requested)
            turn = bool(direction and last_direction and direction != last_direction)
            if direction:
                last_direction = direction
            if turn:
                reversal_count += 1
                turns.append(before)
            assert int(row["reversal"]) == turn
            assert int(row["reversal_count"]) == reversal_count
        assert history[-1]["staircase_complete"] == "1"
        assert reversal_count == 4
        retained = turns[-2:]
        if rule["within_staircase"] == "median":
            expected = median(retained)
        else:
            assert rule["within_staircase"] == "geometric_mean"
            expected = math.sqrt(retained[0] * retained[1])
        estimates[identity] = expected
        assert primary["staircase_thresholds"][identity] == pytest.approx(expected, rel=1e-12)
    assert not primary["excluded_staircases"]
    for condition, identities in primary["expected_staircases"].items():
        expected = fmean(estimates[str(identity)] for identity in identities)
        actual = primary["condition_thresholds"][condition]
        assert actual["threshold"] == pytest.approx(expected, rel=1e-12)
        assert actual["sensitivity"] == pytest.approx(1 / expected, rel=1e-12)


@pytest.mark.parametrize("identity,method,seed", CASES)
def test_completed_official_method_matrix(tmp_path, identity, method, seed):
    values = settings(identity, method, seed)
    artifact, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id=identity,
                           values=values, seed=seed, observer=TeachingObserver(.65), analyse=False)
    run = artifact.run_directory
    assert artifact.status == "completed", (identity, method, artifact.status)
    with artifact.trial_log_file.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert len(rows) == artifact.accepted_trials > 0
    assert len(load_run(run)["trials"]["trial_index"]) == len(rows)
    assert all(check.passed for check in validate_run(run)), validate_run(run)
    manifest = read_json(run, "manifest.json")
    assert manifest["data_kind"] == "synthetic" and manifest["simulation"]["seed"] == seed
    assert all(int(r["correct"]) == (r["target_alternative"] == r["participant_response"]) for r in rows)
    if method == "constant_stimuli":
        counts = Counter((r["stimulus_condition"], float(r["presented_display_contrast"])) for r in rows)
        assert set(counts.values()) == {4}
        assert {level for _, level in counts} == {0., .012, .04}
        balance = Counter((r["stimulus_condition"], r["presented_display_contrast"], r["target_alternative"]) for r in rows)
        assert set(balance.values()) == {2}
        assert all(r["staircase_id"] == r["reversal_count"] == "" for r in rows)
    elif (run / "primary_thresholds.json").exists():
        assert_independent_primary(rows, read_json(run, "primary_thresholds.json"))
    # The two-stage saved event journal must agree with the durable trial file.
    journal = [json.loads(line) for line in (run / "trial_events.jsonl").read_text().splitlines()]
    assert len(journal) == len(rows)
    for row, event in zip(rows, journal):
        response = next(item["response"] for item in event["trial"]["events"] if item["kind"] == "response")
        assert response["alternative"] == int(row["participant_response"])
        assert response["correct"] == bool(int(row["correct"]))
    if seed == 1729:
        repeated, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id=identity,
                               values=values, seed=seed, observer=TeachingObserver(.65), analyse=False)
        assert repeated.run_directory != run
        assert repeated.trial_log_file.read_bytes() == artifact.trial_log_file.read_bytes()
    if (run / "primary_thresholds.json").exists():
        from psychophysics_lab.analysis.thresholds import analyse_thresholds
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}
        derived = analyse_thresholds(data_root=tmp_path / "data", run_directory=run, create_plot=False)
        assert derived.condition_thresholds
        assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}
