"""Public procedures use the real configure/save/finalise/validate pipeline."""
import json
from dataclasses import replace
from pathlib import Path
import pytest
from psychophysics_lab.researcher import experiment
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.core.synthetic import SimulationRun
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.preflight import validate_setup, human_blockers
from psychophysics_lab.experiments._internal import registry
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def make_spec(procedure, **changes):
    return experiment(id="public_task", name="Public task", description="Lifecycle regression",
        procedure=procedure, calibration_requirements=("geometry", "luminance", "timing"),
        monitor_capabilities=("display_binding", "resolution"), **changes)


def run_procedure(tmp_path, monkeypatch, procedure):
    monkeypatch.setitem(registry._REGISTRY, "public_task", make_spec(procedure))
    data = tmp_path / "data"
    simulation = SimulationRun(data, {"seed": 123, "physical_display_used": False}, lambda *args: None)
    return run_request(SetupRequest("synthetic_123", "new", "public_task", "legacy_reference_display", {}),
        repo_root=ROOT, data_root=data, simulation=simulation)


def initialise(run):
    run.initialise(expected_trials=2, resolution={"stimulus_id": "test", "task": "two responses"})


def record(run):
    run.record(stimulus_condition="left", target_alternative=0, participant_response=0,
               response_key="LEFT", correct=1)


@pytest.mark.parametrize("outcome", ["completed", "aborted_by_user", "error", "empty", "premature"])
def test_public_lifecycle_preserves_truth_and_artifacts(tmp_path, monkeypatch, outcome):
    def procedure(run):
        if outcome == "empty":
            return
        initialise(run)
        record(run)
        if outcome == "aborted_by_user":
            run.abort("Participant pressed Escape")
        if outcome == "error":
            run.fail("Renderer disconnected")
        if outcome == "premature":
            run.complete()
        record(run)
        run.complete()
    if outcome in {"error", "empty", "premature"}:
        with pytest.raises((ValueError, RuntimeError)):
            run_procedure(tmp_path, monkeypatch, procedure)
        directory = next((tmp_path / "data").rglob("manifest.json")).parent
        assert json.loads((directory / "manifest.json").read_text())["status"] == "error"
        assert (directory / "trials.tsv").exists()
    else:
        result = run_procedure(tmp_path, monkeypatch, procedure)
        directory = result.run_directory
        assert result.status == outcome
    if outcome != "empty":
        checks = validate_run(directory)
        assert all(check.passed for check in checks), [check for check in checks if not check.passed]


def test_declarations_cannot_accidentally_omit_calibration():
    args = dict(id="bad", name="Bad", description="Bad", procedure=lambda run: None)
    with pytest.raises(ValueError, match="calibration_requirements"):
        experiment(**args, monitor_capabilities=())
    with pytest.raises(ValueError, match="monitor_capabilities"):
        experiment(**args, calibration_not_applicable="No visual presentation")
    spec = experiment(**args, calibration_not_applicable="No visual presentation", monitor_capabilities=())
    with pytest.raises(ValueError, match="Unknown experiment calibration"):
        replace(spec, calibration_not_applicable="", calibration_requirements=("typo",))


def test_required_calibration_blocks_reference_profile_only_for_humans():
    spec = make_spec(lambda run: None)
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    request = SetupRequest("S001", "new", spec.id, profile.id, {})
    assert human_blockers(spec, profile)
    with pytest.raises(ValueError, match="Human acquisition blocked"):
        validate_setup(request, spec, profile)
    assert validate_setup(request, spec, profile, mode="simulation")
