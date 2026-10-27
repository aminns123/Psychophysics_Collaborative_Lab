"""Internal traversal for RunContext's existing TrialTimeline (no run/file ownership)."""
import time
from .timeline import Phase


def execute_timeline(timeline, backend, events, action, *, instructions="", software_timestamps=False):
    """One traversal for live and virtual presentation, including nonvisual actions.

    Events are owned by the caller, so exceptions cannot discard partial history.
    This function performs no persistence. Action callbacks must not do IO.
    """
    return execute_actions(timeline.phases, backend, events, action, instructions=instructions,
                           software_timestamps=software_timestamps)


def execute_actions(phases, backend, events, action, *, instructions="", start_index=0, software_timestamps=False):
    """Execute an ordered slice; staged updates continue the same trial event indices."""
    response = None
    for index, phase in enumerate(phases, start_index):
        event = {"action_index": index, **phase.to_dict(), "status": "started",
                 "timing_basis": "virtual observer" if backend.synthetic else "software perf_counter"}
        if not backend.synthetic or software_timestamps:
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
            if not backend.synthetic or software_timestamps:
                event["software_finished_s"] = time.perf_counter()
    return response


class VirtualPresentation:
    synthetic = True

    def __init__(self, response=None):
        self.response = response
        self.elapsed_ms = 0

    def prepare(self, timeline, resolved):
        from .presentation import render_values
        from ..stimuli.registry import get_stimulus
        for identity, parameters in resolved.values():
            render_values(get_stimulus(identity), parameters)

    def play_phase(self, phase, event, *, instructions=""):
        event["planned_onset_ms"] = self.elapsed_ms  # schema-1 compatibility
        event["virtual_onset_ms"] = self.elapsed_ms
        event["timing_basis"] = "simulated schedule, not measured presentation"
        if phase.kind == "key_wait":
            event["readiness"] = {"key": phase.key, "elapsed_s": 0.,
                                  "policy": "accept declared key immediately; no observer response or RNG draw"}
            event["virtual_offset_ms"] = self.elapsed_ms
            event["planned_offset_ms"] = None
            if phase.beep is not None:
                event["audio"] = {"trigger": "accepted_readiness", **phase.beep.to_dict(),
                                  "output": "virtual schedule only; no sound generated",
                                  "virtual_request_ms": self.elapsed_ms}
            return None
        if phase.kind == "show" and phase.beep is not None:
            event["audio"] = {"trigger": "display_onset", **phase.beep.to_dict(),
                              "output": "virtual schedule only; no sound generated",
                              "virtual_request_ms": self.elapsed_ms}
        if phase.kind == "response":
            elapsed = self.response.reaction_time_s * 1000
            if phase.duration_ms and elapsed >= phase.duration_ms:
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


class ScientificTrial:
    """One open trial boundary; persistence remains owned by RunContext.

    The accepted response and current state are immutable detached mappings.
    Only nonvisual scientific actions can be appended after the response.
    """
    def __init__(self, response, state, append):
        self._response, self._state, self._append = response, state, append
        self._open = True

    @property
    def response(self):
        return self._response()

    @property
    def state(self):
        return self._state()

    def apply(self, *actions):
        if not self._open:
            raise RuntimeError("Scientific updates require an open trial context.")
        self._append(actions)

    def close(self):
        self._open = False
