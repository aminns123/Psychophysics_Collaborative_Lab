"""A new modular ellipse study must not change old DetectionScene acquisition."""
import numpy as np
import pytest

from psychophysics_lab.core.layer_composition import compose_ordered_layers
from psychophysics_lab.stimulus_library import EllipseRing, ProbeLine, LayerGaussianFixation
from psychophysics_lab.experiments import ellipse_modular_centre as study


def test_overlap_order_and_absent_background_pixels():
    # Both transparent layers were rendered against the same background.
    ring = np.array([[.5, .7, .5]])
    ring_alpha = np.array([[0, 1, 0]], dtype=float)
    probe = np.array([[.8]])
    px, py, composed = compose_ordered_layers([
        (0, 0, ring, ring_alpha, .5),
        (1, 0, probe, np.array([[1.]]), .5),
    ], .5)
    assert (px, py) == (0, 0)
    np.testing.assert_allclose(composed, [[.5, .8, .5]])
    _, _, reversed_layers = compose_ordered_layers([
        (1, 0, probe, np.array([[1.]]), .5),
        (0, 0, ring, ring_alpha, .5),
    ], .5)
    np.testing.assert_allclose(reversed_layers, [[.5, .7, .5]])


def test_fractional_subpixel_coverage_never_erases_other_layers():
    _, _, result = compose_ordered_layers([
        (0, 0, np.array([[.7]]), np.array([[1.]]), .5),
        (0, 0, np.array([[.6]]), np.array([[.25]]), .5),
    ], .5)
    # 0.6 is a line drawn with 25% coverage over .5 -> foreground .9.
    assert result[0, 0] == pytest.approx(.75)


@pytest.mark.parametrize("invalid", [-.01, 1.01, np.nan])
def test_bad_alpha_rejected_not_clipped(invalid):
    with pytest.raises(ValueError, match="alpha"):
        compose_ordered_layers([(0, 0, np.array([[.5]]),
                                 np.array([[invalid]]), .5)], .5)


def test_composite_requires_one_background():
    with pytest.raises(ValueError, match="background"):
        compose_ordered_layers([(0, 0, np.array([[.6]]),
                                 np.array([[1.]]), .25)], .5)


def test_ellipse_ring_matches_axial_inset_and_six_degree_radius():
    p = {f.key:f.default for f in EllipseRing.PARAMETERS}
    p.update(background=.25, display_contrast=.5, outer_radius_deg=6,
             aspect_ratio=.5, inner_inset_deg=.16)
    EllipseRing.SPEC.validate_parameters(p)
    x = np.array([[5.95, 5.0, 6.1, 0.]])
    y = np.zeros_like(x)
    np.testing.assert_array_equal(EllipseRing.alpha(p, x, y), [[1, 0, 0, 0]])
    np.testing.assert_allclose(EllipseRing.render(p, x, y), [[.625, .25, .25, .25]])
    assert EllipseRing.geometry(p)["raster_extent_deg"] >= 12
    with pytest.raises(ValueError, match="inner semi-axes"):
        EllipseRing.SPEC.validate_parameters(p | {"inner_inset_deg": 4})


def test_probe_alpha_has_subpixel_coverage():
    p = {f.key:f.default for f in ProbeLine.PARAMETERS}
    p.update(background=.25, display_contrast=.5)
    x = np.array([[0., .05], [0., .05]])
    y = np.array([[0., 0.], [.1, .1]])
    coverage = ProbeLine.alpha(p, x, y, pixel_steps=(np.full_like(x, .05), np.full_like(y, .05)))
    assert coverage[0, 0] == pytest.approx(.013/.05)
    assert coverage[0, 1] == 0
    assert ProbeLine.render(p, x, y, pixel_steps=(np.full_like(x, .05), np.full_like(y, .05)))[0, 0] > .25


def test_new_study_is_independent_and_uses_contrast_not_raw_increment():
    values = study.SPEC.normalise_values(study.SPEC.field_defaults(), use_config=False)
    assert values["ring_radius_deg"] == 6
    assert values["ring_display_contrast"] == pytest.approx(.2)
    assert values["starting_probe_contrast"] == pytest.approx(.04)
    assert study.SPEC.id == "ellipse_modular_centre"
    cond = study.make_conditions(values)[0] | {"contrast": .05, "target": 0}
    events = study.trial_events(values, cond)
    assert [a.name for a in events] == ["fixation", "interval_one", "inter_interval", "interval_two", "answer"]
    one, two = events[1].placements, events[3].placements
    assert [p.slot for p in one] == ["ring", "probe", "fixation"]
    assert [p.slot for p in two] == ["ring", "fixation"]
    assert one[0].y_deg == values["ellipse_centre_y_deg"]
    assert one[1].y_deg == values["ellipse_centre_y_deg"]


def test_constant_stimuli_plan_and_invalid_geometry():
    values = study.SPEC.normalise_values(study.SPEC.field_defaults() | {
        "contrast_method": "constant_stimuli", "aspect_ratios": "1",
        "fixed_contrasts": "0.1,0.2", "fixed_repetitions": 2,
        "max_trials": 4,
    }, use_config=False)
    schedule = study.make_fixed_schedule(values, seed=5)
    assert len(schedule) == 4
    assert {item["contrast"] for item in schedule} == {.1, .2}
    assert {item["target"] for item in schedule} == {0, 1}
    with pytest.raises(ValueError, match="inner ellipse"):
        study.SPEC.normalise_values(values | {
            "ring_radius_deg": .2,
            "ring_inset_deg": .16,
            "aspect_ratios": ".5",
        }, use_config=False)


def test_old_scene_still_registered_under_legacy_id():
    from psychophysics_lab.stimulus_library import DetectionScene
    assert DetectionScene.SPEC.id == "detection_scene"
    assert DetectionScene.SPEC.layer_alpha is None
