"""Researcher-facing ownership plus frozen pre-audit scientific equivalence."""
import ast
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from psychophysics_lab.authoring import stage, mark_tested, publish
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.core.synthetic import SimulationRun
from psychophysics_lab.core.timeline import load_timeline
from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments

ROOT = Path(__file__).resolve().parents[1]


def normalise(value):
    if isinstance(value, list):
        return [normalise(v) for v in value]
    if isinstance(value, dict):
        return {k: v.rsplit(".", 1)[-1] if k in {"function", "update_value"} and isinstance(v, str)
                else normalise(v) for k, v in value.items()}
    return value


def test_current_public_csf_exposes_its_scientific_parameter_contract():
    spec = get_experiment("contrast_sensitivity")
    assert spec.procedure is not None
    assert spec.id == "contrast_sensitivity"
    assert "grating_offset_deg" in spec.field_defaults()
    assert "frequencies_cpd" in spec.field_defaults()
    assert "src/psychophysics_lab/experiments/contrast_sensitivity.py" in spec.source_paths


def test_every_python_procedure_is_owned_by_its_named_file():
    for spec in list_experiments(include_historical=True):
        assert spec.procedure is not None, spec.id
        if spec.historical:
            continue  # Frozen replay tests qualify archived scientific behaviour.
        if spec.procedure.__module__.endswith("library_builder"):
            continue  # saved-design compatibility; absent from normal authoring UI
        from psychophysics_lab.experiments._internal.source_names import source_name
        name = source_name(spec.id)
        assert spec.procedure.__module__ == "psychophysics_lab.experiments." + name
        assert f"src/psychophysics_lab/experiments/{name}.py" in spec.source_paths


def test_current_csf_and_orientation_timelines_use_selected_settings():
    from psychophysics_lab.experiments import contrast_sensitivity as csf
    values = csf.SPEC.normalise_values(csf.SPEC.field_defaults() | {
        "fixation_ms":173,"grating_ms":91,"grating_offset_deg":1.7
    })
    trial = csf.make_trial(values, {"target":0}).resolve(values)
    assert [(p.name,p.duration_ms) for p in trial.phases] == [
        ("fixation",173),("grating",91),("answer",0)]
    assert trial.phases[1].placements[0].x_deg == -1.7
    for identity in ("orientation_task","orientation_adaptive"):
        module = importlib.import_module("psychophysics_lab.experiments." + identity)
        values = module.SPEC.field_defaults() | {"fixation_ms":173,"stimulus_ms":91}
        expected = load_timeline(ROOT / "configs/experiments/orientation_task.json",
                                 timings=values,slots={"target"})
        actual = module.make_trial(values,{"target":0}).resolve(values)
        assert [(p.name,p.kind,p.slot,p.duration_ms,p.instructions) for p in actual.phases] == [
            (p.name,p.kind,p.slot,p.duration_ms,p.instructions) for p in expected.phases]


def test_new_file_is_discovered_without_registry_edits_and_managed_drafts_stay_gated(tmp_path, monkeypatch):
    from psychophysics_lab.experiments._internal import contributions as loader
    import psychophysics_lab.authoring as authoring
    folder = tmp_path / "experiments"
    folder.mkdir()
    (folder / "contributions.py").write_text("")
    (folder / "new_task.py").write_text("SPEC = object()")
    (folder / "draft_task.py").write_text("SPEC = object()")
    (folder / "flanker_response.py").write_text("from .contrast_sensitivity import CSF_SPEC as SPEC")
    (folder / "helper.py").write_text("def policy(): pass")
    monkeypatch.setattr(loader, "__file__", str(folder / "_internal/contributions.py"))
    monkeypatch.setattr(authoring, "inventory", lambda root: (SimpleNamespace(name="draft_task", kind="experiment"),))
    assert loader.discover_experiment_modules() == ("psychophysics_lab.experiments.new_task",)


