"""Explicit confirmation for ordinary human acquisition with a recorded waiver."""

from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Static
from .checkbox import ExplicitCheckbox as Checkbox

from ..config.local import content_hash
from ..config.models import SetupRequest
from ..config.preflight import effective_requirements, validate_setup
from ..config.researcher_override import (
    ACKNOWLEDGEMENT, OVERRIDABLE_REQUIREMENTS, authorize_researcher_override,
    outstanding_requirements,
)


class ResearcherOverrideScreen(ModalScreen):
    DEFAULT_CSS = """
    ResearcherOverrideScreen { align: center middle; }
    #override-dialog { width: 90%; max-width: 90; height: auto; max-height: 90%;
        padding: 1 2; border: round $primary; background: $surface; }
    #override-dialog Static { height: auto; }
    #override-ack { width: 100%; height: auto; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, request: SetupRequest, spec, profile):
        super().__init__()
        self.request = validate_setup(request, spec, profile, mode="configuration")
        self.spec = effective_requirements(spec, self.request.stimulus_snapshots)
        self.profile = profile
        self.outstanding = outstanding_requirements(self.spec, profile, self.request.experiment_values)

    def compose(self):
        with VerticalScroll(id="override-dialog"):
            yield Static("Researcher override — collect participant data", markup=False)
            yield Static(
                "This starts the full human experiment and saves responses in the ordinary "
                "participant data folder. Calibration and qualification records stay unchanged. "
                "Your deliberate decision and the outstanding requirements are recorded with this run.",
                markup=False,
            )
            yield Static("\n".join(
                row["name"] + ": " + row["detail"] for row in self.outstanding
                if row["key"] in OVERRIDABLE_REQUIREMENTS), markup=False)
            remaining = [row["detail"] for row in self.outstanding
                         if row["key"] not in OVERRIDABLE_REQUIREMENTS]
            yield Static("Display, parameter and response safeguards still apply."
                         + ("\nResolve before starting: " + "; ".join(remaining) if remaining else ""),
                         markup=False)
            yield Checkbox(ACKNOWLEDGEMENT, id="override-ack")
            yield Button("Override and collect participant data", id="override-launch", variant="success")
            yield Button("Cancel", id="override-cancel")
            yield Static("", id="override-feedback", markup=False)

    def action_cancel(self):
        self.app.pop_screen()

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == "override-cancel":
            self.action_cancel()
        elif event.button.id == "override-launch":
            try:
                from ..config.monitor import load_monitor_profiles
                from ..experiments._internal.registry import get_experiment
                from ..core.display import preflight_fullscreen_display

                self.app.verify_settings_current(self.request)
                current = load_monitor_profiles(self.app.repo_root)[self.request.monitor_profile_id]
                spec = effective_requirements(get_experiment(self.request.experiment_id), self.request.stimulus_snapshots)
                if (content_hash(current.to_dict()) != content_hash(self.profile.to_dict())
                        or outstanding_requirements(spec, current, self.request.experiment_values) != self.outstanding):
                    raise ValueError("Setup or requirements changed. Cancel and review the run again.")
                request = authorize_researcher_override(
                    self.request, spec, current,
                    acknowledged=self.query_one("#override-ack", Checkbox).value,
                )
                preflight_fullscreen_display(current)
                self.app.exit(request)
            except Exception as exc:
                self.query_one("#override-feedback", Static).update(str(exc))
                if not isinstance(exc, (ValueError, TypeError, KeyError, OSError)):
                    from .setup import _report_ui_exception
                    _report_ui_exception(self.app, exc, phase="tui_researcher_override")
