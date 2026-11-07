"""One-shot handoff from the Windows launcher to the first Textual screen."""

import os
import sys
from time import monotonic

from textual.color import Color
from textual.widgets import Static


def take_handoff():
    mode = os.environ.pop("PSYCOLAB_STARTUP_HANDOFF", "")
    if mode not in {"skip", "reveal"} or sys.platform != "win32" or not sys.stdout.isatty():
        return None, False

    from textual.drivers.windows_driver import WindowsDriver

    class StartupDriver(WindowsDriver):
        _adopting_screen = True

        def write(self, data):
            # The launcher has already entered the alternate screen. A second
            # entry can clear the docked title before Textual renders.
            if self._adopting_screen and data == "\x1b[?1049h":
                self._adopting_screen = False
                return
            super().write(data)

    return StartupDriver, mode == "reveal"


class StartupReveal:
    DURATION = 1.5
    FRAME_INTERVAL = 1 / 24
    CYAN = Color.parse("#066383")
    BLACK = Color.parse("black")

    def __init__(self):
        self.brand = Static("PsyCoLab", markup=False, id="startup-brand")
        self.active = False
        self.timer = None

    async def prepare(self, app):
        screen = app.screen
        if app.size.width < 68 or app.size.height < 10:
            return
        self.screen = screen
        self.children = [(widget, widget.styles.opacity) for widget in screen.children]
        self.background = screen.styles.background
        screen.styles.background = self.BLACK
        for widget, _ in self.children:
            widget.styles.opacity = 0
        styles = self.brand.styles
        styles.position = "absolute"
        styles.overlay = "screen"
        styles.layer = "transient-feedback"
        styles.offset = (1, 0)
        styles.width = 8
        styles.height = 1
        styles.color = self.CYAN
        styles.background = self.BLACK
        self.brand_color = screen.query_one("#console-heading").styles.color
        self.active = True
        try:
            await screen.mount(self.brand)
            app.call_after_refresh(self.play, app)
        except Exception:
            self.finish()

    def play(self, app):
        if self.active:
            self.started = monotonic()
            self.timer = app.set_interval(self.FRAME_INTERVAL, self.step)

    def step(self):
        progress = (monotonic() - self.started) / self.DURATION
        if progress >= 1:
            self.finish()
            return
        opacity = progress * progress * (3 - 2 * progress)
        for widget, original in self.children:
            widget.styles.opacity = original * opacity
        self.screen.styles.background = self.brand.styles.background = self.BLACK.blend(self.background, opacity)
        self.brand.styles.color = self.CYAN.blend(self.brand_color, opacity)

    def finish(self):
        if not self.active:
            return
        self.active = False
        if self.timer is not None:
            self.timer.stop()
        self.screen.styles.background = self.background
        for widget, opacity in self.children:
            widget.styles.opacity = opacity
        if self.brand.is_attached:
            self.brand.remove()
