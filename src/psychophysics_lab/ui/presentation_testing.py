"""Confirm an isolated physical test, without changing study parameters."""

from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Static, Checkbox, Button, Input, Label


class PresentationTestScreen(ModalScreen):
    DEFAULT_CSS = """
    PresentationTestScreen { align: center middle; }
    #presentation-dialog { width: 90%; max-width: 90; height: auto; padding: 1 2; border: round $primary; background: $surface; }
    #presentation-dialog Static { height: auto; }
    """

    def __init__(self, request):
        super().__init__()
        self.request = request

    def compose(self):
        from ..experiments._internal.registry import get_experiment

        supports_limit = (
            get_experiment(self.request.experiment_id).procedure is not None
        )
        with Vertical(id="presentation-dialog"):
            yield Static(
                "Try the experiment on your selected monitor. Use its response keys; Escape stops. Test records are saved separately. This does not qualify the display.",
                markup=False,
            )
            yield Label("Responses to try (blank runs the full experiment)")
            yield Input(
                value="8" if supports_limit else "",
                disabled=not supports_limit,
                id="presentation-trial-limit",
            )
            yield Checkbox("Save this as test data", id="presentation-ack")
            yield Button(
                "Try the experiment", id="presentation-launch", variant="primary"
            )
            yield Button("Cancel", id="presentation-cancel")
            yield Static("", id="presentation-feedback", markup=False)

    def on_button_pressed(self, event):
        if event.button.id == "presentation-cancel":
            self.app.pop_screen()
        elif event.button.id == "presentation-launch":
            try:
                if not self.query_one("#presentation-ack", Checkbox).value:
                    raise ValueError("Select Save this as test data to continue.")
                from ..core.presentation_testing import (
                    PresentationTestRequest,
                    validate_presentation,
                )
                from ..config.monitor import load_monitor_profiles
                from ..experiments._internal.registry import get_experiment

                raw = self.query_one("#presentation-trial-limit", Input).value.strip()
                action = PresentationTestRequest(
                    self.request, int(raw) if raw else None
                )
                profile = load_monitor_profiles(self.app.repo_root)[
                    self.request.monitor_profile_id
                ]
                validate_presentation(
                    self.request, get_experiment(self.request.experiment_id), profile
                )
                self.app.verify_settings_current(self.request)
                self.app.exit(action)
            except (ValueError, OSError) as exc:
                self.query_one("#presentation-feedback", Static).update(str(exc))
