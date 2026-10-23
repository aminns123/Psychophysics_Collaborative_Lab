"""Researcher-only application chrome; delegates to the existing hub routes."""
from textual import events
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static


PAGES = (
    ("setup", "Experiment", "Setup"),
    ("stimuli", "Build Stimuli", "Stimuli"),
    ("experiments", "Build Experiments", "Build"),
    ("display", "Calibration", "Calibrate"),
    ("simulations", "Scenarios", "Scenarios"),
    ("data", "Data", "Data"),
    ("help", "Learn / Help", "Help"),
)
CONTEXTS = {
    "ExperimentsScreen": ("experiments", "BUILD EXPERIMENTS"),
    "StimuliScreen": ("stimuli", "BUILD STIMULI"),
    "DisplayCheckScreen": ("display", "CALIBRATION / MEASURE"),
    "ProfileScreen": ("display", "CALIBRATION / DISPLAY PROFILE"),
    "PhysicalVerificationScreen": ("display", "CALIBRATION / VERIFY"),
    "ExperimentQualificationScreen": ("display", "CALIBRATION / QUALIFICATION"),
    "LuminanceDataScreen": ("display", "CALIBRATION / LUMINANCE DATA"),
    "DataScreen": ("data", "DATA / RUNS"),
    "HelpScreen": ("help", "LEARN / HELP"),
    "ExperimentConfigScreen": ("setup", "EXPERIMENT / 02 CONFIGURE"),
    "ReviewScreen": ("setup", "EXPERIMENT / 03 REVIEW"),
    "ChangeDisplayScreen": ("setup", "EXPERIMENT / DISPLAY"),
    "VirtualObserverOptionsScreen": ("setup", "EXPERIMENT / VIRTUAL OBSERVER"),
    "SimulationsScreen": ("simulations", "SCENARIOS"),
    "SimulationReviewScreen": ("simulations", "SCENARIOS / REVIEW"),
    "AdaptiveAlgorithmScreen": ("simulations", "SCENARIOS / ADAPTIVE SETTINGS"),
}


class LaboratoryNavigation(VerticalScroll):
    def __init__(self, section):
        super().__init__(id="hub-nav")
        self.section = section

    def compose(self):
        yield Static("LABORATORY", id="laboratory-label")
        for key, label, _ in PAGES:
            yield Button(label, id="nav-"+key, tooltip=label)
        yield Button("Refresh · F5", id="refresh-psycolab", tooltip="Reload saved Python and JSON files (F5)")

    def on_mount(self):
        self.query_one("#nav-simulations").display = self.app.include_historical
        self.update_size(self.app.size.width)

    def on_resize(self, event: events.Resize):
        self.update_size(self.app.size.width)

    def update_size(self, width):
        self.screen.set_class(width < 100, "console-compact")
        self.screen.set_class(width < 70, "console-narrow")
        self.screen.set_class(self.app.size.height < 32, "console-short")
        for key, label, short in PAGES:
            button = self.query_one("#nav-"+key, Button)
            selected = key == self.section
            button.label = ("> " if selected else "") + (short if width < 100 else label)
            button.set_class(selected, "nav-selected")
            button.variant = "primary" if selected else "default"

    def on_button_pressed(self, event):
        identity = event.button.id or ""
        if identity.startswith("nav-"):
            event.stop()
            self.app.open_hub_page(identity[4:])
        elif identity == "refresh-psycolab":
            event.stop()
            self.app.action_refresh_files()


async def install_console(screen):
    if screen.query("#console-heading"):
        return
    section, title = CONTEXTS.get(type(screen).__name__, ("setup", "EXPERIMENT / 01 SETUP"))
    if type(screen).__name__ in {"SourceView", "CodeViewScreen", "JsonPresetEditor", "StimulusValueEditor"}:
        previous = list(screen.app.screen_stack)
        previous = previous[:previous.index(screen)]
        if previous:
            section = getattr(previous[-1], "console_section", "setup")
        title = dict((key, label.upper()) for key, label, _ in PAGES)[section] + " / " + {
            "SourceView": "SOURCE", "CodeViewScreen": "SOURCE", "JsonPresetEditor": "PRESET", "StimulusValueEditor": "STIMULUS VALUES"
        }[type(screen).__name__]
    if not screen.query(Footer):
        await screen.mount(Footer())
    screen.console_section = section
    screen.add_class("laboratory-console")
    # The sidebar reserves the heading and footer rows with dock margins.
    await screen.mount(LaboratoryNavigation(section),
                       Static("PsyCoLab  /  " + title, id="console-heading", markup=False), before=0)


class ConsoleScreen(Screen):
    async def _on_mount(self):
        await install_console(self)


CONSOLE_CSS = """
Screen.laboratory-console { background: $background; }
Screen.laboratory-console Header { display: none; }
Screen.laboratory-console .buttons Button { width: 1fr; }
Screen.laboratory-console Label { width: 100%; height: auto; }
#console-heading { dock: top; width: 100%; height: 2; padding: 0 1;
    background: $surface; color: $text; text-style: bold; border-bottom: solid $primary; }
#hub-nav { dock: left; layout: vertical; width: 23; height: 1fr;
    margin: 2 0 1 0; padding: 0 1; background: $surface; border-right: solid $primary-muted; }
#laboratory-label { height: 2; color: $text-muted; padding-top: 1; }
#hub-nav Button { width: 100%; height: 3; min-width: 0; margin: 0; padding: 0;
    content-align: left middle; border: none; background: $surface; }
#hub-nav Button.nav-selected { background: $primary; text-style: bold; }
#hub-nav Button:focus { text-style: bold underline; background: $boost; }
#hub-nav Button:hover { background: $boost; }
#hub-nav #refresh-psycolab { margin-top: 1; color: $text-muted; }
.console-short #hub-nav Button { height: 2; }
.console-compact #hub-nav { width: 17; padding: 0; }
.console-compact #setup-body, .console-compact #review-body,
.console-compact .page-body, .console-compact #config-body { padding: 0 1; }
.console-compact .buttons { layout: grid; grid-size: 2; grid-rows: 3; height: auto; }
.console-compact .buttons Button { width: 100%; max-width: 100%; height: 3; border: none; }
.console-compact .buttons Button:focus { text-style: bold underline; }
.console-compact #calibration-stage-nav { layout: grid; grid-size: 4 2;
    grid-rows: 3 3; height: 6; }
.console-compact #calibration-stage-nav Button { width: 100%; height: 3; border: none; }
.console-compact #calibration-stage-nav Button.calibration-active { text-style: bold underline; }
.console-narrow #calibration-stage-nav { grid-size: 3 3; grid-rows: 3 3 3; height: 9; }
.old-navigation-placeholder { display: none; }
Screen.laboratory-console #fixed-shell { background: $background; dock: none; width: 100%; max-height: 45%; overflow-y: auto; }

Screen.laboratory-console #setup-body, Screen.laboratory-console #review-body,
Screen.laboratory-console .page-body, Screen.laboratory-console #config-body,
Screen.laboratory-console #code-body { border: none; }
"""
