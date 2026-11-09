"""Delayed researcher-facing status, scoped to named interface operations."""

from functools import partial
from time import monotonic

from textual.widgets import Static


class LoadingFeedback:
    DELAY = 0.18
    POLL_INTERVAL = 0.06
    DOT_INTERVAL = 0.30
    GROUP = "ui-operation"

    def __init__(self, app):
        self.app = app
        self.foreground = None
        self.status = None
        self.timer = None
        self.operations = {}
        self.closed = False

    @property
    def busy(self):
        return self.foreground is not None and not self.foreground.is_finished

    def run(self, screen, operation, *args, label):
        if not self.closed and not self.busy:
            self.foreground = screen.run_worker(partial(operation, *args), group=self.GROUP)
            self.watch(self.foreground, label)
        return self.foreground

    def watch(self, worker, label):
        if self.closed:
            return
        self.operations[worker] = (label, monotonic())
        if self.timer is None:
            self.timer = self.app.set_interval(self.POLL_INTERVAL, self.update)

    def _hide(self):
        if self.status is not None:
            if self.status.is_attached:
                self.status.display = False
                self.status.remove()
            self.status = None

    def _stop_timer(self):
        if self.timer is not None:
            self.timer.stop()
            self.timer = None

    def close(self):
        """Stop feedback before returning control to a run or display test."""
        if self.closed:
            return
        self.closed = True
        self.operations.clear()
        self._stop_timer()
        self._hide()

    def update(self):
        if self.closed:
            return
        self.operations = {worker: status for worker, status in self.operations.items()
                           if not worker.is_finished}
        if not self.operations:
            self._hide()
            self._stop_timer()
            return
        label, started = next(reversed(self.operations.values()))
        elapsed = monotonic() - started - self.DELAY
        if elapsed < 0:
            self._hide()
            return

        screen = self.app.screen
        width = len(label) + 3
        if screen.size.width < max(24, width + 2):
            self._hide()
            return
        if self.status is not None and self.status.parent is not screen:
            self._hide()
        frame = label + "." * (int(elapsed / self.DOT_INTERVAL) % 3 + 1)
        if self.status is None:
            status = Static(frame, markup=False, id="operation-loading")
            styles = status.styles
            styles.overlay = "screen"
            styles.position = "absolute"
            styles.layer = "transient-feedback"
            # The research workspace uses a two-column grid. Span both
            # columns so a long status is not clipped to the sidebar width.
            styles.column_span = 2
            styles.width = width
            styles.height = 1
            styles.color = "#b0b0b0"
            styles.background = "#080808"
            styles.offset = (screen.size.width - width - 1, 0)
            self.status = status
            screen.mount(status)
        self.status.styles.width = width
        self.status.styles.offset = (screen.size.width - width - 1, 0)
        if frame != self.status.renderable:
            self.status.update(frame)
