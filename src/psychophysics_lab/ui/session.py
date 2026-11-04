"""In-memory navigation between acquisitions; never a scientific parameter file."""
from copy import deepcopy

from textual.widgets import Input, Select, Button, Static
from textual.containers import VerticalScroll

from .console import ConsoleScreen


_DRAFTS = ("config_drafts", "mapping_drafts", "stimulus_drafts",
           "review_parameter_files", "display_draft", "loaded_source_hashes")


def capture_session(app, state):
    if not app.screen_stack:
        return
    home = app.screen_stack[0]
    from .setup import _ExperimentInputsScreen
    for screen in app.screen_stack:
        if isinstance(screen, _ExperimentInputsScreen):
            screen.remember_draft()
    state.update(home={w.id: w.value for w in home.query("Input, Select")
                       if w.id and w.value is not Select.BLANK},
                 run_intent=app.run_intent, include_historical=app.include_historical)
    for name in _DRAFTS:
        state[name] = deepcopy(getattr(app, name))


def restore_session(app, state):
    home = app.screen_stack[0]
    # Restore experiment before its dependent display options.
    with app.prevent(Input.Changed, Select.Changed):
        for name, value in state.get("home", {}).items():
            if name == "monitor-profile":
                continue
            widgets = list(home.query("#" + name))
            if widgets:
                widget = widgets[0]
                if not isinstance(widget, Select) or value in [o[1] for o in widget._options]:
                    widget.value = value
        app._refresh_experiment_context()
        selected = state.get("home", {}).get("monitor-profile")
        widget = home.query_one("#monitor-profile", Select)
        if selected in [o[1] for o in widget._options]:
            widget.value = selected
        app._refresh_monitor_context()
        app.run_intent = state.get("run_intent", app.run_intent)
        app._refresh_run_intent()
    for name in _DRAFTS:
        if name in state:
            setattr(app, name, deepcopy(state[name]))


class RunResultScreen(ConsoleScreen):
    page_title = "Experiment result"

    def __init__(self, outcome):
        super().__init__()
        self.outcome = outcome

    def compose_content(self):
        with VerticalScroll():
            yield Static(self.outcome["summary"], id="run-result-summary", markup=False)
            yield Button("Inspect saved results", id="run-inspect",
                         disabled=self.outcome.get("run_directory") is None)
            yield Button("Configure another run of this experiment", id="run-repeat")
            yield Button("Return to experiment selection", id="run-select", variant="primary")

    def on_button_pressed(self, event):
        name = event.button.id
        if name not in {"run-inspect", "run-repeat", "run-select"}:
            return
        event.stop()
        if name == "run-inspect":
            from .plots import open_run_directory
            try:
                open_run_directory(self.outcome.get("data_root", self.app.data_root), self.outcome["run_directory"])
            except (OSError, ValueError) as exc:
                self.notify(str(exc), severity="error")
            return
        self.app.open_hub_page("setup")
        if name == "run-repeat":
            # Normal configuration and Review must run again, including source,
            # calibration and waiver checks. Never replay an approved request.
            self.app.screen.query_one("#configure", Button).press()
