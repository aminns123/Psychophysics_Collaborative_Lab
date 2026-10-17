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


def render_values(stimulus, parameters, *, pixels=(256, 256), extent_deg=None):
    """Scientific floating-point command image, before any display encoding."""
    parameters = stimulus.validate_parameters(parameters)
    extent = extent_deg or parameters[stimulus.extent_parameter]
    width, height = pixels
    x = (np.arange(width) + .5 - width / 2) * extent / width
    y = (np.arange(height) + .5 - height / 2) * extent / height
    xx, yy = np.meshgrid(x, y)
    result = np.asarray(stimulus.render(parameters, xx, yy), dtype=float)
    if result.shape != (height, width) or not np.isfinite(result).all() or result.min() < 0 or result.max() > 1:
        raise ValueError("Stimulus renderer must return finite grayscale pixels in [0,1] with the supplied grid shape.")
    return result


def render_pixels(stimulus, parameters, *, pixels=(256,256), extent_deg=None):
    """Explicit 8-bit teaching/PNG preview; not a precision-qualified stimulus."""
    return np.rint(render_values(stimulus,parameters,pixels=pixels,extent_deg=extent_deg)*255).astype(np.uint8)


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
    frequencies = (stimulus.spatial_frequencies(parameters) if stimulus.spatial_frequencies
                   else (parameters.get(stimulus.frequency_parameter, 0),))
    if any(f >= min(geometry.nyquist_cpd_at_centre) for f in frequencies):
        raise ValueError("Stimulus spatial frequency reaches/exceeds the display Nyquist limit.")
    return pixels


