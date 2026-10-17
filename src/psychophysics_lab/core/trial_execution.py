"""Internal traversal for RunContext's existing TrialTimeline (no run/file ownership)."""
import time
from .timeline import Phase


def execute_timeline(timeline, backend, events, action, *, instructions=""):
    """One traversal for live and virtual presentation, including nonvisual actions.

    Events are owned by the caller, so exceptions cannot discard partial history.
    This function performs no persistence. Action callbacks must not do IO.
    """
    response = None
    for index, phase in enumerate(timeline.phases):
        event = {"action_index": index, **phase.to_dict(), "status": "started",
                 "timing_basis": "virtual observer" if backend.synthetic else "software perf_counter"}
        if not backend.synthetic:
            event["software_started_s"] = time.perf_counter()
        events.append(event)
        try:
            if isinstance(phase, Phase):
                observed = backend.play_phase(phase, event, instructions=instructions)
                if observed is not None:
                    response = observed
            action(phase, response, event)
            event["status"] = "completed"
        except BaseException as exc:
            from ..researcher import ParticipantAbort
            event["status"] = "aborted" if isinstance(exc, ParticipantAbort) else "error"
            event["error"] = str(exc)
            raise
        finally:
            if not backend.synthetic:
                event["software_finished_s"] = time.perf_counter()
    return response


class VirtualPresentation:
    synthetic = True

    def __init__(self, response):
        self.response = response
        self.elapsed_ms = 0

    def prepare(self, timeline, resolved):
        from .presentation import render_pixels
        from ..stimuli.registry import get_stimulus
        for identity, parameters in resolved.values():
            render_pixels(get_stimulus(identity), parameters)

    def play_phase(self, phase, event, *, instructions=""):
        event["planned_onset_ms"] = self.elapsed_ms  # schema-1 compatibility
        event["virtual_onset_ms"] = self.elapsed_ms
        event["timing_basis"] = "simulated schedule, not measured presentation"
        if phase.kind == "show" and phase.beep is not None:
            event["audio"] = {"trigger": "display_onset", **phase.beep.to_dict(),
                              "output": "virtual schedule only; no sound generated",
                              "virtual_request_ms": self.elapsed_ms}
        if phase.kind == "response":
            elapsed = self.response.reaction_time_s * 1000
            if phase.duration_ms and elapsed > phase.duration_ms:
                self.elapsed_ms += phase.duration_ms
                event["virtual_offset_ms"] = self.elapsed_ms
                raise TimeoutError("No valid virtual response before the configured response timeout")
            self.elapsed_ms += elapsed
            event["virtual_offset_ms"] = self.elapsed_ms
            event["planned_offset_ms"] = None
            if phase.beep is not None:
                event["audio"] = {"trigger": "accepted_response", **phase.beep.to_dict(),
                                  "output": "virtual schedule only; no sound generated",
                                  "virtual_request_ms": self.elapsed_ms}
            return self.response
        self.elapsed_ms += phase.duration_ms
        event["planned_offset_ms"] = self.elapsed_ms
        event["virtual_offset_ms"] = self.elapsed_ms
        return None
