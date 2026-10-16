"""Shared static-raster presentation/input service; hardware imports remain lazy.

This teaching contract is self-paced. Software flip/key times are never described
as measured photon onset or independently verified input latency.
"""
from dataclasses import dataclass
import time
import numpy as np
from ..stimuli.registry import get_stimulus
from ..stimuli.geometry import physical_length_for_visual_angle
from ..stimuli.spatial_calibration import resolve_spatial_geometry


@dataclass(frozen=True)
class Response:
    alternative: int
    key: str
    reaction_time_s: float


def render_pixels(stimulus, parameters, *, pixels=(256, 256), extent_deg=None):
    parameters = stimulus.validate_parameters(parameters)
    extent = extent_deg or parameters[stimulus.extent_parameter]
    width, height = pixels
    x = (np.arange(width) + .5 - width / 2) * extent / width
    y = (np.arange(height) + .5 - height / 2) * extent / height
    xx, yy = np.meshgrid(x, y)
    result = np.asarray(stimulus.render(parameters, xx, yy), dtype=float)
    if result.shape != (height, width) or not np.isfinite(result).all() or result.min() < 0 or result.max() > 1:
        raise ValueError("Stimulus renderer must return finite grayscale pixels in [0,1] with the supplied grid shape.")
    return np.rint(result * 255).astype(np.uint8)


def preview_stimulus(identity, parameters, output):
    """Export a headless preview using the same scientific renderer as presentation."""
    from matplotlib.image import imsave
    stimulus = get_stimulus(identity)
    if stimulus.render is None:
        raise ValueError("This legacy/diagnostic stimulus uses its existing preview page.")
    pixels = render_pixels(stimulus, parameters)
    imsave(output, pixels, cmap="gray", vmin=0, vmax=255)
    return output


def validate_geometry(profile, resolution, stimulus, parameters):
    extent = parameters[stimulus.extent_parameter]
    metres = physical_length_for_visual_angle(extent, profile.viewing_distance_m)
    pixels = (round(metres / profile.physical_width_m * resolution[0]),
              round(metres / profile.physical_height_m * resolution[1]))
    if min(pixels) < 2 or any(p > limit for p, limit in zip(pixels, resolution)):
        raise ValueError("Stimulus size does not fit the calibrated display.")
    geometry = resolve_spatial_geometry(profile, resolution)
    if parameters.get(stimulus.frequency_parameter, 0) >= min(geometry.nyquist_cpd_at_centre):
        raise ValueError("Stimulus spatial frequency reaches/exceeds the display Nyquist limit.")
    return pixels


class Presentation:
    def __init__(self, profile, responses):
        import pyglet
        from .display import select_screen
        screen, identity = select_screen(profile)
        self.window = pyglet.window.Window(fullscreen=True, screen=screen, vsync=True, caption="PsyCoLab — Escape aborts")
        self.profile, self.responses = profile, responses
        self.held = set()
        self.window.push_handlers(on_key_release=lambda symbol, modifiers: self.held.discard(symbol))
        self.resolution = (self.window.width, self.window.height)
        if profile.expected_resolution_px != self.resolution:
            self.window.close()
            raise ValueError("Actual fullscreen size differs from calibration; rebind the display.")
        self.metadata = {"monitor_profile_id": profile.id, "physical_display_used": True,
                         "resolution_px": self.resolution, "display_identity": identity,
                         "photon_timing_verified": False, "input_latency_verified": False,
                         "timing_basis": "software perf_counter; self-paced response"}

    def close(self):
        self.window.close()

    def present(self, stimulus, parameters, instructions):
        import pyglet
        from pyglet import gl
        from ..researcher import ParticipantAbort
        parameters = stimulus.validate_parameters(parameters)
        pixels = validate_geometry(self.profile, self.resolution, stimulus, parameters)
        array = render_pixels(stimulus, parameters, pixels=pixels)
        picture = pyglet.image.ImageData(*pixels, "L", array.tobytes(), pitch=pixels[0])
        label = pyglet.text.Label(instructions, x=20, y=20, font_size=14)
        answer = None
        aborted = False
        onset = None
        def keypress(symbol, modifiers):
            nonlocal answer, aborted
            if symbol == pyglet.window.key.ESCAPE:
                aborted = True
                return True
            if symbol in self.held:
                return True
            self.held.add(symbol)
            key = pyglet.window.key.symbol_string(symbol).removeprefix("_")
            if onset is not None and key in self.responses.keys and answer is None:
                answer = Response(self.responses.decode(key), key, time.perf_counter()-onset)
                return True
        self.window.push_handlers(on_key_press=keypress)
        try:
            # Drain old events before onset; a held response must not answer a new trial.
            self.window.dispatch_events()
            gl.glClearColor(.5, .5, .5, 1)
            self.window.clear()
            picture.blit((self.resolution[0]-pixels[0])/2, (self.resolution[1]-pixels[1])/2)
            label.draw()
            self.window.flip()
            onset = time.perf_counter()
            while answer is None and not aborted and not self.window.has_exit:
                self.window.dispatch_events()
                time.sleep(.001)
            if aborted or self.window.has_exit:
                raise ParticipantAbort("Participant closed the window or pressed Escape")
            return answer
        finally:
            self.window.remove_handlers(on_key_press=keypress)
