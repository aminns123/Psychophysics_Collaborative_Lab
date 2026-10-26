"""The public CSF grating's Gaussian sigma is not an infinite visible tail.

These are renderer-level tests: preview and floating display use the *same*
scientific pixel values before display encoding. No physical luminance or
photon timing is inferred from their results.
"""
import numpy as np
import pytest

from psychophysics_lab.core.presentation import render_values
from psychophysics_lab.experiments import contrast_sensitivity as csf
from psychophysics_lab.stimulus_library import ContrastSensitivityGrating


def default_parameters(**selected):
    return {f.key: f.default for f in ContrastSensitivityGrating.PARAMETERS} | selected


@pytest.mark.parametrize("sigma", [0.2, 0.5, 1.0])
@pytest.mark.parametrize("cutoff", [2.0, 2.5, 3.0])
def test_exact_background_outside_selected_radial_support(sigma, cutoff):
    params = default_parameters(
        background=0.37,
        contrast=0.6,
        sigma_deg=sigma,
        cutoff_sigmas=cutoff,
        size_deg=8.0,
        spatial_frequency_cpd=1.37,
    )
    # A raster is a square, but the scientific support must be circular.
    grid = np.linspace(-4, 4, 321)
    xx, yy = np.meshgrid(grid, grid)
    image = ContrastSensitivityGrating.render(params, xx, yy)
    outside = np.hypot(xx, yy) >= sigma * cutoff
    assert outside.any()
    assert np.all(image[outside] == params["background"])
    assert not np.isnan(image).any()
    assert np.isfinite(image).all()
    assert np.max(np.abs(image)) <= 1.0
    assert np.any(image[~outside] != params["background"])


@pytest.mark.parametrize("cutoff", [2., 3., 4.])
def test_gaussian_is_unchanged_inside_smooth_taper(cutoff):
    params = default_parameters(
        sigma_deg=0.5, cutoff_sigmas=cutoff,
        background=.27, contrast=.34, spatial_frequency_cpd=1.33,
        size_deg=8.,
    )
    x = np.array([0., .25, .5, (cutoff - 1.) * .5 * .95])
    y = np.zeros_like(x)
    actual = ContrastSensitivityGrating.render(params, x, y)
    expected = params["background"] + .5 * params["contrast"] * np.exp(
        -(x*x)/(2 * params["sigma_deg"]**2)
    ) * np.sin(2*np.pi*params["spatial_frequency_cpd"]*x)
    np.testing.assert_allclose(actual, expected, rtol=1e-13, atol=1e-14)


def test_taper_is_smooth_and_goes_to_exact_background_including_at_edge():
    params = default_parameters(
        sigma_deg=.5, cutoff_sigmas=3., background=.33,
        contrast=.4, spatial_frequency_cpd=.83
    )
    radius = params["sigma_deg"] * params["cutoff_sigmas"]
    locations = np.array([radius - 1e-4, radius - 1e-5, radius, radius + 1e-5, radius + 1e-4])
    image = ContrastSensitivityGrating.render(params, locations, np.zeros_like(locations))
    assert image[2] == params["background"]
    assert np.array_equal(image[2:], np.full(3, params["background"]))
    assert abs(image[1]-params["background"]) < abs(image[0]-params["background"])
    assert abs(image[0]-params["background"]) < 1e-6


def test_real_raster_preparation_has_no_residual_patch_tails():
    stimulus = ContrastSensitivityGrating.SPEC
    params = default_parameters(
        background=.41, sigma_deg=.5, cutoff_sigmas=3.,
        spatial_frequency_cpd=1.25, contrast=.35
    )
    raster = render_values(stimulus, params, pixels=(201,201))
    grid = (np.arange(201) + .5 - 201/2) * params["size_deg"] / 201
    xx, yy = np.meshgrid(grid, grid)
    outside = np.hypot(xx, yy) >= params["sigma_deg"] * params["cutoff_sigmas"]
    assert np.all(raster[outside] == .41)
    assert (raster[0, :] == .41).all()
    assert (raster[-1, :] == .41).all()
    assert (raster[:, 0] == .41).all()
    assert (raster[:, -1] == .41).all()


def test_support_expands_minimum_raster_without_changing_requested_parameters():
    from psychophysics_lab.core.viewport import stimulus_geometry
    stimulus = ContrastSensitivityGrating.SPEC
    params = default_parameters(size_deg=8., sigma_deg=5., cutoff_sigmas=2.)
    assert stimulus.validate_parameters(params) == params
    geometry = stimulus_geometry(stimulus, params)
    assert geometry["support_diameter_deg"] == 20.
    assert geometry["raster_extent_deg"] == 20.
    assert params["size_deg"] == 8.


def test_experiment_selected_sigma_and_cutoff_reach_actual_grating():
    values = csf.SPEC.normalise_values(csf.SPEC.field_defaults() | {
        "grating_sigma_deg": .7,
        "grating_cutoff_sigmas": 2.5,
        "background_intensity": .38
    })

    class Run:
        def __init__(self):
            self.values = values
        def stimulus_parameters(self, slot, **params):
            return params

    params = csf.prepare_stimuli(Run(), {
        "frequency_cpd": 2.25, "contrast": .25
    }, {})["grating"]
    assert params["sigma_deg"] == .7
    assert params["cutoff_sigmas"] == 2.5
    assert params["background"] == .38
    assert params["spatial_frequency_cpd"] == 2.25
    assert params["contrast"] == .25
    assert csf.SPEC.field_defaults()["grating_cutoff_sigmas"] == 3.0


def test_exported_csf_preview_expands_to_full_scientific_support(tmp_path, monkeypatch):
    """Preview and physical presentation must use the same support extent.

    Direct render_values still permits intentionally requested cropped rasters;
    preview_stimulus's default appearance image depicts the complete support.
    """
    from psychophysics_lab.core import presentation
    from matplotlib.image import imread

    params = default_parameters(size_deg=8., sigma_deg=5., cutoff_sigmas=2.,
                                contrast=.8, background=.5,
                                spatial_frequency_cpd=1.25)
    observed = []
    actual = presentation.render_pixels

    def record(stimulus, parameters, **kwargs):
        observed.append(kwargs.get("extent_deg"))
        return actual(stimulus, parameters, **kwargs)

    monkeypatch.setattr(presentation, "render_pixels", record)
    target = tmp_path / "full_scientific_support.png"
    presentation.preview_stimulus("contrast_sensitivity_grating", params, target)

    assert observed == [20.]
    pixels = imread(target)
    # A full-radius circular cutoff returns to exact background at all
    # boundaries, rather than showing the nonzero central 8-degree crop.
    assert pixels.shape[:2] == (256, 256)
    assert np.max(np.abs(pixels[0, :, :3] - .5)) <= 2/255
    assert np.max(np.abs(pixels[-1, :, :3] - .5)) <= 2/255
    assert np.max(np.abs(pixels[:, 0, :3] - .5)) <= 2/255
    assert np.max(np.abs(pixels[:, -1, :3] - .5)) <= 2/255
    assert np.max(pixels[:, :, 0]) - np.min(pixels[:, :, 0]) > .1
