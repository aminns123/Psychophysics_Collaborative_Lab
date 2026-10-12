"""End-to-end guarantees for self-contained CSF human/synthetic run figures."""
import csv
import json
from pathlib import Path

import pytest

from simulations.run import simulate
from simulations.scenarios import run_scenario
from psychophysics_lab.analysis.previews import create_staircase_preview, latest_staircase_plot
from psychophysics_lab.analysis.thresholds import analyse_thresholds
from psychophysics_lab.experiments.registry import get_experiment
from psychophysics_lab.config.models import SetupRequest

ROOT = Path(__file__).resolve().parents[1]


def test_multiple_independent_staircases_per_condition_and_nonempty_dynamic_plot(tmp_path):
    root = tmp_path / "local_psychophysics_data"
    run, _ = simulate(
        data_root=root, repo_root=ROOT, seed=17,
        values={"staircases_per_condition": 3, "max_trials": 120, "reversal_termination": 3},
    )
    directory = run.run_directory
    source = json.loads((directory / "state" / "conditions.runtime.json").read_text())
    assert source["condition_list"] == [63.0, 252.0] * 3
    assert source["staircase_Identities"] == [0, 1, 2, 3, 4, 5]
    metadata = json.loads((directory / "adaptive_session.json").read_text())
    assert set(metadata["staircases"]) == {str(i) for i in range(6)}
    assert len({id(state) for state in metadata["staircases"].values()}) == 6

    picture = directory / "analysis" / "staircases.png"
    assert picture.is_file()
    assert picture.stat().st_size > 3_000
    with (directory / "trials.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    seen = {(row["stimulus_condition"], row["staircase_id"]) for row in rows}
    assert len(seen) == 6
    summary = json.loads((directory / "analysis" / "staircase_preview.json").read_text())
    assert summary["condition_staircase_counts"] == {"63.0": 3, "252.0": 3}
    assert summary["staircases_plotted"] == 6
    assert sum(int(row["correct"]) for row in rows) > 0
    assert summary["plotted_accepted_trials"] == len(rows)
    assert latest_staircase_plot(data_root=root, run_directory=directory) == picture


def test_scenario_report_trials_and_images_cohabit_same_run(tmp_path):
    root = tmp_path / "local_psychophysics_data"
    output = run_scenario(
        experiment_id="contrast_sensitivity", scenario_id="csf_baseline",
        data_root=root, repo_root=ROOT, seeds=(123,),
        experiment_values={"staircases_per_condition": 2, "max_trials": 150},
    )
    assert output.passed
    directory = output.runs[0].artifacts.run_directory
    assert output.report_file == directory / "scenario_report.json"
    report = json.loads(output.report_file.read_text())
    assert report["experiment_values"]["staircases_per_condition"] == 2
    assert (directory / "manifest.json").is_file()
    assert (directory / "adaptive_session.json").is_file()
    assert (directory / "trials.tsv").is_file()
    assert (directory / "analysis" / "staircases.png").is_file()
    assert (root / report["runs"][0]["staircase_plot"]) == directory / "analysis" / "staircases.png"
    assert (directory / "analysis" / "threshold_vs_condition.png").is_file()
    assert report["runs"][0]["threshold_plot"] is not None
    assert (root / report["runs"][0]["threshold_plot"]).is_relative_to(directory)
    assert not (root / "simulation_reports").exists()


def test_multiple_seeds_each_get_own_scenario_report(tmp_path):
    root = tmp_path / "local_psychophysics_data"
    result = run_scenario(
        experiment_id="contrast_sensitivity", scenario_id="csf_shifted_preference",
        data_root=root, repo_root=ROOT, seeds=(41, 42),
        experiment_values={"max_trials": 100},
    )
    assert len(result.runs) == 2
    for case in result.runs:
        report = case.artifacts.run_directory / "scenario_report.json"
        assert report.is_file()
        assert json.loads(report.read_text())["seeds"] == [41, 42]
        assert (case.artifacts.run_directory / "trials.tsv").is_file()


def test_staircase_instance_count_is_registered_and_validated_for_both_modes():
    spec = get_experiment("contrast_sensitivity")
    assert "staircases_per_condition" in {field.key for field in spec.fields}
    assert "staircases_per_condition" in spec.adaptive.controls
    assert spec.normalise_values({"staircases_per_condition": 4})["staircases_per_condition"] == 4
    for number in (0, 25):
        with pytest.raises(ValueError, match="Staircases per condition"):
            spec.normalise_values({"staircases_per_condition": number})


def test_human_finalisation_generates_staircases_from_actual_canonical_records(tmp_path, monkeypatch):
    from psychophysics_lab.core.runner import run_request
    from psychophysics_lab.data.trials import TrialLog
    import Experiments.contrast_sensitivity_function as legacy

    root = tmp_path / "local_psychophysics_data"

    def fake_human_study(conditions_path, parameters_path, response_path, state_dir):
        path = Path(response_path).parent / "trials.tsv"
        for trial_index, correct in enumerate((True, False, True), 1):
            TrialLog(path).append({
                "trial_index": trial_index, "staircase_id": 0,
                "staircase_trial_index": trial_index, "stimulus_condition": 63.0,
                "presented_display_contrast": .1 / trial_index,
                "next_display_contrast": .1 / (trial_index + 1),
                "reversal": int(trial_index == 3), "correct": int(correct),
            })

    monkeypatch.setattr(legacy, "run_experiment", fake_human_study)
    artifacts = run_request(
        SetupRequest("H001", "new", "contrast_sensitivity", "legacy_reference_display",
                     {"max_trials": 10}), repo_root=ROOT, data_root=root,
    )
    assert artifacts.accepted_trials == 3
    assert (artifacts.run_directory / "trials.tsv").is_file()
    assert (artifacts.run_directory / "analysis" / "staircases.png").is_file()
    assert (artifacts.run_directory / "analysis" / "threshold_vs_condition.png").is_file()


def test_reanalysis_stays_in_the_same_run_and_never_changes_raw_trials(tmp_path):
    root = tmp_path / "local_psychophysics_data"
    artifacts, _ = simulate(data_root=root, repo_root=ROOT, seed=18, values={"max_trials": 100})
    run = artifacts.run_directory
    before = (run / "trials.tsv").read_bytes()
    old = analyse_thresholds(data_root=root, run_directory=run, last_n_reversals=2)
    new = analyse_thresholds(data_root=root, run_directory=run, last_n_reversals=3)
    assert old.output_directory != new.output_directory
    assert old.output_directory.is_relative_to(run / "analysis" / "thresholds")
    assert new.output_directory.is_relative_to(run / "analysis" / "thresholds")
    assert (run / "analysis" / "threshold_vs_condition.png").is_file()
    assert (run / "trials.tsv").read_bytes() == before
