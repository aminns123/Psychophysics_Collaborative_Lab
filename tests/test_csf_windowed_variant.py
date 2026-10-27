"""Circular-windowed CSF is scientifically distinct but shares its trial engine.

No physical photometric/timing qualification is implied by numerical tests.
"""
import csv
import json
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.stimulus_library import (
    CircularWindowedSinusoidalGrating,
    ContrastSensitivityGrating,
)
from psychophysics_lab.experiments import (
    contrast_sensitivity as gaussian_csf,
    contrast_sensitivity_windowed as windowed_csf,
)
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.core.viewport import stimulus_geometry
from psychophysics_lab.data.trials import TRIAL_COLUMNS


def params(**overrides):
    return {field.key: field.default
            for field in CircularWindowedSinusoidalGrating.PARAMETERS} | overrides


def test_new_stimulus_and_experiment_are_separate_registered_public_components():
    stimulus = get_stimulus("circular_windowed_sinusoidal_grating")
    exp = get_experiment("contrast_sensitivity_windowed")
    original = get_experiment("contrast_sensitivity")
    assert stimulus is CircularWindowedSinusoidalGrating.SPEC
    assert exp.id != original.id
    assert exp.stimulus_slots["grating"] == stimulus.id
    assert original.stimulus_slots["grating"] == ContrastSensitivityGrating.SPEC.id
    assert exp.data_directory_name == "contrast_sensitivity_windowed"
    assert original.data_directory_name == "contrast_sensitivity"
    assert {"adaptive", "constant_stimuli"} <= {
        f.default for f in exp.fields if f.key == "contrast_method"
    } | {"constant_stimuli"}
    assert "grating_sigma_deg" not in {f.key for f in exp.fields}
    assert "aperture_diameter_deg" in {f.key for f in exp.fields}
    assert exp.source_paths[0].endswith("contrast_sensitivity_windowed.py")
    assert set(exp.trial_column_overrides) == set(original.trial_column_overrides)


def test_windowed_csf_uses_exact_same_trials_conditions_and_updates_as_original():
    assert windowed_csf.make_trial is gaussian_csf.make_trial
    assert windowed_csf.make_conditions is gaussian_csf.make_conditions
    assert windowed_csf.choose_condition is gaussian_csf.choose_condition
    assert windowed_csf.update_experiment is gaussian_csf.update_experiment
    assert windowed_csf.interpret_response is gaussian_csf.interpret_response
    assert windowed_csf.finish_experiment is gaussian_csf.finish_experiment
    assert windowed_csf.make_fixed_schedule is gaussian_csf.make_fixed_schedule
    assert windowed_csf.fixed_contrast_levels is gaussian_csf.fixed_contrast_levels
    assert windowed_csf.SPEC.adaptive == gaussian_csf.SPEC.adaptive


def test_circle_is_full_amplitude_until_edge_fade_and_background_outside():
    p = params(size_deg=2., fade_width_deg=.2,
               spatial_frequency_cpd=1., contrast=.6, background=.37)
    x = np.asarray([.25, .75, .9, 1., 1.2])
    y = np.zeros_like(x)
    response = CircularWindowedSinusoidalGrating.render(p, x, y)
    gain = np.asarray([1., 1., .5, 0., 0.])
    expected = .37 + (.6/2) * gain * np.sin(2*np.pi*x)
    np.testing.assert_allclose(response, expected, atol=1e-14)
    xx, yy = np.meshgrid(np.linspace(-1.2, 1.2, 81),
                         np.linspace(-1.2, 1.2, 81))
    image = CircularWindowedSinusoidalGrating.render(p, xx, yy)
    assert np.all(image[np.hypot(xx, yy) >= 1.] == .37)
    # Square corners in an otherwise-visible floating raster are background.
    assert image[0, 0] == .37
    assert image[-1, -1] == .37


@pytest.mark.parametrize("style,fade", [("hard_edge", 0.), ("hard_edge", .3),
                                        ("soft_edge", 0.)])
