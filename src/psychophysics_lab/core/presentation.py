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
    synthetic = False
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


    def prepare(self, timeline, parameters_by_slot):
        """Prepare all images before the first timed phase; no disk IO."""
        import pyglet
        rendered = {}
        for phase in timeline.phases:
            if not hasattr(phase, "placements"):
                continue
            pictures = []
            for placement in phase.placements:
                stimulus_id, params = parameters_by_slot[placement.slot]
                stimulus = get_stimulus(stimulus_id)
                pixels = validate_geometry(self.profile, self.resolution, stimulus, params)
                x, y = placement_pixels(self.profile, self.resolution, pixels, placement)
                array = render_pixels(stimulus, params, pixels=pixels)
                pictures.append((x, y, pyglet.image.ImageData(*pixels, "L", array.tobytes(), pitch=pixels[0])))
            rendered[phase.name] = pictures
        self._rendered = rendered

    def play_phase(self, phase, event, *, instructions=""):
        """Observe one visual phase; append partial timing even on Escape/timeout."""
        import pyglet
        from pyglet import gl
        from ..researcher import ParticipantAbort
        answer = None
        aborted = False
        onset = None
        accepting = False

        def keypress(symbol, modifiers):
            nonlocal answer, aborted
            if symbol == pyglet.window.key.ESCAPE:
                aborted = True
                return True
            if symbol in self.held:
                return True
            self.held.add(symbol)
            key = pyglet.window.key.symbol_string(symbol).removeprefix("_")
            if accepting and key in self.responses.keys and answer is None:
                answer = Response(self.responses.decode(key), key, time.perf_counter() - onset)
                return True

        self.window.push_handlers(on_key_press=keypress)
        try:
            self.window.dispatch_events()  # discard stale/held responses before onset
            if aborted or self.window.has_exit:
                raise ParticipantAbort("Escape or window close before visual phase")
            gl.glClearColor(.5, .5, .5, 1)
            self.window.clear()
            for x, y, picture in self._rendered[phase.name]:
                picture.blit(x, y)
            label = instructions if instructions and phase.kind == "response" else phase.instructions
            if label:
                pyglet.text.Label(label, x=self.resolution[0]//2,
                                  y=25 if phase.placements else self.resolution[1]//2,
                                  anchor_x="center", font_size=16).draw()
            self.window.flip()
            onset = time.perf_counter()
            event["software_onset_s"] = onset
            accepting = phase.kind == "response"
            while True:
                if aborted or self.window.has_exit:
                    raise ParticipantAbort("Escape or window close during trial timeline")
                if answer is not None:
                    return answer
                if phase.duration_ms and (time.perf_counter() - onset)*1000 >= phase.duration_ms:
                    if accepting:
                        raise TimeoutError("No valid response before the configured response timeout")
                    return None
                self.window.dispatch_events()
                time.sleep(.001)
        finally:
            event["software_offset_s"] = time.perf_counter()
            event["timing_basis"] = "software flip/clock; photons and input latency unverified"
            self.window.remove_handlers(on_key_press=keypress)

    def play_timeline(self, timeline, parameters_by_slot, *, instructions=None):
        """Compatibility entrypoint; the public RunContext owns scientific actions."""
        from .timeline import Phase
        from .trial_execution import execute_timeline
        if any(not isinstance(p, Phase) for p in timeline.phases):
            raise ValueError("Scientific actions require RunContext.play_trial.")
        timeline.validate_slots(parameters_by_slot)
        self.prepare(timeline, parameters_by_slot)
        events = []
        response = execute_timeline(timeline, self, events, lambda a, r, e: None,
                                    instructions=instructions or "")
        return response, events

    def present(self, stimulus, parameters, instructions):
        """Compatibility self-paced display uses the same phase/input implementation."""
        from .timeline import Phase, TrialTimeline
        response, _ = self.play_timeline(
            TrialTimeline((Phase("answer", "response", "target"),)),
            {"target": (stimulus.id, parameters)}, instructions=instructions)
        return response


def placement_pixels(profile, resolution, pixels, placement):
    """Position a patch in calibrated screen coordinates; reject clipped patches."""
    import math
    if abs(placement.x_deg) >= 90 or abs(placement.y_deg) >= 90:
        raise ValueError("Stimulus position must be within the forward display field.")
    x_offset = profile.viewing_distance_m * math.tan(math.radians(abs(placement.x_deg)))
    y_offset = profile.viewing_distance_m * math.tan(math.radians(abs(placement.y_deg)))
    x_offset *= (1 if placement.x_deg >= 0 else -1) * resolution[0] / profile.physical_width_m
    y_offset *= (1 if placement.y_deg >= 0 else -1) * resolution[1] / profile.physical_height_m
    x = (resolution[0] - pixels[0]) / 2 + x_offset
    y = (resolution[1] - pixels[1]) / 2 + y_offset
    if x < 0 or y < 0 or x + pixels[0] > resolution[0] or y + pixels[1] > resolution[1]:
        raise ValueError("Positioned stimulus does not fit the calibrated display.")
    return x, y
