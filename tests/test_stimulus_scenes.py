import json
import math
from pathlib import Path
import numpy as np
import pytest
from psychophysics_lab.stimulus_library import (
    Scene, Drawing, fixation, line, rectangle, square, grating, gabor, ellipse, annulus, gaussian_dot,
)


@pytest.mark.parametrize("factory", [fixation, line, rectangle, square, grating, gabor, ellipse, annulus, gaussian_dot])
def test_primitives_roundtrip_and_finite_output(factory):
    s = Scene(factory())
    grid = np.linspace(-4, 4, 129)
    x, y = np.meshgrid(grid, grid)
    pixels = s.render(x, y)
    assert pixels.shape == x.shape and np.isfinite(pixels).all()
    assert pixels.min() >= 0 and pixels.max() <= 1
    restored = Scene.from_dict(json.loads(s.parameters(20)["scene_json"]))
    np.testing.assert_array_equal(restored.render(x, y), pixels)


def test_composition_has_no_opaque_background_holes():
    s = Scene(rectangle(width_deg=4, height_deg=4, intensity=.8),
              line(length_deg=2, width_deg=.2, intensity=0))
    assert s.render(np.array([0., .5, 3.]), np.zeros(3)).tolist() == [0., .8, .5]
    reverse = Scene(*reversed(s.drawings))
    assert reverse.render(0, 0) == .8


def test_grating_units_and_legacy_nonbox_formula():
    x = np.linspace(-2.49, 2.49, 100)
    s = Scene(grating(size_deg=5, spatial_frequency_cpd=31.5/(2*np.pi*5),
                      amplitude=.018/2, mean=.24), background=.24)
    np.testing.assert_allclose(s.render(x, np.zeros_like(x)), .24+.018/2*np.sin(31.5*x/5), atol=1e-15)


def test_annulus_width_maps_squared_legacy_equation():
    s = Scene(annulus(radius_x_deg=2, radius_y_deg=1, inner_ratio=math.sqrt(.98)))
    assert s.render(2*.995, 0) == 1
    assert s.render(2*.98, 0) == .5
    assert s.render(0, .995) == 1
    assert s.render(2.01, 0) == .5


def test_placement_rotation_and_immutability():
    vertical = line(length_deg=2, width_deg=.1)
    horizontal = line(length_deg=2, width_deg=.1, orientation_deg=90)
    assert Scene(vertical).render(0, .8) == 1
    assert Scene(horizontal).render(.8, 0) == 1
    moved = vertical.at(2, 1)
    assert Scene(moved).render(2, 1) == 1
    assert vertical.parameters["x_deg"] == 0
    with pytest.raises(TypeError):
        vertical.parameters["x_deg"] = 1


@pytest.mark.parametrize("build", [lambda: line(width_deg=0), lambda: line(x_deg=float("nan")),
    lambda: grating(amplitude=.4, mean=.2), lambda: annulus(inner_ratio=1),
    lambda: Scene(background=float("inf")), lambda: line(intensity=True),
    lambda: Drawing("untrusted_function", {}), lambda: Scene(line()).parameters(.01)])
def test_invalid_drawings_fail_without_clipping_or_eval(build):
    with pytest.raises((ValueError, TypeError)):
        build()


def test_composed_adapter_checks_nested_nyquist():
    from dataclasses import replace
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.stimuli.registry import get_stimulus
    from psychophysics_lab.core.presentation import validate_geometry
    root = Path(__file__).resolve().parents[1]
    profile = replace(load_monitor_profiles(root)["legacy_reference_display"], expected_resolution_px=(1920,1080))
    with pytest.raises(ValueError, match="Nyquist"):
        validate_geometry(profile, (1920,1080), get_stimulus("composed_scene"),
                          Scene(grating(spatial_frequency_cpd=10000)).parameters(18))


def test_shared_library_edits_invalidate_opt_in_authored_fingerprint(tmp_path):
    from psychophysics_lab.authoring import Component, fingerprint
    source = tmp_path / "src/psychophysics_lab/stimuli/my_scene.py"
    source.parent.mkdir(parents=True)
    source.write_text("from psychophysics_lab.stimulus_library import Scene, line\n")
    config = tmp_path / "configs/stimuli/my_scene.json"
    config.parent.mkdir(parents=True)
    config.write_text("{}")
    library = tmp_path / "src/psychophysics_lab/stimulus_library.py"
    library.write_text("first version")
    item = Component("stimulus", "my_scene", "draft")
    before = fingerprint(tmp_path, item)
    library.write_text("changed geometry")
    assert fingerprint(tmp_path, item) != before
