"""Scientific Gabor support, legacy identity and explicit digital fade controls."""
import numpy as np
import pytest

from psychophysics_lab.stimulus_library import GaborPatch, TeachingGabor


@pytest.mark.parametrize("cls", [GaborPatch, TeachingGabor])
def test_one_degree_flat_hard_edge_has_full_carrier_amplitude_inside(cls):
    params = {f.key: f.default for f in cls.PARAMETERS}
    params.update(size_deg=1.0, envelope_mode="flat_hard_edge",
                  contrast=1.0, orientation_deg=0., phase_deg=0.,
                  spatial_frequency_cpd=2.)
    x = np.asarray([-.6, -.49, 0, .49, .6])
    y = np.zeros_like(x)
    value = cls.render(params, x, y)
    assert value[0] == value[-1] == .5
    assert value[2] == 1.0
    np.testing.assert_allclose(
        value[1:4], .5 + .5*np.cos(2*np.pi*2*x[1:4]),
        atol=1e-15,
    )


@pytest.mark.parametrize("cls", [GaborPatch, TeachingGabor])
def test_explicit_fade_width_is_in_degrees_and_zero_outside(cls):
    params = {f.key: f.default for f in cls.PARAMETERS}
    params.update(size_deg=1.0, envelope_mode="edge_fade",
                  fade_width_deg=.1, contrast=1., orientation_deg=0.,
                  phase_deg=0., spatial_frequency_cpd=2.)
    x = np.asarray([0., .4, .45, .5, .51, 1.])
    values = cls.render(params, x, np.zeros_like(x))
    envelope = np.asarray([1., 1., .5, 0., 0., 0.])
    expected = .5 + .5*envelope*np.cos(2*np.pi*2*x)
    np.testing.assert_allclose(values, expected, atol=1e-14)


@pytest.mark.parametrize("cls", [GaborPatch, TeachingGabor])
def test_legacy_gaussian_math_remains_identical_and_old_presets_accepted(cls):
    params = {f.key: f.default for f in cls.PARAMETERS}
    historical = {k: v for k, v in params.items()
                  if k not in {"envelope_mode", "fade_width_deg"}}
    normalised = cls.SPEC.validate_parameters(historical)
    assert normalised["envelope_mode"] == "legacy_gaussian"
    assert normalised["fade_width_deg"] == .1
    x = np.asarray([0., .3, .6])
    y = np.asarray([0., .2, 0.])
    result = cls.render(normalised, x, y)
    theta = np.deg2rad(normalised["orientation_deg"])
    coord = x*np.cos(theta)+y*np.sin(theta)
    wave = np.cos(
        2*np.pi*normalised["spatial_frequency_cpd"]*coord
        + np.deg2rad(normalised["phase_deg"])
    )
    sigma = (normalised["size_deg"] / 6 if cls is TeachingGabor
             else normalised["sigma_deg"])
    expected = .5 + .5*normalised["contrast"]*np.exp(
        -(x*x+y*y)/(2*sigma*sigma))*wave
    if cls is GaborPatch:
        mask = ((np.abs(x) <= normalised["size_deg"]/2)
                & (np.abs(y) <= normalised["size_deg"]/2))
        expected = np.where(mask, expected, .5)
    np.testing.assert_allclose(result, expected, atol=1e-15)
    np.testing.assert_array_equal(cls.render(historical, x, y), result)


@pytest.mark.parametrize("cls", [GaborPatch, TeachingGabor])
def test_out_of_range_fade_is_rejected_for_fade_mode_only(cls):
    params = {f.key: f.default for f in cls.PARAMETERS}
    params.update(size_deg=1., fade_width_deg=.6, envelope_mode="edge_fade")
    with pytest.raises(ValueError, match="at most half"):
        cls.SPEC.validate_parameters(params)
    params["envelope_mode"] = "flat_hard_edge"
    assert cls.SPEC.validate_parameters(params)["envelope_mode"] == "flat_hard_edge"
