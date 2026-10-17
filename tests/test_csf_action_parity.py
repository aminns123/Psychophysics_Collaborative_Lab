"""CSF action-state replay against immutable legacy fixtures, not renderer parity."""
import csv
import json
from pathlib import Path
import pytest
from simulations.csf_actions import capture_legacy, replay, compare, BASIS
from psychophysics_lab.analysis.thresholds import analyse_thresholds

FIXTURES = Path(__file__).parent / "fixtures/csf_actions"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_legacy_capture_and_public_actions_match_scientific_fixtures(tmp_path, path):
    expected = json.loads(path.read_text())
    current_legacy = capture_legacy(expected["case"], tmp_path / "legacy")
    assert current_legacy == expected
    rows, snapshots = replay(expected, tmp_path / "actions")
    compare(expected, rows, snapshots)
    trace = json.loads((tmp_path / "actions/trial_actions.json").read_text())
    assert all(t["presentation_basis"] == BASIS for t in trace["trials"])
    assert all([e["name"] for e in t["events"] if e["kind"] in {"show", "response"}] ==
               ["fixation", "new_condition", "stimuli", "interval", "response"] for t in trace["trials"])
    assert all(not any("software_onset_s" in e for e in t["events"]) for t in trace["trials"])
    if path.stem == "response_ceiling":
        assert snapshots[-1]["status"] == "max_trials_reached"
    if path.stem == "reversal_completion":
        assert snapshots[-1]["status"] == "completed"


def test_threshold_analyser_agrees_for_legacy_and_action_state_rows(tmp_path):
    expected = json.loads((FIXTURES / "reversal_completion.json").read_text())
    actual, _ = replay(expected, tmp_path / "actions")
    thresholds = []
    for name, rows in (("captured_legacy", expected["rows"]), ("action_state_projection", actual)):
        root = tmp_path / name
        root.mkdir()
        (root / "manifest.json").write_text(json.dumps({
            "status": "completed", "experiment_id": "contrast_sensitivity",
            "participant_id": "synthetic_validation", "data_kind": "synthetic",
        }))
        with (root / "trials.tsv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        result = analyse_thresholds(data_root=tmp_path, run_directory=root, create_plot=False)
        thresholds.append(result.staircase_thresholds)
    assert thresholds[0] == thresholds[1]


def test_development_replay_is_not_human_catalogue_or_replacement_csf():
    from psychophysics_lab.experiments.registry import list_experiments, get_experiment
    assert "csf_state_validation" not in {s.id for s in list_experiments()}
    original = get_experiment("contrast_sensitivity")
    assert original.procedure is None
    assert original.legacy_module == "psychophysics_lab._reference_csf.contrast_sensitivity_function"
