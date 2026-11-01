"""A new modular ellipse study must not change old DetectionScene acquisition."""
import numpy as np
import pytest

from psychophysics_lab.core.layer_composition import compose_ordered_layers
from psychophysics_lab.stimulus_library import EllipseRing, ProbeLine, GaussianFixationSpot, FlankerGrating
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
    assert [p.slot for p in one] == ["ellipse", "probe", "fixation"]
    assert [p.slot for p in two] == ["ellipse", "fixation"]
    assert one[0].y_deg == values["ring_centre_y_deg"]
    assert one[1].y_deg == values["ring_centre_y_deg"]

    # A single scientist-authored mapping defines names *and* compatible
    # stimulus families, rather than duplicate STIMULUS_SLOTS/DEFAULTS.
    assert set(study.STIMULI) == {"ellipse", "probe", "fixation"}
    assert study.SPEC.stimulus_defaults == study.STIMULI
    assert study.SPEC.stimulus_slots["fixation"] == "fixation"


def test_scientist_controls_reach_stimulus_parameters_and_placements():
    from types import SimpleNamespace

    changed = study.SPEC.normalise_values(study.SPEC.field_defaults() | {
        "ring_radius_deg": 6, "ring_orientation_deg": 45,
        "ring_inset_deg": .3, "aspect_ratios": "0.5",
        "ring_centre_x_deg": 1.25, "ring_centre_y_deg": -.7,
        "probe_offset_x_deg": -.3, "probe_offset_y_deg": .4,
        "probe_length_deg": .6, "probe_width_deg": .07,
        "fixation_sigma_deg": .06, "fixation_display_contrast": .45,
        "background_intensity": .25, "ring_display_contrast": .5,
    }, use_config=False)
    condition = study.make_conditions(changed)[0] | {"target": 0, "contrast": .2}

    class StubRun:
        values = changed
        def stimulus_parameters(self, _slot, **overrides):
            return overrides

    parameters = study.prepare_stimuli(StubRun(), condition, {})
    assert parameters["ellipse"]["outer_radius_deg"] == 6
    assert parameters["ellipse"]["orientation_deg"] == 45
    assert parameters["ellipse"]["inner_inset_deg"] == .3
    assert parameters["ellipse"]["display_contrast"] == .5
    assert parameters["probe"]["display_contrast"] == .2
    assert parameters["probe"]["width_deg"] == .07
    assert parameters["fixation"]["sigma_deg"] == .06
    assert parameters["fixation"]["display_contrast"] == .45

    first, second = study.trial_events(changed, condition)[1::2]
    assert first.placements[0].x_deg == pytest.approx(1.25)
    assert first.placements[0].y_deg == pytest.approx(-.7)
    assert first.placements[1].x_deg == pytest.approx(.95)
    assert first.placements[1].y_deg == pytest.approx(-.3)
    assert [item.slot for item in second.placements] == ["ellipse", "fixation"]


def test_single_stimuli_mapping_rejects_unknowns_and_conflicts():
    from psychophysics_lab.researcher import experiment
    with pytest.raises(ValueError, match="both"):
        experiment(id="temp_ellipse", name="Bad", description="", procedure=None,
                   stimuli=study.STIMULI, stimulus_defaults=study.STIMULI)
    with pytest.raises(ValueError, match="slot name"):
        experiment(id="temp_ellipse", name="Bad", description="", procedure=None,
                   stimuli={"not-a-slot": "ellipse_ring"})


def test_rotating_ellipse_changes_mask_without_changing_sagittal_gamut():
    p = {field.key: field.default for field in EllipseRing.PARAMETERS}
    p.update(outer_radius_deg=6, aspect_ratio=.5, orientation_deg=90)
    x = np.array([[0., 0.]])
    y = np.array([[5.95, 6.2]])
    np.testing.assert_array_equal(EllipseRing.alpha(p, x, y), [[1., 0.]])


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


@pytest.mark.parametrize("method", ["adaptive", "constant_stimuli"])
def test_new_ellipse_synthetic_recording_for_both_methods(tmp_path, method):
    import csv
    from pathlib import Path
    from simulations.run import simulate
    from scripts.validate_run import validate_run

    repo_root = Path(__file__).resolve().parents[1]
    chosen = study.SPEC.field_defaults() | {
        "contrast_method": method,
        "aspect_ratios": "1",
        "staircases_per_condition": 1,
        "max_trials": 4,
        "fixed_contrasts": "0.01,0.02",
        "fixed_repetitions": 2,
    }
    artifact, _ = simulate(
        repo_root=repo_root, data_root=tmp_path / "recorded",
        experiment_id="ellipse_modular_centre", values=chosen,
        seed=131, analyse=False,
    )
    assert artifact.accepted_trials == 4
    assert not [check for check in validate_run(artifact.run_directory)
                if not check.passed]
    with artifact.trial_log_file.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert rows and len(rows[0]) == 20
    if method == "constant_stimuli":
        assert {float(row["presented_display_contrast"]) for row in rows} == {.01, .02}


def test_flanker_is_an_independent_positionable_grating_with_signed_gamut():
    p = {field.key: field.default for field in FlankerGrating.PARAMETERS}
    x = np.array([[0., .125, 2.6]])
    y = np.zeros_like(x)
    np.testing.assert_allclose(
        FlankerGrating.alpha(p, x, y), [[1, 1, 0]]
    )
    np.testing.assert_allclose(
        FlankerGrating.render(p, x, y), [[.5, .509, .5]]
    )
    assert FlankerGrating.geometry(p)["raster_extent_deg"] == 5.
    with pytest.raises(ValueError, match="gamut"):
        FlankerGrating.SPEC.validate_parameters(
            p | {"background": .005, "amplitude": .009}
        )
