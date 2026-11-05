"""Independent point/area/algebra checks for the baseline's stimulus families."""
import json
import math

import numpy as np
import pytest

from psychophysics_lab.stimuli.registry import get_stimulus, list_stimuli
from psychophysics_lab.core.layer_composition import compose_ordered_layers


def scalar(identity, p, x, y):
    """Scalar equations from the declared geometry; no production math helpers."""
    b = p.get("background", .5)
    angle = math.radians(p.get("orientation_deg", 0))
    u, v = x * math.cos(angle) + y * math.sin(angle), -x * math.sin(angle) + y * math.cos(angle)
    if identity == "oriented_line":
        covered = abs(u) <= p["width_deg"] / 2 and abs(v) <= p["length_deg"] / 2
    elif identity == "square_patch":
        covered = max(abs(x), abs(y)) <= p["side_deg"] / 2
    elif identity == "rectangle_patch":
        covered = abs(x) <= p["width_deg"] / 2 and abs(y) <= p["height_deg"] / 2
    elif identity in {"ellipse_patch", "annulus_patch"}:
        distance = (x / p["radius_x_deg"])**2 + (y / p["radius_y_deg"])**2
        covered = distance <= 1 and (identity == "ellipse_patch" or distance >= p["inner_ratio"]**2)
    elif identity in {"example_stimulus", "new_probe_vertical_line"}:
        covered = abs(x - p["offset_deg"]) < p["line_width_deg"] / 2 and abs(y) < p["line_length_deg"] / 2
    elif identity == "vertical_line_probe":
        covered = abs(x) <= p["width_deg"] / 2 and abs(y) <= p["length_deg"] / 2
    elif identity == "fixation_cross":
        covered = ((abs(x) <= p["arm_length_deg"] / 2 and abs(y) <= p["width_deg"] / 2)
                   or (abs(y) <= p["arm_length_deg"] / 2 and abs(x) <= p["width_deg"] / 2))
    elif identity in {"gaussian_dot", "gaussian_fixation", "gaussian_scene_fixation", "gaussian_fixation_spot"}:
        r = math.hypot(x, y)
        envelope = math.exp(-.5 * (r / p["sigma_deg"])**2)
        if identity in {"gaussian_dot", "gaussian_fixation_spot"} and r > 4 * p["sigma_deg"]:
            envelope = 0.
        peak = (p["intensity"] if identity == "gaussian_dot" else
                b + p["display_contrast"] * (1 - b) if identity == "gaussian_fixation_spot" else
                min(1., b + p["increment"]))
        return b + (peak - b) * envelope
    elif identity == "ellipse_ring":
        a, c, inset = p["outer_radius_deg"], p["outer_radius_deg"] * p["aspect_ratio"], p["inner_inset_deg"]
        covered = ((u / a)**2 + (v / c)**2 <= 1 and (u / (a - inset))**2 + (v / (c - inset))**2 >= 1)
        return b + covered * p["display_contrast"] * (1 - b)
    elif identity == "flanker_grating":
        covered = abs(x) <= p["width_deg"] / 2 and abs(y) <= p["height_deg"] / 2
        return b + covered * p["amplitude"] * math.sin(math.tau * p["spatial_frequency_cpd"] * x)
    elif identity in {"sine_grating", "gabor_patch", "teaching_gabor"}:
        phase = math.tau * p["spatial_frequency_cpd"] * u + math.radians(p["phase_deg"])
        if identity != "teaching_gabor" and max(abs(x), abs(y)) > p["size_deg"] / 2:
            return .5
        sigma = p["size_deg"] / 6 if identity == "teaching_gabor" else p.get("sigma_deg", 1.)
        envelope = 1. if identity == "sine_grating" else math.exp(-(x*x + y*y) / (2 * sigma*sigma))
        carrier = math.sin(phase) if identity == "sine_grating" else math.cos(phase)
        return .5 + p["contrast"] / 2 * envelope * carrier
    elif identity in {"contrast_sensitivity_grating", "circular_windowed_sinusoidal_grating"}:
        r = math.hypot(x, y)
        radius = p["size_deg"] / 2 if identity.startswith("circular") else p["sigma_deg"] * p["cutoff_sigmas"]
        fade = p["fade_width_deg"] if identity.startswith("circular") else p["sigma_deg"]
        if r >= radius:
            return b
        taper = 1.
        if r > radius - fade:
            taper = (1 + math.cos(math.pi * (r - (radius - fade)) / fade)) / 2
        envelope = 1. if identity.startswith("circular") else math.exp(-r*r / (2 * p["sigma_deg"]**2))
        return b + p["contrast"] / 2 * taper * envelope * math.sin(math.tau * p["spatial_frequency_cpd"] * x)
    elif identity == "composed_scene":
        # Independently evaluate its default single fixation, including the
        # drawing's declared full arm length rather than an assumed radius.
        scene = json.loads(p["scene_json"])
        d = scene["drawings"][0]["parameters"]
        assert scene["drawings"][0]["kind"] == "fixation"
        covered = ((abs(x) <= d["length_deg"] / 2 and abs(y) <= d["width_deg"] / 2)
                   or (abs(y) <= d["length_deg"] / 2 and abs(x) <= d["width_deg"] / 2))
        return d["intensity"] if covered else scene["background"]
    else:
        raise AssertionError("Missing independent oracle: " + identity)
    return p["intensity"] if covered else b


