"""Viewport clipping samples original coordinates, never a fitted replacement."""
from dataclasses import replace
import math
from types import SimpleNamespace
import sys

import numpy as np
import pytest

from psychophysics_lab.core import presentation as display
from psychophysics_lab.core.timeline import Stimulus, Show, CollectResponse, TrialTimeline
from psychophysics_lab.core.viewport import angular_viewport, stimulus_geometry
from psychophysics_lab.config.stimulus_parameters import document_for
from psychophysics_lab.stimuli.registry import get_stimulus


def profile():
    return SimpleNamespace(physical_width_m=.16, physical_height_m=.12,
                           viewing_distance_m=.5, geometry_status='unverified')


RESOLUTION = (320, 240)


def parameters(identity, **changes):
    stimulus = get_stimulus(identity)
    return stimulus, document_for(stimulus)['parameters'] | changes


def original_raster(p, extent, placement):
    """Independent legacy edge formula; modest arrays, used only as test oracle."""
    corners = []
    for centre, metres, limit in zip((placement.x_deg, placement.y_deg),
                                   (p.physical_width_m, p.physical_height_m), RESOLUTION):
        corners.append([round(limit/2 + p.viewing_distance_m*math.tan(math.radians(edge))/(metres/limit))
                        for edge in (centre-extent/2, centre+extent/2)])
    origin = tuple(pair[0] for pair in corners)
    size = tuple(pair[1]-pair[0] for pair in corners)
    return origin, size, display.display_degree_coordinates(p, RESOLUTION, size, origin, placement)


@pytest.mark.parametrize('identity', ['contrast_sensitivity_grating', 'sine_grating',
    'gabor_patch', 'teaching_gabor', 'oriented_line', 'square_patch', 'rectangle_patch',
    'ellipse_patch', 'annulus_patch', 'gaussian_dot', 'new_probe_vertical_line', 'detection_scene'])
@pytest.mark.parametrize('side', [-1, 1])
def test_visible_values_equal_crop_of_original_scientific_raster(identity, side):
    p = profile()
    edge = math.degrees(math.atan(p.physical_width_m/2/p.viewing_distance_m))
    placement = Stimulus('target', side*(edge-.25), .3)
    stimulus, params = parameters(identity)
    if identity == 'detection_scene':
        params |= {'probe_x_deg': side*.25, 'probe_y_deg': .4, 'probe_width_deg': .08,
                   'probe_length_deg': 1., 'ring_present': True, 'flanker_present': True}
    extent = stimulus_geometry(stimulus, params)['raster_extent_deg']
    old_origin, old_size, old_coordinates = original_raster(p, extent, placement)
    full = display.render_values(stimulus, params, pixels=old_size, coordinates=old_coordinates)
    view, coordinates, steps = display.plan_visible_stimulus(p, RESOLUTION, stimulus, params, placement)
    assert view['clipped']
    new = display.render_values(stimulus, params, pixels=view['raster_px'], coordinates=coordinates, pixel_steps=steps)
    x, y = np.subtract(view['origin_px'], old_origin)
    w, h = view['raster_px']
    np.testing.assert_array_equal(new, full[y:y+h, x:x+w])
    assert w <= RESOLUTION[0] and h <= RESOLUTION[1]


@pytest.mark.parametrize('identity', ['contrast_sensitivity_grating', 'detection_scene', 'oriented_line'])
def test_fully_visible_geometry_and_pixels_remain_exact(identity):
    stimulus, params = parameters(identity)
    params['size_deg'] = 4.
    if identity == 'contrast_sensitivity_grating':
        params['sigma_deg'] = .5
    placement = Stimulus('target', .5, -.25)
    old_origin, size, coordinates = original_raster(profile(), 4., placement)
    expected = display.render_values(stimulus, params, pixels=size, coordinates=coordinates)
    view, actual_coordinates, steps = display.plan_visible_stimulus(profile(), RESOLUTION, stimulus, params, placement)
    assert not view['clipped'] and steps is None
    assert tuple(view['origin_px']) == old_origin and tuple(view['raster_px']) == size
    actual = display.render_values(stimulus, params, pixels=size, coordinates=actual_coordinates)
    np.testing.assert_array_equal(actual, expected)


