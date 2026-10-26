"""Source presets and active settings have distinct, strict provenance roles."""
import json
from pathlib import Path
import pytest
from simulations.run import simulate
from scripts.validate_run import validate_run


@pytest.mark.parametrize("method", ["adaptive", "constant_stimuli"])
def test_source_preset_is_preserved_but_cannot_hide_active_ceiling_corruption(tmp_path, method):
    artifact, _ = simulate(repo_root=Path(__file__).resolve().parents[1], data_root=tmp_path,
        experiment_id="example_experiment", analyse=False,
        values={"contrast_method": method, "trial_count": 4, "max_trials": 4,
                "fixed_contrasts": "0,0.1", "fixed_repetitions": 2})
    assert not [c for c in validate_run(artifact.run_directory) if not c.passed]
    resolution_path = artifact.run_directory / "resolved_experiment.json"
    resolution = json.loads(resolution_path.read_text())
    source = resolution["experiment_settings"]
    assert source["values"]["max_trials"] == source["document"]["values"]["max_trials"] == 1000
    assert source["values"]["contrast_method"] == "original"
    active_path = artifact.run_directory / "state/parameters.final.json"
    active = json.loads(active_path.read_text())
    active["max_trials"] = 5
    active_path.write_text(json.dumps(active), encoding="utf-8")
    def ceiling_check():
        return next(c for c in validate_run(artifact.run_directory)
                    if c.name == "Configured maximum accepted responses across configuration/state")
    assert not ceiling_check().passed and "disagree" in ceiling_check().detail
    active["max_trials"] = 4
    active_path.write_text(json.dumps(active), encoding="utf-8")
    resolution["experiment_settings"]["sha256"] = "invalid"
    resolution_path.write_text(json.dumps(resolution), encoding="utf-8")
    assert not ceiling_check().passed and "source preset hash" in ceiling_check().detail
