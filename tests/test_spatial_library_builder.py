"""Researcher acceptance: reusable stimuli -> JSON-only experiment -> saved trials."""
import json
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.core.presentation import render_pixels
from psychophysics_lab.experiments.library_builder import (
    BUILTIN, create_design, default_design, inventory, make_spec,
    validate_design, test_design as run_library_test, mark_ready,
)
from psychophysics_lab.experiments.registry import get_experiment, list_experiments
from psychophysics_lab.scaffold import scaffold_vertical_line
from psychophysics_lab.stimuli.registry import get_stimulus
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def test_stimulus_library_contains_real_cross_and_white_line():
    cross, line = get_stimulus("fixation_cross"), get_stimulus("vertical_line_probe")
    assert cross.render is not None and line.render is not None
    from psychophysics_lab.config.stimulus_parameters import load_parameters
    a = load_parameters(ROOT / cross.default_config, cross)["document"]["parameters"]
    b = load_parameters(ROOT / line.default_config, line)["document"]["parameters"]
    cross_pixels = render_pixels(cross, a)
    line_pixels = render_pixels(line, b)
    assert cross_pixels.shape == line_pixels.shape == (256, 256)
    assert np.max(cross_pixels) == np.max(line_pixels) == 255
    # A cross and a line are different rendered geometric stimuli.
    assert not np.array_equal(cross_pixels, line_pixels)


def test_spatial_probe_demo_is_registered_without_an_experiment_python_file():
    spec = get_experiment("probe_above_below")
    assert spec.procedure is not None and spec.supports_simulation
    assert spec.stimulus_defaults == {"fixation": "fixation_cross", "probe": "vertical_line_probe"}
    assert spec.response_paradigm.alternatives == ("above", "below")
    assert spec.response_paradigm.keys == ("F", "J")
    assert spec.calibration_requirements == ("geometry",)
    assert any(x.id == "probe_above_below" for x in list_experiments())
    assert (ROOT / "configs/experiment_designs/probe_above_below.json").is_file()
    assert not (ROOT / "src/psychophysics_lab/experiments/probe_above_below.py").exists()


def test_full_demo_virtual_run_saves_actions_conditions_and_positions(tmp_path):
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data",
                            experiment_id="probe_above_below",
                            values={"trial_count": 4, "random_seed": 0}, analyse=False)
    assert artifacts.status == "completed"
    assert artifacts.accepted_trials == 4
    failures = [check for check in validate_run(artifacts.run_directory) if not check.passed]
    assert not failures, failures
    data = json.loads((artifacts.run_directory / "resolved_experiment.json").read_text())
    assert data["library_design"]["stimuli"]["fixation"] == "fixation_cross"
    events = json.loads((artifacts.run_directory / "trial_actions.json").read_text())
    assert events["trials"]
    positions = []
    for trial in events["trials"]:
        phases = trial["plan"]["phases"]
        assert [p["kind"] for p in phases] == [
            "show", "record_state", "show", "show", "response",
            "record_state", "update_state"
        ]
        placements = phases[2]["stimuli"]
        assert [p["slot"] for p in placements] == ["fixation", "probe"]
        positions.append(placements[-1]["y_deg"])
        assert trial["final_state"]["correct_count"] >= 0
    assert set(positions) == {-2.0, 2.0}


def test_design_schema_rejects_unsafe_or_conflicting_configuration():
    sample = default_design("spatial_check")
    validate_design(sample)
    for change in (
        lambda d: d.update(injected="ignore"),
        lambda d: d["actions"][2].update(code="__import__('os')"),
        lambda d: d["stimuli"].update(probe="nonexistent_library_stimulus"),
        lambda d: d["conditions"][1].update(probe_position_deg=[0.0, 2.0]),
        lambda d: d["values"].update(stimulus_ms=-12),
        lambda d: d["response"].update(keys=["F", "F"]),
    ):
        candidate = json.loads(json.dumps(sample))
        change(candidate)
        with pytest.raises((ValueError, TypeError)):
            validate_design(candidate)


def test_new_white_line_scaffold_and_json_experiment_are_independent(tmp_path):
    files = scaffold_vertical_line(tmp_path, "my_white_line")
    assert len(files) == 2
    assert files[0].name == "my_white_line.py"
    source = files[0].read_text(encoding="utf-8")
    compile(source, str(files[0]), "exec")
    assert 'id="my_white_line"' not in source  # declaration uses positional args
    assert '"my_white_line"' in source
    data = json.loads(files[1].read_text(encoding="utf-8"))
    assert data["stimulus_id"] == "my_white_line"
    assert "line_length" not in data["parameters"]  # keys are short and scientific
    with pytest.raises(ValueError, match="already exist"):
        scaffold_vertical_line(tmp_path, "my_white_line")


def test_library_create_never_writes_new_python_experiment_module(tmp_path):
    path = create_design(tmp_path, "my_spatial_task", separation_deg=1.75)
    assert path.name == "my_spatial_task.json"
    assert len(inventory(tmp_path)) >= 2
    assert not (tmp_path / "src/psychophysics_lab/experiments/my_spatial_task.py").exists()
    doc = json.loads(path.read_text())
    assert doc["conditions"][0]["probe_position_deg"] == [0.0, 1.75]
    # The generated JSON is independently valid, with no Python source scaffold.
    validate_design(doc)