def test_sigma_five_cutoff_two_uses_twenty_degree_support_and_only_visible_pixels():
    stimulus, params = parameters('contrast_sensitivity_grating', sigma_deg=5., cutoff_sigmas=2.)
    calls = []
    def render(p, x, y):
        calls.append((x.copy(), y.copy()))
        return stimulus.render(p, x, y)
    measured = replace(stimulus, render=render)
    placement = Stimulus('target', 1., 0.)
    view, coords, steps = display.plan_visible_stimulus(profile(), RESOLUTION, measured, params, placement)
    image = display.render_values(measured, params, pixels=view['raster_px'], coordinates=coords)
    assert view['requested_extent_deg'] == 8.
    assert view['support_radius_deg'] == 10. and view['support_diameter_deg'] == 20.
    assert view['raster_extent_deg'] == 20. and view['clipped']
    assert image.shape == (240, 318) and len(calls) == 1
    # Absolute angle still comes from actual pixel centres, not a 20-degree fit.
    expected_x = np.degrees(np.arctan((2+np.arange(318)+.5-160)*(.16/320)/.5))-1.
    np.testing.assert_array_equal(calls[0][0][0], expected_x)
    outside = np.hypot(*coords) >= 10.
    assert outside.any() and np.all(image[outside] == params['background'])


@pytest.mark.parametrize('centre', [(50., 0.), (-50., 0.), (0., 50.), (0., -50.)])
def test_wholly_outside_aperture_is_rejected(centre):
    with pytest.raises(ValueError, match='wholly outside'):
        angular_viewport(profile(), RESOLUTION, 20., Stimulus('target', *centre))


def test_visible_padding_cannot_hide_an_invisible_grating_support():
    stimulus, params = parameters('contrast_sensitivity_grating', sigma_deg=.1, size_deg=8.)
    # The software square intersects the display, but its circular signal does not.
    with pytest.raises(ValueError, match='required stimulus support has no visible'):
        display.plan_visible_stimulus(profile(), RESOLUTION, stimulus, params, Stimulus('target', 11., 0.))


def test_fixation_cannot_hide_an_invisible_present_probe_but_catch_trial_is_allowed():
    stimulus, params = parameters('detection_scene', probe_x_deg=6., probe_y_deg=0.)
    position = Stimulus('target', 5., 0.)
    with pytest.raises(ValueError, match='required stimulus support has no visible'):
        display.plan_visible_stimulus(profile(), RESOLUTION, stimulus, params, position)
    display.plan_visible_stimulus(profile(), RESOLUTION, stimulus, params | {'probe_present': False}, position)


def test_zero_contrast_is_not_confused_with_invisible_geometry():
    stimulus, params = parameters('contrast_sensitivity_grating', contrast=0.)
    view, coords, _ = display.plan_visible_stimulus(profile(), RESOLUTION, stimulus, params, Stimulus('target'))
    assert np.all(display.render_values(stimulus, params, pixels=view['raster_px'], coordinates=coords) == .5)


def test_near_forward_plane_boundary_never_requests_a_huge_raster():
    view = angular_viewport(profile(), RESOLUTION, 179., Stimulus('target', 10., 10.))
    assert view['origin_px'] == [0, 0] and view['raster_px'] == list(RESOLUTION)
    assert view['clipped']


@pytest.mark.parametrize('extent,centre', [(float('nan'), 0), (float('inf'), 0), (0, 0), (-1, 0), (8, float('nan'))])
def test_nonfinite_or_nonpositive_geometry_still_fails(extent, centre):
    with pytest.raises(ValueError):
        angular_viewport(profile(), RESOLUTION, extent, Stimulus('target', centre, 0))


def test_actual_prepare_records_requested_and_displayed_geometry_without_offscreen_upload(monkeypatch):
    textures = []
    class Texture:
        def __init__(self, array):
            textures.append(array.copy())
        def delete(self):
            pass
    monkeypatch.setitem(sys.modules, 'pyglet', SimpleNamespace())
    monkeypatch.setattr(display, 'FloatingTexture', Texture)
    presentation = object.__new__(display.Presentation)
    presentation.profile, presentation.resolution = profile(), RESOLUTION
    stimulus, params = parameters('contrast_sensitivity_grating', sigma_deg=5., cutoff_sigmas=2.)
    timeline = TrialTimeline((Show('grating', stimuli=(Stimulus('target', 1., 0.),), duration=100),
                              CollectResponse(actions=('left', 'right'))))
    presentation.prepare(timeline, {'target': (stimulus.id, params)})
    geometry = presentation._phase_geometry['grating'][0]
    assert geometry['clipped'] and geometry['support_diameter_deg'] == 20.
    assert geometry['requested_centre_deg'] == [1., 0.]
    assert geometry['displayed_bounds_deg'] and geometry['requested_bounds_deg']
    assert textures[0].shape == (240, 318)
    assert presentation._rendered['grating'][0][:2] == (2, 0)
