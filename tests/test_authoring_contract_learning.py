"""Stable authoring contract and TUI-independent first lesson."""
import json
from pathlib import Path

import pytest

from psychophysics_lab.app import _main, build_parser
from _manual_authoring_fixture import scaffold
from psychophysics_lab.experiments._internal.registry import get_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_learning_is_discoverable_without_textual(capsys):
    assert build_parser().parse_args(["--learn"]).learn is True
    assert _main(["--learn"]) == 0
    rendered = capsys.readouterr().out
    for topic in ("--dev-preview", "--dev-stage experiment", "--dev-test",
                  "--dev-ready experiment", "stimulus_library.py", "TrialTimeline"):
        assert topic in rendered
    assert chr(92) + chr(96) not in rendered


def test_advanced_scaffold_does_not_copy_left_right_science(tmp_path):
    source, settings = scaffold(tmp_path, "my_adv_task", kind="experiment")
    code = source.read_text(encoding="utf-8")
    assert "NotImplementedError" in code
    assert "BLUEPRINT_" not in code
    assert "left/right line task" not in code
    assert "return [trial % 2" not in code
    from test_beginner_examples import _load
    spec = _load(source, "my_adv_task").SPEC
    assert spec.id == "my_adv_task"
    assert spec.stimulus_defaults == {"target": "vertical_line_probe"}
    assert spec.stimulus_slots == {"target": "line"}
    assert json.loads(settings.read_text())["experiment_id"] == spec.id
    with pytest.raises(NotImplementedError):
        spec.procedure(type("FakeRun", (), {"values": {"trial_count": 6}})())


def test_stimulus_scaffold_uses_centered_line(tmp_path):
    code, settings = scaffold(tmp_path, "my_line", kind="stimulus")
    source = code.read_text(encoding="utf-8")
    assert "offset_deg" not in source
    assert "def render(parameters, x_deg, y_deg)" in source
    assert 'family="line"' in source
    assert set(json.loads(settings.read_text())["parameters"]) == {
        "size_deg", "length_deg", "width_deg", "intensity"
    }


def test_json_and_user_python_experiments_are_distinguishable(tmp_path):
    from dataclasses import replace
    from psychophysics_lab.ui.setup import experiment_choice_label
    json_label = experiment_choice_label(get_experiment("probe_above_below"), ROOT)
    # The classification must not depend on a particular researcher's files
    # or bypass Ready source-hash enforcement in the live registry.
    authoring = tmp_path / "authoring"
    authoring.mkdir()
    (authoring / "components.json").write_text(json.dumps({
        "schema_version": 1, "components": [
            {"kind": "experiment", "name": "researcher_task",
             "status": "ready", "tested_fingerprint": ""}
        ]
    }))
    authored_spec = replace(get_experiment("example_experiment"),
                            id="researcher_task", display_name="Probe task")
    user_label = experiment_choice_label(authored_spec, tmp_path)
    assert "Built-in Python" in json_label and "probe_above_below" in json_label
    assert "Researcher Python" in user_label
    assert "researcher_task" in user_label


def test_tui_links_to_the_independent_guide():
    source = (ROOT / "src/psychophysics_lab/ui/setup.py").read_text(encoding="utf-8")
    for control in ("learn-guide", "learn-experiments", "learn-stimuli", "authoring-contract"):
        assert f'id="{control}"' in source
    assert "yield LibraryExperimentBuilder()" not in source
    assert 'id="build-new-experiment"' not in source
    assert 'id="build-new-stimulus"' not in source
    assert 'id="view-shared-stimulus-library"' in source
    assert 'id="view-shared-scene-example"' in source
    assert "src/psychophysics_lab/stimulus_library.py" in source
    assert "examples/shared_stimuli.py" in source
    assert "Advanced: create independent stimulus adapter" not in source
    assert (ROOT / "docs/LEARN_PSYCOLAB.md").is_file()
    assert (ROOT / "docs/AUTHORING_CONTRACT.md").is_file()


def test_archived_or_incomplete_drafts_do_not_need_to_be_deleted():
    from psychophysics_lab.authoring import inventory
    records = inventory(ROOT)
    # A historical draft can refer to a file not currently in the checkout.
    # Only attempting to load/publish it should require actual source files.
    assert len({(item.kind, item.name) for item in records}) == len(records)
    assert all(item.kind in {"stimulus", "experiment", "adaptive"} for item in records)
