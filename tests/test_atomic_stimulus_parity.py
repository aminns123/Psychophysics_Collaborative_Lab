"""Numerical science gate: independent objects vs established DetectionScene.

These tests retain the old renderer ONLY as a frozen comparison oracle. A new
experiment must describe every independent object and overlap rule in A1.
No historical saved trials, source hashes or calibration files are changed.
"""
import importlib
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.core.layer_composition import compose_ordered_layers
from psychophysics_lab.core.timeline import Stimulus
from psychophysics_lab.stimulus_library import (
    DetectionScene, EllipseRing, ProbeLine, FlankerGrating,
    GaussianSceneFixation,
)
from psychophysics_lab.experiments._internal.registry import get_experiment


OFFICIAL_WITH_OLD_SCENES = (
    "ellipse_centre",
    "ellipse_major_axis",
    "line_position_baseline",
    "line_position_flanker",
)
ROOT = Path(__file__).resolve().parents[1]


def parameters(definition):
    return {f.key: f.default for f in definition.PARAMETERS}


@pytest.mark.parametrize("name", OFFICIAL_WITH_OLD_SCENES)
def test_all_old_composite_clients_use_only_separately_named_stimuli(name):
    module = importlib.import_module("psychophysics_lab.experiments." + name)
    source = (ROOT / "src/psychophysics_lab/experiments" /
              (name + ".py")).read_text(encoding="utf-8")
    assert "STIMULI =" in source
    assert "STIMULUS_SLOTS" not in source
    assert "STIMULUS_DEFAULTS" not in source
    assert "detection_scene" not in module.STIMULI.values()
    assert dict(module.SPEC.stimulus_defaults) == module.STIMULI
    assert "probe_line" in module.STIMULI.values()
    assert "gaussian_scene_fixation" in module.STIMULI.values()
    # The legacy source is still available as a migration comparator.
    assert get_experiment(name).id == name


@pytest.mark.parametrize("background", [.2, .5, .8])
@pytest.mark.parametrize("ratio", [.5, .75, 1.])
@pytest.mark.parametrize("ring_present,flanker_present", [
    (False, False), (True, False), (False, True), (True, True),
])
@pytest.mark.parametrize("probe_present", [False, True])
def test_independent_objects_reconstruct_every_legacy_overlap(
    background, ratio, ring_present, flanker_present, probe_present
):
    """Pixel values must agree even where a bright probe overlaps the ring."""
    x, y = np.meshgrid(np.linspace(-6., 6., 481),
                       np.linspace(-4., 4., 321))
    pixel_steps = (.025, .025)
    legacy = parameters(DetectionScene)
    legacy.update(
        background=background, contrast=.035,
        probe_present=probe_present, probe_x_deg=.4, probe_y_deg=.25,
        ring_present=ring_present, ring_radius_deg=.85,
        ring_y_deg=.25, aspect_ratio=ratio, ring_increment=.06,
        flanker_present=flanker_present, flanker_cpd=2.5,
    )
    old_pixels = DetectionScene.render(legacy, x, y, pixel_steps=pixel_steps)

    layers = []
    if flanker_present:
        flanker = parameters(FlankerGrating)
        flanker.update(background=background, spatial_frequency_cpd=2.5,
                       width_deg=5., height_deg=5., amplitude=.009)
        layers.append((0, 0, FlankerGrating.render(flanker, x+3., y),
                       FlankerGrating.alpha(flanker, x+3., y),
                       background, "over"))
    if ring_present:
        ring = parameters(EllipseRing)
        ring.update(background=background, outer_radius_deg=.85,
                    aspect_ratio=ratio, inner_inset_deg=.16,
                    orientation_deg=0., display_contrast=.06/(1-background))
        layers.append((0, 0, EllipseRing.render(ring, x, y-.25),
                       EllipseRing.alpha(ring, x, y-.25),
                       background, "over"))
    if probe_present:
        probe = parameters(ProbeLine)
        probe.update(background=background, length_deg=1.,
                     width_deg=.013, display_contrast=.035/(1-background))
        px, py = x-.4, y-.25
        layers.append((0, 0, ProbeLine.render(probe, px, py,
                                                pixel_steps=pixel_steps),
                       ProbeLine.alpha(probe, px, py, pixel_steps=pixel_steps),
                       background, "add"))
    fixation = parameters(GaussianSceneFixation)
    fixation.update(background=background, size_deg=14.,
                    increment=.09, sigma_deg=.035)
    layers.append((0, 0, GaussianSceneFixation.render(fixation, x, y),
                   GaussianSceneFixation.alpha(fixation, x, y),
                   background, "over"))
    origin_x, origin_y, modern_pixels = compose_ordered_layers(layers, background)
    assert (origin_x, origin_y) == (0, 0)
    np.testing.assert_allclose(modern_pixels, old_pixels, rtol=0, atol=4e-15)