def test_single_python_file_can_be_staged_and_fingerprinted_without_companion(tmp_path):
    path = tmp_path / "src/psychophysics_lab/experiments/single_file.py"
    path.parent.mkdir(parents=True)
    path.write_text("SPEC = None\n")
    item = stage(tmp_path, "experiment", "single_file")
    assert item.status == "draft"
    mark_tested(tmp_path, "experiment", "single_file")
    # Publishing validates imported SPEC dependencies; no companion is required.
    # Fingerprinting a Python-only experiment tracks source changes correctly.
    from psychophysics_lab.authoring import fingerprint
    before = fingerprint(tmp_path, item)
    path.write_text("SPEC = None\n# source edited\n")
    assert fingerprint(tmp_path, item) != before
    with pytest.raises(ValueError, match="changed since last successful test"):
        publish(tmp_path, "experiment", "single_file")


@pytest.mark.parametrize("identity", [
    "line_position_baseline","line_position_flanker","ellipse_centre","ellipse_major_axis"
])
def test_public_adaptive_policy_is_visible_in_the_experiment_source(identity):
    from psychophysics_lab.experiments._internal.registry import get_experiment
    spec=get_experiment(identity)
    source=(ROOT / f"src/psychophysics_lab/experiments/{identity}.py").read_text()
    defaults=spec.field_defaults()
    for key in ("n_down","n_up","reversal_termination","staircases_per_condition"):
        assert key in defaults and key in source
        assert key in spec.adaptive.controls


def test_spatial_python_migration_matches_legacy_design_for_every_phase_and_position():
    from psychophysics_lab.experiments.probe_above_below import make_trial, update_experiment, SPEC
    from psychophysics_lab.experiments._internal.library_builder import _make_timeline
    doc = json.loads((ROOT / "configs/experiment_designs/probe_above_below.json").read_text())
    for y in (2., -2.):
        old = _make_timeline(doc["actions"], SPEC.field_defaults(), (0., y), ("above", "below"))
        from psychophysics_lab.researcher import TrialTimeline
        actions = []
        update_experiment(None, None, {}, None, SimpleNamespace(apply=lambda *a: actions.extend(a), state={}))
        new = TrialTimeline(make_trial(SPEC.field_defaults(), {"probe_y_deg":y}).phases + tuple(actions)).resolve(SPEC.field_defaults())
        # The callable has moved and been renamed; compare its behaviour too.
        before, after = normalise(old.to_dict()), normalise(new.to_dict())
        before["phases"][-1].pop("function")
        after["phases"][-1].pop("function")
        assert after == before
        for correct in (False, True):
            state, response = {"correct_count": 7}, {"correct": correct}
            assert new.phases[-1].function(state, response) == old.phases[-1].function(state, response)


def test_researcher_probe_instructions_follow_remapped_response_keys():
    from psychophysics_lab.experiments.new_probe_vertical_line_stimulus import procedure, SPEC
    from contextlib import contextmanager
    captured = []
    run = SimpleNamespace(values=SPEC.field_defaults() | {"trial_count":1}, accepted_trials=0,
        synthetic=True, responses=SimpleNamespace(keys=("UP", "DOWN"), alternatives=("above", "below")),
        initialise=lambda **kwargs: None, complete=lambda: None, stimulus_parameters=lambda *a, **k: {})
    @contextmanager
    def trial(plan, **kwargs):
        captured.append(kwargs)
        yield SimpleNamespace(response={"alternative":0, "correct":True},
            apply=lambda *a: None, state={"correct_count":1})
        run.accepted_trials += 1
    run.trial = trial
    procedure(run)
    assert captured[0]["instructions"] == "Above: UP   Below: DOWN"
    assert captured[0]["target"] == 0 and captured[0]["condition"] == "above"



def test_discovery_registers_a_new_python_file_without_companion_or_manual_list(tmp_path, monkeypatch):
    import sys
    import psychophysics_lab.experiments as package
    from psychophysics_lab import contributions
    from psychophysics_lab.experiments._internal import contributions as loader, registry
    from psychophysics_lab.stimuli import registry as stimuli
    # Make a real importable single-file experiment outside the checkout.
    source = (ROOT / "src/psychophysics_lab/experiments/example_experiment.py").read_text()
    source = source.replace('identity="example_experiment"', 'identity="new_task"')
    source = source.replace('default_config=f"configs/experiments/{identity}.json",', '')
    (tmp_path / "new_task.py").write_text(source)
    monkeypatch.setattr(package, "__path__", [str(tmp_path), *package.__path__])
    monkeypatch.setattr(loader, "__file__", str(tmp_path / "_internal/contributions.py"))
    monkeypatch.setattr(loader, "_loaded", False)
    monkeypatch.setattr(registry, "_REGISTRY", dict(registry._REGISTRY))
    monkeypatch.setattr(stimuli, "_REGISTRY", dict(stimuli._REGISTRY))
    monkeypatch.setattr(contributions, "EXPERIMENT_MODULES", None)
    # Restore the module cache along with registries when this test exits.
    monkeypatch.setitem(sys.modules, "psychophysics_lab.experiments.new_task", None)
    del sys.modules["psychophysics_lab.experiments.new_task"]
    spec = get_experiment("new_task")
    assert spec.procedure.__module__ == "psychophysics_lab.experiments.new_task"
    assert spec.field_defaults()["trial_count"] == 6 and not spec.default_config


