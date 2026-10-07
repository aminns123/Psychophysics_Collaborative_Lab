from pathlib import Path

from psychophysics_lab.experiments.registry import get_experiment
from psychophysics_lab.ui.setup import _source_candidates, _stimulus_sources


ROOT = Path(__file__).resolve().parents[1]


def test_registered_experiment_has_inspectable_source_files():
    paths = _source_candidates(ROOT, get_experiment("contrast_sensitivity"))
    assert any(path.name == "contrast_sensitivity.py" for path in paths)
    assert any(path.name == "contrast_sensitivity_function.py" for path in paths)


def test_reusable_and_legacy_stimulus_sources_are_visible_to_inspector():
    names = {path.name for path in _stimulus_sources(ROOT)}
    assert "geometry.py" in names
    assert "stimuliC.py" in names