def test_default_blend_remains_unchanged_and_additive_mode_is_explicit():
    assert Stimulus("probe").to_dict() == {
        "slot": "probe", "x_deg": 0., "y_deg": 0.
    }
    assert Stimulus("probe", blend="add").to_dict()["blend"] == "add"
    with pytest.raises(ValueError, match="blend"):
        Stimulus("probe", blend="multiply")

    a = np.full((3, 3), .5)
    target = np.full((3, 3), .55)
    full = np.ones((3, 3))
    _, _, blend = compose_ordered_layers([
        (0, 0, target, full, .5),
        (0, 0, target, full, .5, "add"),
    ], .5)
    np.testing.assert_allclose(blend, .60)


@pytest.mark.parametrize("name", OFFICIAL_WITH_OLD_SCENES)
@pytest.mark.parametrize("target", [0, 1])
@pytest.mark.parametrize("ring", [False, True])
def test_trials_declare_exact_layers_and_target_alternative_in_python(
    name, target, ring
):
    """A1 is the source of placements, not any TUI-coded experiment scene."""
    m = importlib.import_module("psychophysics_lab.experiments." + name)
    fields = m.SPEC.field_defaults()
    fields.update(
        auditory_cues=False, probe_vertical_offset_deg=.4,
        ellipse_centre_y_deg=.5, major_axis_y_deg=.6,
    )
    condition = dict(
        target=target, x_deg=.2, value="test", contrast=.02,
        aspect_ratio=.75, ring=ring, repeat=1,
    )
    events = m.trial_events(fields, condition)
    assert events[-1].kind == "response"
    if name.startswith("line_"):
        assert [v.slot for v in events[1].placements] == (
            ["flanker", "probe", "fixation"]
            if name == "line_position_flanker" else ["probe", "fixation"]
        )
        assert [v.blend for v in events[1].placements if v.slot == "probe"] == ["add"]
    else:
        for interval_index, target_slot in [(1, 0), (3, 1)]:
            expected = (["ellipse"] if ring else []) + (
                ["probe"] if target_slot == target else []
            ) + ["fixation"]
            assert [v.slot for v in events[interval_index].placements] == expected
            assert [v.blend for v in events[interval_index].placements
                    if v.slot == "probe"] == (["add"] if target_slot == target else [])
    assert all(v.slot != "first" and v.slot != "second"
               for event in events if hasattr(event, "placements")
               for v in event.placements)


@pytest.mark.parametrize("flanker_present,ring_present", [
    (False, False), (False, True), (True, False), (True, True),
])
def test_real_angular_viewport_layer_placement_matches_historical_pixels(
    flanker_present, ring_present
):
    """Exercise the actual display-angle and edge-clipping coordinate planner.

    This tests not only mathematical masks but independently cropped raster
    bounds and pixel-centre placement through the shipping compositor.
    No physical monitor, photometer, pyglet window or participant is required.
    """
    from types import SimpleNamespace
    from psychophysics_lab.core.presentation import (
        plan_visible_stimulus, render_values, render_layered_phase
    )
    from psychophysics_lab.core.timeline import Show

    profile = SimpleNamespace(
        physical_width_m=.16, physical_height_m=.12,
        viewing_distance_m=.5, geometry_status="unverified",
    )
    resolution = (320, 240)
    bg = .5
    old = parameters(DetectionScene)
    old.update(background=bg, contrast=.03,
               probe_present=True, probe_x_deg=.35, probe_y_deg=.25,
               probe_length_deg=1., probe_width_deg=.013,
               ring_present=ring_present, ring_radius_deg=.8,
               ring_y_deg=.25, ring_increment=.06, aspect_ratio=.75,
               flanker_present=flanker_present, flanker_cpd=2.)
    old_view, old_coords, steps = plan_visible_stimulus(
        profile, resolution, DetectionScene.SPEC, old, Stimulus("legacy")
    )
    old_image = render_values(
        DetectionScene.SPEC, old, pixels=old_view["raster_px"],
        coordinates=old_coords, pixel_steps=steps
    )

    fixation = parameters(GaussianSceneFixation) | {"background": bg}
    probe = parameters(ProbeLine) | {
        "background": bg, "display_contrast": .03/(1-bg),
    }
    ring = parameters(EllipseRing) | {
        "background": bg, "display_contrast": .06/(1-bg),
        "outer_radius_deg": .8, "aspect_ratio": .75,
    }
    flanker = parameters(FlankerGrating) | {
        "background": bg, "spatial_frequency_cpd": 2.,
    }
    placements = []
    if flanker_present:
        placements.append(Stimulus("flanker", -3., 0.))
    if ring_present:
        placements.append(Stimulus("ellipse", 0., .25))
    placements += [Stimulus("probe", .35, .25, blend="add"),
                   Stimulus("fixation")]
    phase = Show("comparison", duration=100, stimuli=tuple(placements))
    selected = {
        "flanker": ("flanker_grating", flanker),
        "ellipse": ("ellipse_ring", ring),
        "probe": ("probe_line", probe),
        "fixation": ("gaussian_scene_fixation", fixation),
    }
    px, py, image, _ = render_layered_phase(
        profile, resolution, phase, selected, bg
    )
    assert (px, py) == tuple(old_view["origin_px"])
    assert image.shape == old_image.shape
    np.testing.assert_allclose(image, old_image, rtol=0, atol=4e-14)
