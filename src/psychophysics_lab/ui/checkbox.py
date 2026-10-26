"""Readable input state; persisted evidence remains in each screen's status."""
from rich.text import Text
from textual.widgets import Checkbox


class ExplicitCheckbox(Checkbox):
    """Retain Textual interaction, with words independent of theme/glyphs."""

    def __init__(self, label="", value=False, *args,
                 selected_status="Selected — not yet saved", **kwargs):
        self._purpose = str(label)
        self._selected_status = selected_status
        super().__init__(label, value, *args, **kwargs)
        self._refresh_label()

    def _refresh_label(self):
        state = "[X] " + self._selected_status if self.value else "[ ] Not selected"
        self.label = Text(f"{self._purpose} — {state}")

    def watch_value(self):
        super().watch_value()
        self._refresh_label()