@pytest.mark.parametrize("adaptive", [None, SimpleNamespace(algorithm_id="consecutive_up_down")])
def test_ready_publication_succeeds_for_an_exact_tested_python_file(tmp_path, monkeypatch, adaptive):
    from psychophysics_lab import authoring
    path = tmp_path / "src/psychophysics_lab/experiments/ready_task.py"
    path.parent.mkdir(parents=True)
    path.write_text("SPEC = None\n")
    authoring.stage(tmp_path, "experiment", "ready_task")
    authoring.mark_tested(tmp_path, "experiment", "ready_task")
    module = SimpleNamespace(SPEC=SimpleNamespace(adaptive=adaptive))
    monkeypatch.setattr(authoring.importlib, "import_module", lambda name: module)
    monkeypatch.setattr(authoring.importlib, "reload", lambda value: value)
    assert authoring.publish(tmp_path, "experiment", "ready_task").status == "ready"


def test_ready_publication_still_requires_tested_ready_adaptive_dependency(tmp_path, monkeypatch):
    from psychophysics_lab import authoring
    folder = tmp_path / "src/psychophysics_lab"
    for kind, name in (("experiments", "dependent_task"), ("adaptive", "custom_rule")):
        path = folder / kind / (name + ".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("SPEC = None\n")
    authoring.stage(tmp_path, "adaptive", "custom_rule")
    authoring.stage(tmp_path, "experiment", "dependent_task")
    authoring.mark_tested(tmp_path, "experiment", "dependent_task")
    module = SimpleNamespace(SPEC=SimpleNamespace(adaptive=SimpleNamespace(algorithm_id="custom_rule")))
    monkeypatch.setattr(authoring.importlib, "import_module", lambda name: module)
    monkeypatch.setattr(authoring.importlib, "reload", lambda value: value)
    with pytest.raises(ValueError, match="Publish and retest dependent adaptive"):
        authoring.publish(tmp_path, "experiment", "dependent_task")


def test_python_procedure_storyboard_does_not_replay_a_retired_json_plan(tmp_path):
    from psychophysics_lab.development import preview_trial_storyboard
    spec = get_experiment("orientation_task")
    assert preview_trial_storyboard(ROOT, spec, spec.field_defaults(), tmp_path / "story.png") is None
    assert not (tmp_path / "story.png").exists()


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="Windows batch launcher")
def test_windows_launcher_forwards_cli_arguments_and_preserves_spaces(tmp_path):
    import os
    import shutil
    import subprocess
    import venv
    # Run the actual batch entry point, using a hardware-free fake app and a
    # no-install setup hook. The real local environment is never changed.
    shutil.copyfile(ROOT / "run_psycolab.bat", tmp_path / "run_psycolab.bat")
    (tmp_path / "pyproject.toml").write_text("# launcher presence check\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "launcher_setup.py").write_text("# no installation in this regression fixture\n")
    venv.EnvBuilder(with_pip=False).create(tmp_path / ".venv")
    package = tmp_path / "psychophysics_lab"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "__main__.py").write_text(
        "import json, sys\nfrom pathlib import Path\n"
        "Path('received.json').write_text(json.dumps(sys.argv[1:]))\n")
    command = (
        '"' + os.environ.get("COMSPEC", "cmd.exe") + '" /d /c '
        'call run_psycolab.bat --probe-token "a value with spaces" <NUL'
    )
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=45,
        creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / "received.json").read_text()) == ["--probe-token", "a value with spaces"]
