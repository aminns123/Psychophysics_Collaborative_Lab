"""Every DetectionScene study supports both methods and the same local TSV.

No change to the established adaptive callbacks or human calibration rules.
"""
from collections import Counter
import csv
import json
from pathlib import Path

import pytest

from psychophysics_lab.experiments import (
    line_position_baseline, line_position_flanker,
    ellipse_centre, ellipse_major_axis,
)
from psychophysics_lab.methods.probe import (
    fixed_contrast_levels, make_probe_fixed_schedule,
    unique_probe_conditions,
)
from psychophysics_lab.data.trials import TRIAL_COLUMNS


STUDIES = (
    line_position_baseline,
    line_position_flanker,
    ellipse_centre,
    ellipse_major_axis,
)


def valid_values(study, *, method="constant_stimuli"):
    values = dict(study.SPEC.field_defaults())
    # Some research-critical inputs deliberately have no original default.
    # These are disposable scientific test conditions, not new defaults.
    for key, value in (
        ("probe_vertical_offset_deg", 0.3),
        ("flanker_cpd", 2.0),
        ("ring_increment", 0.05),
    ):
        if key in values and values[key] is None:
            values[key] = value
    values.update(
        contrast_method=method, fixed_contrasts="0,0.01",
        fixed_repetitions=2,
    )
    return study.SPEC.normalise_values(values)


@pytest.mark.parametrize("study", STUDIES, ids=lambda study: study.SPEC.id)
def test_both_methods_are_declared_and_old_adaptive_default_is_preserved(study):
    keys = {field.key: field for field in study.SPEC.fields}
    assert keys["contrast_method"].choices == ("adaptive", "constant_stimuli")
    assert keys["contrast_method"].default == "adaptive"
    assert callable(study.SPEC.method_planner)
    adaptive = valid_values(study, method="adaptive")
    fixed = valid_values(study)
    assert adaptive["contrast_method"] == "adaptive"
    assert fixed["contrast_method"] == "constant_stimuli"
    assert callable(study.adaptive_contrast_method)
    assert callable(study.constant_contrast_method)


@pytest.mark.parametrize("study", STUDIES, ids=lambda study: study.SPEC.id)
def test_fixed_trial_schedule_deduplicates_adaptive_staircases(study):
    values = valid_values(study)
    unique = unique_probe_conditions(study.make_conditions(values))
    plan = study.SPEC.method_planner(values, 9)
    assert len(plan) == len(unique) * 2 * 2
    assert plan == study.SPEC.method_planner(values, 9)
    assert {v["contrast"] for v in plan} == {0.0, 0.01}
    cells = Counter((row["value"], row["contrast"]) for row in plan)
    assert set(cells.values()) == {2}
    for key in cells:
        targets = Counter(t["target"] for t in plan
                          if (t["value"], t["contrast"]) == key)
        assert targets == {0: 1, 1: 1}
    assert fixed_contrast_levels(values) == (0, 0.01)


@pytest.mark.parametrize("study", STUDIES, ids=lambda study: study.SPEC.id)
def test_fixed_contrast_rejects_invalid_or_unaffordable_levels(study):
    values = valid_values(study)
    for text in ("nan", "inf", "1.0", "-0.1", "0.1,,0.2", "0.02,0.02"):
        invalid = dict(values, fixed_contrasts=text)
        assert list(study.validate_settings(invalid))
    with pytest.raises(ValueError, match="max_trials"):
        study.SPEC.method_planner(dict(values, max_trials=1), 9)


@pytest.mark.parametrize("name", [study.SPEC.id for study in STUDIES])
def test_real_synthetic_fixed_probe_data_contract(name, tmp_path):
    from simulations.registry import get_simulation
    from simulations.run import simulate
    from scripts.validate_run import validate_run

    root = Path(__file__).resolve().parents[1]
    config = dict(get_simulation(name).defaults)
    config.update(contrast_method="constant_stimuli",
                  fixed_contrasts="0,0.01", fixed_repetitions=2)
    for key, value in (
        ("probe_vertical_offset_deg", 0.3),
        ("flanker_cpd", 2.0),
        ("ring_increment", 0.05),
    ):
        if key in config and config[key] is None:
            config[key] = value
    artifact, analysis = simulate(
        data_root=tmp_path / name, repo_root=root, seed=8,
        experiment_id=name, values=config, analyse=True,
    )
    assert artifact.status == "completed"
    assert analysis is None
    assert artifact.accepted_trials > 0
    with artifact.trial_log_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == artifact.accepted_trials
    assert tuple(rows[0]) == TRIAL_COLUMNS
    assert {float(row["presented_display_contrast"]) for row in rows} == {0.0, 0.01}
    for row in rows:
        for key in ("staircase_id", "staircase_trial_index", "reversal",
                    "reversal_count", "next_display_contrast", "staircase_complete"):
            assert row[key] == ""
    manifest = json.loads((artifact.run_directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["trial_selection_method"] == "constant_stimuli"
    assert manifest["adaptive_algorithm"] is None
    assert not (artifact.run_directory / "adaptive_session.json").exists()
    resolved = json.loads((artifact.run_directory / "resolved_experiment.json").read_text(encoding="utf-8"))
    assert resolved["trial_selection_method"] == "constant_stimuli"
    assert len(resolved["schedule"]) == artifact.accepted_trials
    bad = [r for r in validate_run(artifact.run_directory) if not r.passed]
    assert not bad, [(r.name, r.detail) for r in bad]
