"""Read the existing screen's complete text without terminal-width clipping."""
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Static, TextArea


def field_description(field):
    """Describe declared constraints; cross-field validation remains authoritative."""
    if field.choices:
        limits = "Choices: " + ", ".join(map(str, field.choices))
    elif field.minimum is not None or field.maximum is not None:
        limits = f"Range (inclusive): {field.minimum if field.minimum is not None else '-infinity'} to {field.maximum if field.maximum is not None else '+infinity'}"
    else:
        limits = "Range: experiment/stimulus validation applies; no independent numeric bounds declared"
    return (f"{field.display_label}\n{field.help_text or field.label}\n"
            f"{limits}\nKey: {field.key}; type: {field.kind}; "
            f"{'editable' if field.editable else 'fixed definition'}. "
            "Combined settings must also pass the existing scientific validation.")


class FullTextScreen(Screen):
    BINDINGS = [("escape", "close", "Back")]
    DEFAULT_CSS = """
    FullTextScreen { background: #080808; color: #eeeeee; layout: vertical; }
    FullTextScreen > Vertical { width: 100%; height: 100%; padding: 0 1; }
    #full-text-title { height: auto; }
    #full-text-content { height: 1fr; width: 100%; border: solid #555555; }
    #full-text-back { height: 3; }
    """

    def __init__(self, title, content):
        super().__init__()
        self.title_text, self.content_text = title, content

    def compose(self):
        with Vertical():
            yield Static(self.title_text, id="full-text-title", markup=False)
            yield TextArea(self.content_text, read_only=True, soft_wrap=True,
                           id="full-text-content")
            yield Button("Back / Esc", id="full-text-back")
            yield Footer()

    def on_mount(self):
        self.query_one(TextArea).focus()

    def on_button_pressed(self, event):
        event.stop()
        self.action_close()

    def action_close(self):
        self.app.pop_screen()
