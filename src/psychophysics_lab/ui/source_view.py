"""Read-only fallback when an external source editor is unavailable."""
from .console import ConsoleScreen as Screen
from textual.widgets import Button, Label, TextArea


class SourceView(Screen):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def compose_content(self):
        yield Label(str(self.path))
        yield Button("Back", id="source-close")
        yield TextArea(self.path.read_text(encoding="utf-8"), read_only=True, show_line_numbers=True)

    def on_button_pressed(self, event):
        if event.button.id == "source-close":
            event.stop()
            self.app.pop_screen()
