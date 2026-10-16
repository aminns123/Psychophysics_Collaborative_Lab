import importlib.util
import json
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
from psychophysics_lab.config.stimulus_parameters import load_parameters, save_parameter_preset, resolve_stimuli
from psychophysics_lab.stimuli.registry import get_stimulus, list_stimuli, register_stimulus
from psychophysics_lab.experiments.registry import get_experiment, register_experiment
from psychophysics_lab.core.presentation import render_pixels
from psychophysics_lab.scaffold import scaffold
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("identity", ["orientation_task", "orientation_adaptive"])
def test_independent_tasks_use_public_pipeline_and_validate(tmp_path, identity):
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id=identity,
                            values={"trial_count": 4, "response_keys": "LEFT,RIGHT"})
    assert artifacts.status == "completed" and artifacts.accepted_trials == 4
    checks = validate_run(artifacts.run_directory)
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]
    trials = json.loads((artifacts.run_directory / "trial_presentations.json").read_text())["trials"]
    assert len(trials) == 4 and all(t["reaction_time_s"] > 0 for t in trials)
    if identity == "orientation_adaptive":
        history = json.loads((artifacts.run_directory / "adaptive_history.json").read_text())
        assert len(history["updates"]) == 4


def test_all_defaults_validate_and_preset_edits_change_renderer(tmp_path):
    for stimulus in list_stimuli():
        load_parameters(ROOT / stimulus.default_config, stimulus)
    stimulus = get_stimulus("teaching_gabor")
    selected = load_parameters(ROOT / stimulus.default_config, stimulus)
    original = render_pixels(stimulus, selected["document"]["parameters"])
    selected["document"]["parameters"]["orientation_deg"] = 60.
    path = save_parameter_preset(tmp_path, "sixty", stimulus, selected["document"])
    changed = load_parameters(path, stimulus)
    assert not np.array_equal(original, render_pixels(stimulus, changed["document"]["parameters"]))
    with pytest.raises(FileExistsError):
        save_parameter_preset(tmp_path, "sixty", stimulus, selected["document"])
    selected["document"]["parameters"]["contrast"] = 2
    path.write_text(json.dumps(selected["document"]))
    with pytest.raises(ValueError, match="range"):
        load_parameters(path, stimulus)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scaffold_register_configure_simulate_save_validate(tmp_path, monkeypatch):
    from psychophysics_lab.stimuli import registry as stimuli
    from psychophysics_lab.experiments import registry as experiments
    monkeypatch.setattr(stimuli, "_REGISTRY", dict(stimuli._REGISTRY))
    monkeypatch.setattr(experiments, "_REGISTRY", dict(experiments._REGISTRY))
    files = scaffold(tmp_path, "student_grating", kind="stimulus")
    stimulus = load_module(files[0], "student_grating").SPEC
    register_stimulus(stimulus)
    with pytest.raises(ValueError, match="already"):
        register_stimulus(stimulus)
    document = json.loads(files[1].read_text())
    document["parameters"]["line_width_deg"] = 0.25
    files[1].write_text(json.dumps(document))
    selected = load_parameters(files[1], stimulus)
    # Example 1: a new line stimulus runs in the existing compatible example.
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id="example_experiment",
        values={"trial_count": 3}, stimulus_snapshots={"target": selected})
    assert all(c.passed for c in validate_run(artifacts.run_directory))
    before = (artifacts.run_directory / "stimulus_parameters.json").read_bytes()
    files[1].write_text("invalid later edit")
    assert (artifacts.run_directory / "stimulus_parameters.json").read_bytes() == before
    # Example 2: a generated experiment reuses an existing registered stimulus.
    experiment_file, timeline_file = scaffold(tmp_path, "student_task", kind="experiment")
    assert timeline_file.name == "student_task.json"
    spec = load_module(experiment_file, "student_task").SPEC
    # This isolated test supplies generated source in its own checkout root.
    register_experiment(replace(spec, source_paths=()))
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id=spec.id, values={"trial_count": 2})
    assert all(c.passed for c in validate_run(artifacts.run_directory))


@pytest.mark.parametrize("change", [lambda d: d["parameters"].pop("contrast"),
    lambda d: d["parameters"].update(unknown=3), lambda d: d["parameters"].update(contrast="0.2"),
    lambda d: d.update(stimulus_id="wrong")])
def test_invalid_json_never_silently_defaults(tmp_path, change):
    stimulus = get_stimulus("teaching_gabor")
    document = json.loads((ROOT / stimulus.default_config).read_text())
    change(document)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        load_parameters(path, stimulus)


