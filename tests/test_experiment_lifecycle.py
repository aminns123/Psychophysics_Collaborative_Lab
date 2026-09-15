from psychophysics_lab.core.lifecycle import (
    ABORTED_BY_USER,
    install_escape_handler,
    request_window_end,
)


class FakeWindow:
    def __init__(self):
        self.trials = [1, 2, 3]
        self.run = True
        self.psycolab_end_reason = None
        self.exit_calls = 0
        self.handlers = {}

    def exit(self):
        self.exit_calls += 1

    def push_handlers(self, **handlers):
        self.handlers.update(handlers)


def test_request_window_end_stops_queue_before_exit():
    window = FakeWindow()
    request_window_end(window, "completed")
    assert window.trials == []
    assert window.run is False
    assert window.psycolab_end_reason == "completed"
    assert window.exit_calls == 1


def test_escape_saves_abort_before_closing_and_is_handled():
    window = FakeWindow()
    calls = []

    handler = install_escape_handler(
        window,
        escape_key="ESCAPE",
        on_abort=lambda: calls.append("saved"),
    )

    result = handler("ESCAPE", None)
    assert result is True
    assert calls == ["saved"]
    assert window.psycolab_end_reason == ABORTED_BY_USER
    assert window.trials == []
    assert window.exit_calls == 1


def test_non_escape_key_passes_through_unchanged():
    window = FakeWindow()
    calls = []
    handler = install_escape_handler(
        window,
        escape_key="ESCAPE",
        on_abort=lambda: calls.append("saved"),
    )

    assert handler("LEFT", None) is None
    assert calls == []
    assert window.trials == [1, 2, 3]
    assert window.exit_calls == 0


def test_repeated_escape_does_not_repeat_abort_save():
    window = FakeWindow()
    calls = []
    handler = install_escape_handler(
        window,
        escape_key="ESCAPE",
        on_abort=lambda: calls.append("saved"),
    )

    assert handler("ESCAPE", None) is True
    assert handler("ESCAPE", None) is True
    assert calls == ["saved"]
    assert window.exit_calls == 1