class Presentation:
    synthetic = False
    background_intensity = .5
    def __init__(self, profile, responses, *, background_intensity=.5):
        import math
        if type(background_intensity) not in (int, float) or not math.isfinite(background_intensity) or not 0 <= background_intensity <= 1:
            raise ValueError("Background must be a finite digital command in [0, 1].")
        import pyglet
        from .display import select_screen
        screen, identity = select_screen(profile)
        self.window = pyglet.window.Window(fullscreen=True, screen=screen, vsync=True, caption="PsyCoLab — Escape aborts")
        self.profile, self.responses = profile, responses
        self.background_intensity = background_intensity
        self.held = set()
        self.window.push_handlers(on_key_release=lambda symbol, modifiers: self.held.discard(symbol))
        self.resolution = (self.window.width, self.window.height)
        self.refresh_rate_hz = profile.refresh_rate_hz
        if profile.expected_resolution_px != self.resolution:
            self.window.close()
            raise ValueError("Actual fullscreen size differs from calibration; rebind the display.")
        self.metadata = {"monitor_profile_id": profile.id, "physical_display_used": True,
                         "resolution_px": self.resolution, "display_identity": identity,
                         "photon_timing_verified": False, "input_latency_verified": False,
                         "timing_basis": "vsync frame-counted show stages; self-paced response",
                         "output_precision_verified":False, "display_encoding":"unqualified framebuffer; float texture where requested"}

    def close(self):
        self.window.close()


    def prepare(self, timeline, parameters_by_slot):
        """Prepare all images before the first timed phase; no disk IO."""
        import pyglet
        for pictures in getattr(self,"_rendered",{}).values():
            for _,_,picture in pictures:
                if isinstance(picture,FloatingTexture):picture.delete()
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
                if stimulus.floating_raster:
                    array = np.ascontiguousarray(render_values(stimulus,params,pixels=pixels),dtype=np.float32)
                    picture = FloatingTexture(array)
                else:
                    array = render_pixels(stimulus,params,pixels=pixels)
                    picture = pyglet.image.ImageData(*pixels,"L",array.tobytes(),pitch=pixels[0])
                pictures.append((x,y,picture))
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
                elapsed = time.perf_counter() - onset
                if phase.duration_ms and elapsed * 1000 >= phase.duration_ms:
                    return True  # A late queued key cannot turn a timeout into acceptance.
                answer = Response(self.responses.decode(key), key, elapsed)
                if phase.beep is not None:
                    from .tone import request_beep
                    event["audio"] = request_beep(phase.beep, trigger="accepted_response")
                return True

        self.window.push_handlers(on_key_press=keypress)
        try:
            self.window.dispatch_events()  # discard stale/held responses before onset
            if aborted or self.window.has_exit:
                raise ParticipantAbort("Escape or window close before visual phase")
            gl.glClearColor(self.background_intensity, self.background_intensity, self.background_intensity, 1)
            self.window.clear()
            for x, y, picture in self._rendered[phase.name]:
                picture.blit(x, y)
            label = instructions if instructions and phase.kind == "response" else phase.instructions
            text = pyglet.text.Label(label, x=self.resolution[0]//2,
                                  y=25 if phase.placements else self.resolution[1]//2,
                                  anchor_x="center", font_size=16) if label else None
            if text is not None:
                text.draw()
            self.window.flip()
            onset = time.perf_counter()
            event["software_onset_s"] = onset
            previous = getattr(self,"_last_visual_event",None)
            if previous is not None:
                previous["next_flip_s"] = onset
                previous["actual_display_duration_s"] = onset-previous["software_onset_s"]
                if "requested_frames" in previous:
                    interval = onset-previous["flip_times_s"][-1]
                    previous["frame_intervals_s"].append(interval)
                    previous["dropped_frame_intervals"] += int(interval>1.5/self.refresh_rate_hz)
            self._last_visual_event = event
            event["flip_times_s"] = [onset]
            if phase.kind == "show" and phase.beep is not None:
                from .tone import request_beep
                event["audio"] = request_beep(phase.beep, trigger="display_onset")
            accepting = phase.kind == "response"
            hz = getattr(self,"refresh_rate_hz",None)
            if phase.kind == "show" and hz is not None:
                frames = max(1,round(phase.duration_ms*hz/1000))
                event.update(requested_duration_ms=phase.duration_ms,requested_frames=frames,
                             quantized_duration_ms=frames*1000/hz,frame_intervals_s=[],dropped_frame_intervals=0)
                for _ in range(1,frames):
                    self.window.dispatch_events()
                    if aborted or self.window.has_exit:
                        raise ParticipantAbort("Escape or close during frame-counted phase")
                    self.window.clear()
                    for x,y,picture in self._rendered[phase.name]:picture.blit(x,y)
                    if text is not None:
                        text.draw()
                    self.window.flip()
                    flip = time.perf_counter()
                    interval = flip-event["flip_times_s"][-1]
                    event["frame_intervals_s"].append(interval)
                    event["dropped_frame_intervals"] += int(interval>1.5/hz)
                    event["flip_times_s"].append(flip)
                return None
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


class FloatingTexture:
    """Preserve floating commands through upload; never certify physical bit depth.

    Requires ARB_texture_float. The final framebuffer/LUT/panel still require
    independent precision and luminance measurements before scientific acquisition.
    """
    def __init__(self, array):
        import ctypes
        from pyglet import gl
        if not gl.gl_info.have_extension("GL_ARB_texture_float"):
            raise ValueError("Floating scientific stimuli require GL_ARB_texture_float; no 8-bit fallback.")
        self.width,self.height=array.shape[1],array.shape[0]
        self.identifier=gl.GLuint()
        gl.glGenTextures(1,ctypes.byref(self.identifier))
        gl.glBindTexture(gl.GL_TEXTURE_2D,self.identifier)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_NEAREST)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT,1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D,0,gl.GL_LUMINANCE32F_ARB,self.width,self.height,0,
            gl.GL_LUMINANCE,gl.GL_FLOAT,array.ctypes.data_as(ctypes.POINTER(ctypes.c_float)))

    def blit(self,x,y):
        from pyglet import gl
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D,self.identifier)
        gl.glColor4f(1,1,1,1)
        gl.glBegin(gl.GL_QUADS)
        for u,v,px,py in ((0,0,x,y),(1,0,x+self.width,y),(1,1,x+self.width,y+self.height),(0,1,x,y+self.height)):
            gl.glTexCoord2f(u,v);gl.glVertex2f(px,py)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)

    def delete(self):
        import ctypes
        from pyglet import gl
        gl.glDeleteTextures(1,ctypes.byref(self.identifier))