POINT_STIMULI = [s.id for s in list_stimuli() if s.render is not None and s.id != "probe_line"]


@pytest.mark.parametrize("identity", POINT_STIMULI)
def test_all_point_renderers_against_scalar_equations(identity):
    spec = get_stimulus(identity)
    p = {field.key: field.default for field in spec.parameters}
    if "background" in p:
        p["background"] = .83  # Includes declared legacy clipped fixation peaks.
    if "orientation_deg" in p:
        p["orientation_deg"] = 37.
    if "aspect_ratio" in p:
        p["aspect_ratio"] = .65
    if "phase_deg" in p:
        p["phase_deg"] = 43.
    rng = np.random.default_rng(2761)
    points = [(0., 0.), (.02, 0.), (.1, 0.), (.001, .001), (.2, .17), (8., 8.)]
    points += list(zip(rng.uniform(-3, 3, 80), rng.uniform(-3, 3, 80)))
    x, y = (np.asarray(values).reshape(1, -1) for values in zip(*points))
    expected = np.array([scalar(identity, p, a, b) for a, b in points]).reshape(1, -1)
    np.testing.assert_allclose(spec.render(p, x, y), expected, atol=2e-14, rtol=2e-14)


@pytest.mark.parametrize("offset", [0., .002, -.0047])
def test_probe_subpixel_coverage_conserves_continuous_area(offset):
    spec = get_stimulus("probe_line")
    p = {field.key: field.default for field in spec.parameters}
    p.update(width_deg=.0137, length_deg=.317, background=.72, display_contrast=.3)
    pitch = .01
    x, y = np.meshgrid(np.arange(-.5, .5, pitch) + offset, np.arange(-.5, .5, pitch) - offset)
    image = spec.render(p, x, y, pixel_steps=(pitch, pitch))
    coverage = (image - .72) / (.3 * .28)
    assert coverage.sum() * pitch**2 == pytest.approx(.0137 * .317, rel=2e-13)
    assert image.min() >= .72 and image.max() <= .804 + 1e-14


def test_ordered_over_and_add_against_foreground_equation_and_gamut_rejection():
    rng = np.random.default_rng(9001)
    for _ in range(40):
        background = rng.uniform(.2, .4)
        alpha1, alpha2 = rng.random((2, 5, 7))
        foreground1, foreground2 = rng.uniform(.4, .6, (2, 5, 7))
        layer1 = background * (1-alpha1) + foreground1 * alpha1
        layer2 = background * (1-alpha2) + foreground2 * alpha2
        for mode in ("over", "add"):
            layers = [(0, 0, layer1, alpha1, background), (0, 0, layer2, alpha2, background, mode)]
            actual = compose_ordered_layers(layers, background)[2]
            expected = (layer1 * (1-alpha2) + foreground2 * alpha2 if mode == "over"
                        else layer1 + alpha2 * (foreground2-background))
            np.testing.assert_allclose(actual, expected, atol=3e-16)
    for bad in (np.nan, np.inf, -.01, 1.01):
        with pytest.raises(ValueError):
            compose_ordered_layers([(0, 0, np.array([[bad]]), None, .5)], .5)
    with pytest.raises(ValueError, match="gamut"):
        compose_ordered_layers([(0, 0, np.ones((1, 1)), np.ones((1, 1)), .5),
                                (0, 0, np.ones((1, 1)), np.ones((1, 1)), .5, "add")], .5)