def test_multiple_slots_and_offline_simulation(tmp_path, monkeypatch):
    import socket
    from psychophysics_lab.experiments import registry
    from psychophysics_lab.config.stimulus_parameters import document_for, snapshot
    monkeypatch.setattr(registry, "_REGISTRY", dict(registry._REGISTRY))
    def procedure(run):
        run.initialise(expected_trials=2, resolution={"task": "two separately configured patches"})
        for slot in ("target", "comparison"):
            run.present(slot=slot, target=0, condition=slot)
        run.complete()
    base = get_experiment("orientation_task")
    spec = replace(base, id="two_patches", procedure=procedure, source_paths=(),
        stimulus_slots={"target": "orientation_patch", "comparison": "orientation_patch"},
        stimulus_defaults={"target": "teaching_gabor", "comparison": "teaching_gabor"})
    register_experiment(spec)
    stimulus = get_stimulus("teaching_gabor")
    target = document_for(stimulus)
    comparison = document_for(stimulus, target["parameters"] | {"orientation_deg": 70.})
    snapshots = {"target": snapshot(target, file_identity="target.json"),
                 "comparison": snapshot(comparison, file_identity="comparison.json")}
    def no_network(*args, **kwargs):
        raise AssertionError("Teaching simulation must not access the network")
    monkeypatch.setattr(socket, "create_connection", no_network)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path/"data", experiment_id=spec.id, stimulus_snapshots=snapshots)
    trials = json.loads((artifacts.run_directory/"trial_presentations.json").read_text())["trials"]
    assert [row["parameters"]["orientation_deg"] for row in trials] == [30., 70.]
    assert all(c.passed for c in validate_run(artifacts.run_directory))
    # Detect malformed custom observations even if someone removes output hashes.
    payload = json.loads((artifacts.run_directory/"trial_presentations.json").read_text())
    payload["trials"][0]["reaction_time_s"] = -1
    (artifacts.run_directory/"trial_presentations.json").write_text(json.dumps(payload))
    assert any(not c.passed and c.name.startswith("Stimulus configuration") for c in validate_run(artifacts.run_directory))


def test_adaptive_blueprint_registers_through_contribution_list_and_runs(tmp_path, monkeypatch):
    import sys
    from psychophysics_lab import contributions
    from psychophysics_lab.experiments import contributions as loader, registry
    from psychophysics_lab.adaptive import registry as algorithms, AdaptiveSelection
    from psychophysics_lab.stimuli import registry as stimuli
    for module in (registry, algorithms, stimuli):
        monkeypatch.setattr(module, "_REGISTRY", dict(module._REGISTRY))
    path, = scaffold(tmp_path, "student_step", kind="adaptive")
    module = load_module(path, "student_step")
    monkeypatch.setitem(sys.modules, "student_step", module)
    monkeypatch.setattr(contributions, "ADAPTIVE_MODULES", ("student_step",))
    monkeypatch.setattr(contributions, "EXPERIMENT_MODULES", ())
    monkeypatch.setattr(contributions, "STIMULUS_MODULES", ())
    monkeypatch.setattr(loader, "_loaded", False)
    loader.load_contributions()
    assert algorithms.get_algorithm("student_step") is module.SPEC
    spec = replace(get_experiment("orientation_adaptive"), id="student_adaptive", adaptive=AdaptiveSelection("student_step"))
    register_experiment(spec)
    result, _ = simulate(repo_root=ROOT, data_root=tmp_path/"data", experiment_id=spec.id, values={"trial_count": 3})
    assert result.status == "completed"
    assert all(c.passed for c in validate_run(result.run_directory))
    history = json.loads((result.run_directory/"adaptive_history.json").read_text())
    assert history["algorithm_id"] == "student_step" and len(history["updates"]) == 3


def test_selected_stimulus_requirements_cannot_be_removed_by_experiment(tmp_path, monkeypatch):
    from psychophysics_lab.stimuli import registry as stimuli
    from psychophysics_lab.config.preflight import validate_setup
    from psychophysics_lab.config.human_readiness import experiment_readiness
    from psychophysics_lab.config.models import SetupRequest
    from psychophysics_lab.config.stimulus_parameters import document_for, snapshot
    from test_calibration_review_completion import fixture_profile
    monkeypatch.setattr(stimuli, "_REGISTRY", dict(stimuli._REGISTRY))
    stimulus = replace(get_stimulus("teaching_gabor"), id="photometric_patch", calibration_requirements=("geometry", "luminance"))
    register_stimulus(stimulus)
    spec = get_experiment("orientation_task")
    profile = fixture_profile(verified=True)
    profile = replace(profile, calibration_status="accepted")
    selected = snapshot(document_for(stimulus), file_identity="meter_task.json")
    request = SetupRequest("student", "new", spec.id, profile.id, spec.field_defaults(), stimulus_snapshots={"target": selected})
    report = experiment_readiness(request, spec, profile, repo_root=ROOT)
    assert not next(row for row in report['requirements'] if row['key'] == 'luminance')['passed']
    with pytest.raises(ValueError, match="photometry"):
        validate_setup(request, spec, profile, mode="human")
    validate_setup(request, spec, profile, mode="simulation")
