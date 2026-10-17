"""Single, self-contained stimulus class is the whole authoring contract."""
import inspect
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.app import _main, build_parser
from psychophysics_lab.core.presentation import render_pixels
from psychophysics_lab.stimuli.registry import get_stimulus, list_stimuli
from psychophysics_lab import stimulus_library as stimuli

ROOT = Path(__file__).resolve().parents[1]
IDS = {
    "oriented_line": "LinePatch",
    "square_patch": "SquarePatch",
    "rectangle_patch": "RectanglePatch",
    "ellipse_patch": "EllipsePatch",
    "annulus_patch": "AnnulusPatch",
    "gaussian_dot": "GaussianDot",
    "sine_grating": "SinusoidalGrating",
    "gabor_patch": "GaborPatch",
}


@pytest.mark.parametrize("identity,class_name", IDS.items())
def test_each_shape_is_wholly_defined_in_its_own_library_class(identity, class_name):
    cls = getattr(stimuli, class_name)
    spec = get_stimulus(identity)
    assert issubclass(cls, stimuli.LibraryStimulus)
    assert spec is cls.SPEC
    assert cls.SPEC.render is cls.render
    assert tuple(cls.PARAMETERS) == spec.parameters
    assert spec.source_path == "src/psychophysics_lab/stimulus_library.py"
    assert spec.default_config == ""
    assert Path(inspect.getsourcefile(cls)).resolve() == (
        ROOT / "src/psychophysics_lab/stimulus_library.py").resolve()
    params = {field.key: field.default for field in cls.PARAMETERS}
    pixels = render_pixels(spec, params, pixels=(64, 64))
    assert pixels.shape == (64, 64)
    assert pixels.dtype == np.uint8
    assert pixels.min() < pixels.max()


def test_complete_new_stimulus_classes_are_automatically_registered():
    identifiers = {spec.id for spec in list_stimuli()}
    assert IDS.keys() <= identifiers


def test_no_second_dispatch_or_generator_in_researcher_facing_file():
    source = (ROOT / "src/psychophysics_lab/stimulus_library.py").read_text()
    assert "def _layer(" not in source
    assert "_FUNCTIONS =" not in source
    assert "_FIELDS =" not in source
    assert "class LibraryStimulus:" in source
    assert (ROOT / "src/psychophysics_lab/core/scene_primitives.py").is_file()
    opts = build_parser()
    assert not any(action.dest in {"scaffold", "blueprint", "library_create",
                                    "library_probe", "library_fixation", "library_separation"}
                   for action in opts._actions)


def test_render_without_separate_json_file(tmp_path):
    target = tmp_path / "square.png"
    assert _main(["--preview-stimulus", "square_patch", "--preview-output", str(target)]) == 0
    assert target.is_file() and target.stat().st_size > 0


def test_legacy_scene_maths_stay_the_same():
    scene = stimuli.Scene(
        stimuli.annulus(radius_x_deg=2, radius_y_deg=1, inner_ratio=.8),
        stimuli.line(length_deg=.6, width_deg=.08),
        background=.5,
    )
    x = np.linspace(-2.5, 2.5, 101)
    xx, yy = np.meshgrid(x, x)
    pixels = scene.render(xx, yy)
    clone = stimuli.Scene.from_dict(scene.to_dict())
    np.testing.assert_array_equal(clone.render(xx, yy), pixels)
    assert pixels.min() >= 0 and pixels.max() <= 1


def test_parameter_validation_remains_local_and_strict():
    spec = get_stimulus("annulus_patch")
    values = {field.key: field.default for field in spec.parameters}
    with pytest.raises(ValueError):
        spec.validate_parameters(values | {"inner_ratio": 1.2})
    with pytest.raises(ValueError):
        spec.validate_parameters(values | {"intensity": float("nan")})
