"""Stable authoring contract and TUI-independent first lesson."""
import json
from pathlib import Path

import pytest

from psychophysics_lab.app import _main, build_parser
from psychophysics_lab.scaffold import scaffold
from psychophysics_lab.experiments.registry import get_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_learning_is_discoverable_without_textual(capsys):
    assert build_parser().parse_args(["--learn"]).learn is True
    assert _main(["--learn"]) == 0
    rendered = capsys.readouterr().out
    for topic in ("--dev-preview", "--dev-ready stimulus", "--library-create",
                  "--library-test", "--library-ready", "run_psycolab.bat",
                  "trial_actions.json"):
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


def test_json_and_user_python_experiments_are_distinguishable():
    from psychophysics_lab.ui.setup import experiment_choice_label
    json_label = experiment_choice_label(get_experiment("probe_above_below"), ROOT)
    # Inspect the preserved author definition, not the live acquisition
    # registry: the latter properly excludes Ready IDs whose source hash is stale.
    from psychophysics_lab.experiments.new_probe_vertical_line_stimulus import SPEC as authored_spec
    user_label = experiment_choice_label(authored_spec, ROOT)
    assert "Built-in JSON" in json_label and "probe_above_below" in json_label
    assert "Researcher Python" in user_label
    assert "new_probe_vertical_line_stimulus" in user_label


def test_tui_links_to_the_independent_guide():
    source = (ROOT / "src/psychophysics_lab/ui/setup.py").read_text(encoding="utf-8")
    for control in ("learn-guide", "learn-experiments", "learn-stimuli", "authoring-contract"):
        assert f'id="{control}"' in source
    assert "yield LibraryExperimentBuilder()" in source
    assert (ROOT / "docs/LEARN_PSYCOLAB.md").is_file()
    assert (ROOT / "docs/AUTHORING_CONTRACT.md").is_file()


def test_historical_researcher_modules_are_preserved():
    manifest = json.loads((ROOT / "authoring/components.json").read_text())
    states = {(d["kind"], d["name"]): d["status"] for d in manifest["components"]}
    assert states[("experiment", "new_probe_vertical_line_stimulus")] == "ready"
    assert states[("experiment", "new_probe_fixation_test")] == "draft"
    assert states[("stimulus", "new_probe_vertical_line")] == "ready"
    for path in ("src/psychophysics_lab/experiments/new_probe_fixation_test.py",
                 "src/psychophysics_lab/experiments/new_probe_vertical_line_stimulus.py",
                 "src/psychophysics_lab/stimuli/new_probe_vertical_line.py"):
        assert (ROOT / path).is_file()
