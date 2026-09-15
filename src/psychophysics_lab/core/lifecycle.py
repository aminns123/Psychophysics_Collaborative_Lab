"""Experiment-window termination helpers shared by PsyCoLab experiments.

This module deliberately owns *lifecycle* semantics only. It does not define
stimuli, response mappings, staircase mathematics or experiment completion
criteria. Experiments/adaptive procedures decide when they are complete and ask
this helper to close the presentation window cleanly.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


ABORTED_BY_USER = "aborted_by_user"


def request_window_end(window: Any, reason: str) -> None:
    """Stop accepting further trials and close a presentation window cleanly.

    ``reason`` is stored on the window for experiment-level finalisation and
    diagnostics. Clearing the queued trials before requesting application exit
    prevents an already-complete experiment from accepting another response.
    """
    if getattr(window, "psycolab_end_reason", None) is None:
        window.psycolab_end_reason = str(reason)

    trials = getattr(window, "trials", None)
    if trials is not None:
        trials.clear()

    # Legacy ExpWindow exposes ``run`` as a drawing-state flag. Mark it false as
    # an additional guard even though pyglet.app.exit() is requested immediately.
    if hasattr(window, "run"):
        window.run = False

    window.exit()


def install_escape_handler(
    window: Any,
    *,
    escape_key: Any,
    on_abort: Callable[[], None],
) -> Callable[[Any, Any], bool | None]:
    """Install a high-priority clean Escape handler on a Pyglet window.

    The handler saves the experiment-specific abort state *before* closing the
    GUI. Returning ``True`` tells Pyglet that Escape was handled, so the legacy
    window handler does not also treat Escape as an ordinary response key.
    Non-Escape keys return ``None`` and continue through the normal handler
    chain unchanged.
    """

    def _handle_key(symbol: Any, modifiers: Any) -> bool | None:
        del modifiers
        if symbol != escape_key:
            return None
        if getattr(window, "psycolab_end_reason", None) is not None:
            return True

        # Persist the scientific abort status first. If saving fails we do not
        # falsely report a clean user abort.
        on_abort()
        request_window_end(window, ABORTED_BY_USER)
        return True

    window.push_handlers(on_key_press=_handle_key)
    # Retain an explicit reference for debugging/testing in addition to Pyglet's
    # own handler stack.
    window._psycolab_escape_handler = _handle_key
    return _handle_key
