"""Beginner authoring: the example must be understandable AND actually run."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from _manual_authoring_fixture import scaffold
from psychophysics_lab.experiments._internal.registry import get_experiment, register_experiment
from psychophysics_lab.stimuli.registry import get_stimulus, register_stimulus
from psychophysics_lab.config.stimulus_parameters import load_parameters
from psychophysics_lab.core.presentation import render_pixels
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def _load(path, module_name):
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def test_beginner_stimulus_is_really_a_line_not_renamed_gabor():
    stimulus = get_stimulus("example_stimulus")
    document = load_parameters(ROOT / stimulus.default_config, stimulus)["document"]
    pixels = render_pixels(stimulus, document["parameters"])
    assert pixels.ndim == 2 and pixels.shape == (256, 256)
    assert np.any(pixels == 255)
    assert np.any(pixels == 128)
    assert len(np.unique(pixels)) <= 2  # no Gabor carrier/wave pattern
    assert "spatial_frequency_cpd" not in document["parameters"]


def test_beginner_experiment_runs_full_chronological_response_save_loop(tmp_path):
    artifacts, _ = simulate(
        repo_root=ROOT, data_root=tmp_path / "synthetic", experiment_id="example_experiment",
        values={"trial_count": 4, "fixation_ms": 100, "stimulus_ms": 40, "interval_ms": 50})
    assert artifacts.status == "completed" and artifacts.accepted_trials == 4
    failures = [x for x in validate_run(artifacts.run_directory) if not x.passed]
    assert not failures, failures
    payload = json.loads((artifacts.run_directory / "trial_presentations.json").read_text())
    trials = payload["trials"]
    assert [t["parameters"]["offset_deg"] for t in trials] == [-1, 1, -1, 1]
    assert [[p["name"] for p in t["phase_events"]] for t in trials] == [
        ["fixation", "line", "blank", "answer"]
    ] * 4
    assert all(t["measurements"]["line_offset_deg"] == t["parameters"]["offset_deg"] for t in trials)


def test_new_scaffolds_start_from_simple_science_not_oriented_grating(tmp_path):
    files = scaffold(tmp_path, "my_white_line", kind="pair")
    assert len(files) == 4
    stimulus_file = tmp_path / "src/psychophysics_lab/stimuli/my_white_line.py"
    experiment_file = tmp_path / "src/psychophysics_lab/experiments/my_white_line.py"
    for path in files:
        if path.suffix == ".py":
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        else:
            json.loads(path.read_text(encoding="utf-8"))
    stimulus = _load(stimulus_file, "my_white_line_stimulus").SPEC
    experiment = _load(experiment_file, "my_white_line_experiment").SPEC
    assert stimulus.id == experiment.id == "my_white_line"
    assert experiment.stimulus_defaults == {"target": "my_white_line"}
    assert set(item.key for item in stimulus.parameters) == {
        "size_deg", "length_deg", "width_deg", "intensity"
    }
    assert "Gaussian-windowed" not in stimulus_file.read_text()
    assert "make_trial_order" in experiment_file.read_text()
    assert "NotImplementedError" in experiment_file.read_text()
    assert "left/right line task" not in experiment_file.read_text()
    with pytest.raises(ValueError, match="new files"):
        scaffold(tmp_path, "my_white_line", kind="pair")


def test_new_advanced_experiment_reuses_builtin_line_stimulus(tmp_path):
    path, timeline = scaffold(tmp_path, "my_new_experiment", kind="experiment")
    spec = _load(path, "my_new_experiment").SPEC
    assert spec.stimulus_defaults == {"target": "vertical_line_probe"}
    assert json.loads(timeline.read_text())["experiment_id"] == "my_new_experiment"
    assert spec.field_defaults()["stimulus_ms"] == 200


def test_csf_and_beginner_both_declare_phases_without_changing_csf_science():
    from psychophysics_lab.core.timeline import load_timeline
    beginner = get_experiment("example_experiment")
    csf = get_experiment("contrast_sensitivity")
    from psychophysics_lab.experiments.example_experiment import make_trial
    ex = make_trial().resolve(beginner.field_defaults()).validate_slots(beginner.stimulus_slots)
    cs = load_timeline(ROOT / "configs/experiments/contrast_sensitivity.json",
                       timings=csf.field_defaults(), slots=csf.stimulus_slots)
    assert len(ex.phases) == 7
    assert len(cs.phases) == 5
    assert ex.phases[4].kind == cs.phases[-1].kind == "response"
    assert ex.phases[-1].kind == "update_state"
    assert csf.legacy_module == "psychophysics_lab._reference_csf.contrast_sensitivity_function"


def test_normal_tui_has_explicit_example_source_controls():
    source = (ROOT / "src/psychophysics_lab/ui/setup.py").read_text(encoding="utf-8")
    assert 'id="read-example-stimulus"' not in source
    assert 'id="view-shared-stimulus-library"' in source
    assert 'id="read-example-experiment"' in source
    assert 'id="read-example-timeline"' in source
    assert 'id="read-csf-timeline"' in source
