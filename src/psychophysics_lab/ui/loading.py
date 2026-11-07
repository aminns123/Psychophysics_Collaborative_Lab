"""A delayed, shared status for TUI work running in Textual workers."""

from functools import partial
from time import monotonic

from textual.widgets import Static


class LoadingFeedback:
    DELAY = 0.18
    POLL_INTERVAL = 0.06
    DOT_INTERVAL = 0.30
    GROUP = "ui-operation"
    GROUPS = {GROUP, "refresh-files", "authoring"}
    WIDTH = len("Loading...")

    def __init__(self, app):
        self.app = app
        self.foreground = None
        self.started = None
        self.status = None

    @property
    def busy(self):
        return self.foreground is not None and not self.foreground.is_finished

    def run(self, screen, operation, *args):
        if not self.busy:
            self.foreground = screen.run_worker(partial(operation, *args), group=self.GROUP)
        return self.foreground

    async def update(self):
        if not any(worker.group in self.GROUPS for worker in self.app.workers):
            self.started = None
            if self.status is not None:
                await self.status.remove()
                self.status = None
            return
        now = monotonic()
        if self.started is None:
            self.started = now
        elapsed = now - self.started - self.DELAY
        if elapsed < 0:
            return
        screen = self.app.screen
        if self.status is not None and self.status.parent is not screen:
            await self.status.remove()
            self.status = None
        if self.status is None:
            status = Static("", markup=False, id="operation-loading")
            styles = status.styles
            styles.overlay = "screen"
            styles.position = "absolute"
            styles.layer = "transient-feedback"
            styles.width = self.WIDTH
            styles.height = 1
            styles.color = "#b0b0b0"
            styles.background = "#080808"
            self.status = status
            await screen.mount(status)
        self.status.display = screen.size.width >= 24
        self.status.styles.offset = (max(0, screen.size.width - self.WIDTH - 1), 0)
        label = "Loading" + "." * (int(elapsed / self.DOT_INTERVAL) % 3 + 1)
        if label != self.status.renderable:
            self.status.update(label)
