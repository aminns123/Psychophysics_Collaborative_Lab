"""Optional simple Windows tone, compatible with the PhD winsound.Beep idiom.

Tone requests are asynchronous to avoid freezing visual trial timing for the
beep duration. Thread scheduling and Windows mixer latency are NOT calibrated.
There is no speaker output for virtual observers.
"""
import sys
import threading
import time


def request_beep(beep, *, trigger):
    """Start the simple tone after software flip or accepted keypress.

    Does not block the trial for the entire tone. Never used in simulation.
    On Windows this uses the original winsound.Beep(frequency, duration).
    """
    from .timeline import Beep
    if not isinstance(beep, Beep) or trigger not in {"display_onset", "accepted_response"}:
        raise ValueError("Invalid beep command or trigger.")
    if sys.platform != "win32":
        raise RuntimeError("Physical beep playback currently requires Windows; disable beeps on this system.")
    import winsound

    def play():
        try:
            winsound.Beep(beep.frequency_hz, beep.duration_ms)
        except OSError:
            # Playback may fail on a device even after a successful dispatch.
            # This cannot count as measured speaker output.
            pass

    request_s = time.perf_counter()
    threading.Thread(target=play, name="PsyCoLabBeep", daemon=True).start()
    return {"trigger": trigger, **beep.to_dict(), "software_request_s": request_s,
            "output": "Windows winsound.Beep requested asynchronously; acoustic onset not verified"}