def test_hard_edge_is_immediate_and_does_not_attenuate_centre(style, fade):
    p = params(size_deg=2., edge_mode=style, fade_width_deg=fade,
               spatial_frequency_cpd=1., contrast=.6, background=.37)
    points = np.asarray([.25, .9, 1.0, 1.01])
    values = CircularWindowedSinusoidalGrating.render(p, points,
                                                      np.zeros_like(points))
    gain = np.asarray([1., 1., 0., 0.])
    np.testing.assert_allclose(values, .37 + .3*gain*np.sin(2*np.pi*points))


def test_geometry_and_invalid_fade_are_defined_in_degrees():
    spec = CircularWindowedSinusoidalGrating.SPEC
    result = stimulus_geometry(spec, spec.validate_parameters(params(
        size_deg=1., fade_width_deg=.1
    )))
    assert result["support_radius_deg"] == .5
    assert result["support_diameter_deg"] == 1.
    assert result["taper_start_radius_deg"] == .4
    with pytest.raises(ValueError, match="cannot exceed"):
        spec.validate_parameters(params(size_deg=1., fade_width_deg=.6))
    settings = windowed_csf.SPEC.field_defaults() | {
        "aperture_diameter_deg": 1., "fade_width_deg": .6
    }
    assert list(windowed_csf.validate_settings(settings))
    with pytest.raises(ValueError, match="cannot exceed"):
        windowed_csf.SPEC.normalise_values(settings)
    with pytest.raises(ValueError, match="digital range"):
        spec.validate_parameters(params(background=.1, contrast=.5))


def test_original_gaussian_csf_defaults_and_algorithm_are_unchanged():
    old = gaussian_csf.SPEC.normalise_values({})
    assert old["grating_sigma_deg"] == .5
    assert old["grating_cutoff_sigmas"] == 3.
    assert "aperture_diameter_deg" not in old
    new = windowed_csf.SPEC.normalise_values({})
    assert new["aperture_diameter_deg"] == 3.
    assert new["edge_mode"] == "soft_edge"
    assert new["fade_width_deg"] == .15
    assert "grating_sigma_deg" not in new


def test_real_windowed_fixed_run_preserves_canonical_saved_data(tmp_path):
    from scripts.validate_run import validate_run
    from simulations.run import simulate

    root = Path(__file__).resolve().parents[1]
    changes = {
        "contrast_method": "constant_stimuli",
        "frequencies_cpd": "2,4",
        "fixed_contrasts": "0.05,0.1",
        "fixed_repetitions": 3,
        "max_trials": 12,
        "aperture_diameter_deg": 1.,
        "fade_width_deg": .1,
    }
    result, _ = simulate(
        experiment_id="contrast_sensitivity_windowed",
        data_root=tmp_path / "synthetic",
        repo_root=root,
        seed=19,
        values=changes,
        analyse=False,
    )
    assert result.status == "completed"
    assert result.accepted_trials == 12
    with result.trial_log_file.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream, delimiter="\t"))
    assert tuple(records[0]) == TRIAL_COLUMNS
    assert len(records) == 12
    assert {float(row["stimulus_condition"]) for row in records} == {2., 4.}
    assert {float(row["presented_display_contrast"]) for row in records} == {.05, .1}
    assert all(row["staircase_id"] == "" for row in records)
    manifest = json.loads((result.run_directory / "manifest.json").read_text(encoding="utf-8"))
    resolution = json.loads((result.run_directory / "resolved_experiment.json").read_text(encoding="utf-8"))
    assert manifest["experiment_id"] == "contrast_sensitivity_windowed"
    assert manifest["trial_selection_method"] == "constant_stimuli"
    assert manifest["adaptive_algorithm"] is None
    assert resolution["grating_stimulus_id"] == "circular_windowed_sinusoidal_grating"
    assert resolution["grating_flat_radius_deg"] == .4
    assert "gaussian_sigma_deg" not in resolution
    assert "grating_sigma_deg" not in resolution
    assert "grating_cutoff_sigmas" not in resolution
    assert len(resolution["schedule"]) == 12
    problems = [item for item in validate_run(result.run_directory)
                if not item.passed]
    assert not problems, [(item.name, item.detail) for item in problems]
