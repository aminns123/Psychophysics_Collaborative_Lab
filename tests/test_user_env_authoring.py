"""Developer workbench acceptance: draft registration, edits, promotion and safe paths."""
import json
from pathlib import Path

import pytest

from psychophysics_lab.authoring import (
    inventory, scaffold_draft, mark_tested, publish, fingerprint, stage,
)
from psychophysics_lab.development import user_data_root
from psychophysics_lab.app import build_parser
from psychophysics_lab.experiments.registry import get_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_generated_files_are_drafts_then_can_be_published_only_when_unchanged(tmp_path):
    files = scaffold_draft(tmp_path, "student_patch", "stimulus")
    assert len(files) == 2
    assert inventory(tmp_path)[0].status == "draft"
    with pytest.raises(ValueError, match="last successful test"):
        publish(tmp_path, "stimulus", "student_patch")
    mark_tested(tmp_path, "stimulus", "student_patch")
    assert inventory(tmp_path)[0].tested_fingerprint == fingerprint(tmp_path, inventory(tmp_path)[0])
    files[1].write_text(files[1].read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Source or JSON changed"):
        publish(tmp_path, "stimulus", "student_patch")
    mark_tested(tmp_path, "stimulus", "student_patch")
    assert publish(tmp_path, "stimulus", "student_patch").status == "ready"
    with pytest.raises(ValueError, match="nothing was overwritten"):
        scaffold_draft(tmp_path, "student_patch", "stimulus")
    assert len(inventory(tmp_path)) == 1


def test_non_default_experiments_are_not_available_until_manifest_ready(tmp_path):
    scaffold_draft(tmp_path, "student_task", "experiment")
    assert "student_task" not in {spec.id for spec in __import__(
        "psychophysics_lab.experiments.registry", fromlist=["list_experiments"]).list_experiments()}
    record = inventory(tmp_path)[0]
    assert record.status == "draft"
    assert (tmp_path / "configs/experiments/student_task.json").is_file()
    assert (tmp_path / "src/psychophysics_lab/experiments/student_task.py").is_file()


def test_inventory_rejects_untrusted_module_names_and_invalid_manifest(tmp_path):
    with pytest.raises(ValueError):
        stage(tmp_path, "stimulus", "../bad")
    path = tmp_path / "authoring/components.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"schema_version":1,"components":[{"kind":"experiment","name":"../../bad","status":"ready"}]}))
    with pytest.raises(ValueError):
        inventory(tmp_path)


def test_source_files_and_configuration_use_public_experiment_api():
    spec = get_experiment("orientation_task")
    result = spec.normalise_values({"trial_count": 2, "random_seed": 42,
                                    "response_keys": "F,J", "fixation_ms": 300})
    assert result["trial_count"] == 2
    assert result["fixation_ms"] == 300
    with pytest.raises(ValueError):
        spec.normalise_values({"unknown_input": 4})
    assert (ROOT / "src/psychophysics_lab/experiments/orientation_task.py").is_file()
    assert (ROOT / "configs/experiments/orientation_task.json").is_file()


def test_plain_terminal_cli_does_not_load_user_env_tui():
    from psychophysics_lab import development
    assert callable(development.execute_user_action)
    assert callable(development.preview_trial_storyboard)
    assert not (ROOT / "src/psychophysics_lab/user_env.py").exists()
    parser = build_parser()
    assert parser.parse_args(["--dev-test", "student_task"]).dev_test == "student_task"
    assert parser.parse_args(["--dev-preview", "student_patch"]).dev_preview == "student_patch"
    assert parser.parse_args(["--dev-ready", "stimulus", "student_patch"]).dev_ready == ["stimulus", "student_patch"]
    assert parser.parse_args(["--dev-list"]).dev_list
    with pytest.raises(SystemExit):
        parser.parse_args(["--user-env"])


def test_synthetic_development_root_is_outside_checkout(tmp_path):
    data_root = user_data_root(tmp_path)
    assert data_root.is_relative_to(Path.home())
    assert not data_root.is_relative_to(tmp_path)


def test_human_cannot_reuse_user_env_output_folder(tmp_path):
    from psychophysics_lab.paths import resolve_data_root
    from psychophysics_lab.core.synthetic import simulation_workspace
    root = tmp_path / "isolated_dev"
    root.mkdir()
    (root / ".psycolab_user_env.json").write_text('{"schema_version":1,"purpose":"development_only","human_acquisition_allowed":false}')
    with pytest.raises(ValueError, match="USER_env development data"):
        resolve_data_root(root, ROOT)
    assert simulation_workspace(root, ROOT) == root.resolve()


def test_published_revision_reverts_to_unavailable_after_edit(tmp_path):
    """An untested edit must not register in human acquisition, but can be retested in USER_env."""
    from psychophysics_lab.authoring import load_authored
    import importlib
    import sys
    import psychophysics_lab.stimuli as stimuli_package
    from psychophysics_lab.stimuli import registry

    files = scaffold_draft(tmp_path, "student_patch_unverified", "stimulus")
    # Temporary package module under the test repository, not global app checkout.
    original_paths = list(stimuli_package.__path__)
    stimuli_package.__path__.append(str(tmp_path / "src/psychophysics_lab/stimuli"))
    monkey_registry = dict(registry._REGISTRY)
    try:
        mark_tested(tmp_path, "stimulus", "student_patch_unverified")
        publish(tmp_path, "stimulus", "student_patch_unverified")
        assert load_authored(tmp_path, tolerate_errors=True) == {}
        assert "student_patch_unverified" in registry._REGISTRY
        # Editing scientific Python invalidates the tested authoring fingerprint.
        files[0].write_text(files[0].read_text() + "\n# changed after publication\n")
        registry._REGISTRY.pop("student_patch_unverified")
        failures = load_authored(tmp_path, tolerate_errors=True)
        assert "stimulus:student_patch_unverified" in failures
        assert "student_patch_unverified" not in registry._REGISTRY
    finally:
        stimuli_package.__path__[:] = original_paths
        registry._REGISTRY.clear()
        registry._REGISTRY.update(monkey_registry)
        sys.modules.pop("psychophysics_lab.stimuli.student_patch_unverified", None)
        importlib.invalidate_caches()


def test_main_tui_retains_build_and_source_inspection():
    from psychophysics_lab.ui.setup import ExperimentsScreen, StimuliScreen
    assert ExperimentsScreen.page_title == "Experiments"
    assert StimuliScreen.page_title == "Stimuli"
    source = (ROOT / "src/psychophysics_lab/ui/setup.py").read_text(encoding="utf-8")
    assert 'id="build-new-experiment"' in source
    assert 'id="build-new-stimulus"' in source
    assert 'id="view-selected-source"' in source
    assert 'launch-user-env-experiments' not in source
    assert 'launch-user-env-stimuli' not in source
