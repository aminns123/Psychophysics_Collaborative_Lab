"""All teaching studies can use adaptive and constant-stimuli strategies.

The original (non-adaptive) teaching procedures remain selectable unchanged.
No claimed psychometric thresholds are produced by these finite-count studies.
"""
from collections import Counter
import csv
import json
from pathlib import Path

import pytest

from psychophysics_lab.experiments import (
    orientation_adaptive, orientation_task,
    example_experiment, probe_above_below,
)
from psychophysics_lab.data.trials import TRIAL_COLUMNS


STUDIES = (
    orientation_adaptive, orientation_task,
    example_experiment, probe_above_below,
)


@pytest.mark.parametrize("study", STUDIES, ids=lambda s: s.SPEC.id)
def test_teaching_studies_declare_both_methods_and_keep_original_defaults(study):
    selected = study.SPEC
    fields = {field.key: field for field in selected.fields}
    assert {"adaptive", "constant_stimuli"} <= set(fields["contrast_method"].choices)
    assert callable(selected.method_planner)
    assert callable(study.procedure)
    assert callable(study.fixed_method)
    if study is orientation_adaptive:
        assert fields["contrast_method"].default == "adaptive"
    else:
        assert fields["contrast_method"].default == "original"
        assert "original" in fields["contrast_method"].choices
        assert callable(selected.method_reviewer)


@pytest.mark.parametrize("study", STUDIES, ids=lambda s: s.SPEC.id)
def test_fixed_teaching_conditions_and_target_balance(study):
    values = dict(study.SPEC.field_defaults())
    values.update(
        contrast_method="constant_stimuli",
        fixed_contrasts="0,0.1", fixed_repetitions=4,
    )
    values = study.SPEC.normalise_values(values)
    schedule = selected = study.SPEC.method_planner(values, 13)
    assert schedule == study.SPEC.method_planner(values, 13)
    assert len(schedule) == 8
    assert {row["contrast"] for row in schedule} == {0, .1}
    for strength in (0, .1):
        targets = Counter(row["target"] for row in schedule
                          if row["contrast"] == strength)
        assert targets == {0: 2, 1: 2}


@pytest.mark.parametrize("study", STUDIES, ids=lambda s: s.SPEC.id)
def test_teaching_fixed_method_rejects_malformed_levels_and_excess_count(study):
    values = dict(study.SPEC.field_defaults())
    for bad in ("", "nan", "inf", "-.1", ".1,.1", "not a number", ".1,,.2"):
        invalid = values | dict(contrast_method="constant_stimuli",
                                fixed_contrasts=bad)
        assert list(study.validate_method_settings(invalid))
    limit = values | dict(contrast_method="constant_stimuli",
                          fixed_contrasts=".1,.2",
                          fixed_repetitions=2, max_trials=3)
    assert "exceeding max_trials" in next(iter(study.validate_method_settings(limit)))


@pytest.mark.parametrize("name", [study.SPEC.id for study in STUDIES])
def test_teaching_constant_synthetic_uses_existing_saved_trial_schema(name, tmp_path):
    from simulations.registry import get_simulation
    from simulations.run import simulate
    root = Path(__file__).resolve().parents[1]
    config = dict(get_simulation(name).defaults)
    config.update(
        contrast_method="constant_stimuli",
        fixed_contrasts="0,0.1", fixed_repetitions=2,
    )
    artifact, analysis = simulate(
        data_root=tmp_path / name, repo_root=root, seed=12,
        experiment_id=name, values=config, analyse=True,
    )
    assert artifact.status == "completed"
    assert artifact.accepted_trials == 4
    assert analysis is None
    with artifact.trial_log_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 4
    assert tuple(rows[0]) == TRIAL_COLUMNS
    assert {float(row["presented_display_contrast"]) for row in rows} == {0, .1}
    for row in rows:
        for key in ("staircase_id", "staircase_trial_index", "reversal",
                    "reversal_count", "staircase_complete", "next_display_contrast"):
            assert row[key] == ""
    manifest = json.loads((artifact.run_directory / "manifest.json").read_text())
    assert manifest["trial_selection_method"] == "constant_stimuli"
    assert manifest["adaptive_algorithm"] is None
    assert not (artifact.run_directory / "adaptive_session.json").exists()
    resolution = json.loads((artifact.run_directory / "resolved_experiment.json").read_text())
    assert resolution["trial_selection_method"] == "constant_stimuli"
    assert len(resolution["schedule"]) == 4
    assert sum(v["accepted_trials"] for v in resolution["observed_level_accuracy"]) == 4


@pytest.mark.parametrize("name", ["orientation_task", "example_experiment", "probe_above_below"])
def test_teaching_adaptive_is_real_owned_staircase_without_threshold_claim(name, tmp_path):
    from simulations.registry import get_simulation
    from simulations.run import simulate
    root = Path(__file__).resolve().parents[1]
    values = dict(get_simulation(name).defaults)
    values.update(contrast_method="adaptive", starting_strength=0.2, trial_count=4)
    artifact, analysis = simulate(
        data_root=tmp_path / name, repo_root=root, seed=11,
        experiment_id=name, values=values, analyse=True,
    )
    assert artifact.status == "completed"
    assert artifact.accepted_trials == 4
    assert analysis is None
    with artifact.trial_log_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 4
    assert {r["staircase_id"] for r in rows} == {"0"}
    assert all(r["presented_display_contrast"] for r in rows)
    assert not (artifact.run_directory / "primary_thresholds.json").exists()


@pytest.mark.parametrize("name", ["orientation_task", "example_experiment", "probe_above_below"])
def test_original_teaching_default_still_executes(name, tmp_path):
    from simulations.run import simulate
    root = Path(__file__).resolve().parents[1]
    artifact, _ = simulate(
        data_root=tmp_path / name, repo_root=root, seed=12,
        experiment_id=name, analyse=False,
    )
    assert artifact.status == "completed"
    assert artifact.accepted_trials >= 1
    manifest = json.loads((artifact.run_directory / "manifest.json").read_text())
    assert manifest["adaptive_algorithm"] is None
    assert not (artifact.run_directory / "adaptive_session.json").exists()


@pytest.mark.parametrize("ceiling", [4, 17])
def test_orientation_finite_goal_and_recorded_safety_ceiling_are_distinct(tmp_path, ceiling):
    from simulations.run import simulate
    from scripts.validate_run import validate_run
    artifact, _ = simulate(
        repo_root=Path(__file__).resolve().parents[1], data_root=tmp_path / "runs",
        experiment_id="orientation_adaptive", seed=13, analyse=False,
        values={"trial_count": 4, "max_trials": ceiling},
    )
    assert artifact.status == "completed" and artifact.accepted_trials == 4
    from scripts.validate_run import leaves
    actions = json.loads((artifact.run_directory / "trial_actions.json").read_text())
    recorded = [value for key, value in leaves(actions) if key.endswith(".max_trials")]
    assert recorded and set(recorded) == {ceiling}
    assert not [check for check in validate_run(artifact.run_directory) if not check.passed]


def test_orientation_rejects_an_unreachable_finite_response_goal():
    with pytest.raises(ValueError, match="response safety ceiling"):
        orientation_adaptive.SPEC.normalise_values({"trial_count": 5, "max_trials": 4})
