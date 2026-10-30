"""Researcher-only application chrome; delegates to the existing hub routes."""
from textual import events
from textual.containers import Container, Vertical, VerticalScroll
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
    "ExperimentParametersScreen": ("setup", "EXPERIMENT / 03 REVIEW / EDIT INPUTS"),
    "ReviewScreen": ("setup", "EXPERIMENT / 03 REVIEW"),
    "ChangeDisplayScreen": ("setup", "EXPERIMENT / DISPLAY"),
    "VirtualObserverOptionsScreen": ("setup", "EXPERIMENT / VIRTUAL OBSERVER"),
    "SimulationsScreen": ("simulations", "SCENARIOS"),
    "SimulationReviewScreen": ("simulations", "SCENARIOS / REVIEW"),
    "AdaptiveAlgorithmScreen": ("simulations", "SCENARIOS / ADAPTIVE SETTINGS"),
}


class NavigationButton(Button):
    """Keep marker changes inside a constant-size navigation row."""
    def __init__(self, label, *, active=False, child=False, **kwargs):
        self.caption = label
        self.active = active
        self.child = child
        self.hovered = False
        super().__init__(label, **kwargs)
        self.set_class(active, 'nav-selected')
        self.set_class(child, 'nav-child')
        self.update_marker()

    def update_marker(self, focused=None):
        marker = '>' if (self.has_focus if focused is None else focused) or self.hovered else '->' if self.active else '-'
        self.label = ('  ' if self.child else '') + marker + ' ' + self.caption

    def on_focus(self):
        self.update_marker(focused=True)

    def on_blur(self):
        self.update_marker(focused=False)

    def on_enter(self):
        self.hovered = True
        self.update_marker()

    def on_leave(self):
        self.hovered = False
        self.update_marker()


class LaboratoryNavigation(VerticalScroll):
    def __init__(self, section, title):
        super().__init__(id='hub-nav')
        self.section, self.title = section, title

    def compose(self):
        yield Static('LABORATORY', id='laboratory-label')
        for key, label, _ in PAGES:
            yield NavigationButton(label, active=key == self.section, id='nav-'+key, tooltip=label)
            if key == 'setup':
                name = next((type(page).__name__ for page in reversed(self.app.screen_stack)
                             if type(page).__name__ in {'ExperimentConfigScreen', 'ReviewScreen', 'ExperimentParametersScreen'}), '')
                yield NavigationButton('Configure', child=True, active=name == 'ExperimentConfigScreen', id='path-configure')
                yield NavigationButton('Review', child=True, active=name in {'ReviewScreen', 'ExperimentParametersScreen'}, id='path-review')
        context = self.title.split(' / ')[-1].title() if '/' in self.title else ''
        if self.title in {'EXPERIMENT / 01 SETUP', 'EXPERIMENT / 02 CONFIGURE', 'EXPERIMENT / 03 REVIEW'}:
            context = ''
        yield Static('  -> '+context if context else '', id='nav-context', markup=False)
        yield Button('Refresh / F5', id='refresh-psycolab', tooltip='Reload saved Python and JSON files (F5)')

    def on_mount(self):
        self.query_one('#nav-simulations').display = self.app.include_historical
        self.update_size(self.app.size.width)

    def on_resize(self, event: events.Resize):
        self.update_size(self.app.size.width)

    def update_size(self, width):
        self.screen.set_class(width < 100, 'console-compact')
        for key, label, short in PAGES:
            button = self.query_one('#nav-'+key, NavigationButton)
            button.caption = short if width < 100 else label
            button.update_marker()
        if self.query('#path-review'):
            self.query_one('#path-review').disabled = not any(type(s).__name__ in {'ExperimentConfigScreen','ExperimentParametersScreen','ReviewScreen'} for s in self.app.screen_stack)

    def on_button_pressed(self, event):
        identity = event.button.id or ''
        if identity.startswith('nav-'):
            event.stop()
            self.app.open_hub_page(identity[4:])
        elif identity.startswith('path-'):
            event.stop()
            if identity == 'path-review' and type(self.app.screen).__name__ in {'ExperimentConfigScreen', 'ExperimentParametersScreen'}:
                # A Review-to-Edit configuration can sit above the existing
                # Review. Apply/validate its current draft before returning;
                # popping straight to the old Review silently discards edits.
                self.app.screen.query_one('#review', Button).press()
                return
            target = 'ExperimentConfigScreen' if identity == 'path-configure' else 'ReviewScreen'
            existing = next((s for s in reversed(self.app.screen_stack) if type(s).__name__ == target), None)
            if existing is not None:
                while self.app.screen is not existing:
                    self.app.pop_screen()
            elif identity == 'path-configure':
                self.app.open_hub_page('setup')
                self.app.screen.query_one('#configure', Button).press()
            else:
                configuration = next((s for s in reversed(self.app.screen_stack)
                                      if type(s).__name__ == 'ExperimentConfigScreen'), None)
                if configuration is not None:
                    while self.app.screen is not configuration:
                        self.app.pop_screen()
                    configuration.query_one('#review', Button).press()
        elif identity == 'refresh-psycolab':
            event.stop()
            self.app.action_refresh_files()


class ConsolePanel(Container):
    """Four fixed edge widgets leave content and the external rail clickable."""
    def on_resize(self, event: events.Resize):
        width, height = event.size
        for name, x, y, w, h in (
            ('top', 0, 0, width - 2, 1),
            ('bottom', 0, height - 1, width - 2, 1),
            ('left', 0, 1, 1, height - 2),
            ('right', width - 3, 1, 1, height - 2),
        ):
            edge = self.query_one('#console-edge-' + name)
            edge.styles.offset = (x, y)
            edge.styles.width, edge.styles.height = w, h


def compose_workspace(content):
    """One scroll owner, one reserved rail, independent of the page's length."""
    with ConsolePanel(id='console-panel'):
        for edge in ('top', 'bottom', 'left', 'right'):
            yield Static('', id='console-edge-' + edge, classes='console-edge')
        with VerticalScroll(id='console-workspace'):
            with Vertical(id='console-content'):
                yield from content
    yield Footer()


async def install_console(screen):
    if screen.query('#console-heading'):
        return
    section, title = CONTEXTS.get(type(screen).__name__, ('setup', 'EXPERIMENT / 01 SETUP'))
    if type(screen).__name__ in {'SourceView','CodeViewScreen','JsonPresetEditor','StimulusValueEditor'}:
        previous = list(screen.app.screen_stack)
        previous = previous[:previous.index(screen)]
        if previous:
            section = getattr(previous[-1], 'console_section', 'setup')
        title = dict((key,label.upper()) for key,label,_ in PAGES)[section] + ' / ' + {
            'SourceView':'SOURCE','CodeViewScreen':'SOURCE','JsonPresetEditor':'PRESET','StimulusValueEditor':'STIMULUS VALUES'
        }[type(screen).__name__]
    screen.console_section = section
    screen.add_class('laboratory-console')
    for button in screen.query('#console-workspace Button'):
        if button.tooltip is None:
            button.tooltip = str(button.label)
    await screen.mount(Static('PsyCoLab / '+title,id='console-heading',markup=False),
                       LaboratoryNavigation(section,title),before=0)


class ConsoleScreen(Screen):
    def compose(self):
        yield from compose_workspace(self.compose_content())

    async def _on_mount(self):
        await install_console(self)


CONSOLE_CSS = """
/* The only owner of researcher application geometry and visual styling. */
Screen.laboratory-console { background: #080808; color: #eeeeee; align: left top; layout: grid; grid-size: 2 3; grid-columns: 23 1fr; grid-rows: 2 1fr 1; }
Screen.console-compact { grid-columns: 17 1fr; }
#console-heading { column-span: 2; height: 2; width: 100%; padding: 0 1;
    background: #080808; color: #eeeeee; border-bottom: solid #555555; }
#hub-nav { width: 23; height: 100%; margin: 0;
    padding: 0 1; background: #080808; border: none; overflow-y: auto; scrollbar-size: 1 1; }
.console-compact #hub-nav { width: 17; padding: 0; }
#laboratory-label { height: 1; color: #999999; }
#hub-nav Button { width: 100%; height: 2; min-width: 0; padding: 0; margin: 0;
    border: none; background: #080808; color: #cccccc; content-align: left middle; text-align: left; }
#hub-nav Button.nav-child { height: 1; }
#hub-nav Button.nav-selected { color: #ffffff; text-style: bold; }
#hub-nav Button:focus, #hub-nav Button:hover { background: #333333; color: #ffffff; }
#nav-context { height: 2; color: #bbbbbb; }
#hub-nav #refresh-psycolab { height: 1; margin: 0; color: #aaaaaa; }
Screen.laboratory-console Footer { dock: none; column-span: 2; height: 1; background: #181818; color: #cccccc; }
FooterKey > .footer-key--key { background: #303030; color: #ffffff; }
FooterKey > .footer-key--description { background: #181818; color: #cccccc; }
#console-panel { width: 100%; height: 100%; layers: content frame; }
.console-edge { layer: frame; position: absolute; background: transparent; }
#console-edge-top, #console-edge-bottom { border-top: solid #555555; }
#console-edge-left { border-left: solid #555555; }
#console-edge-right { border-right: solid #555555; }
#console-workspace { layer: content; width: 100%; height: 100%; border: none; padding: 1 0 1 2;
    background: transparent; overflow-x: hidden; overflow-y: auto;
    scrollbar-gutter: stable; scrollbar-size: 1 1; scrollbar-background: #151515;
    scrollbar-color: #666666; scrollbar-color-hover: #999999; scrollbar-color-active: #cccccc; }
/* Former per-page scrolling containers are now content-sized groups. Tables
   and text editors retain deliberate internal scrolling. */
#console-workspace VerticalScroll { height: auto; width: 100%; overflow: hidden; padding: 0; border: none; }
#console-workspace Vertical, #console-workspace ContentSwitcher { height: auto; width: 100%; }
#console-workspace #console-content { width: 1fr; margin-right: 3; }
#setup-columns { layout: vertical; height: auto; width: 100%; }
#fixed-shell { dock: none; height: auto; width: 100%; padding: 0; margin: 0; }
#console-workspace Static, #console-workspace Label { height: auto; }
#console-workspace Label { margin-top: 1; width: 100%; }
#console-workspace Input, #console-workspace Select { width: 64; max-width: 100%; }
#console-workspace Input { background: #181818; color: #eeeeee; border: solid #444444; }
#console-workspace Input:focus { border: solid #dddddd; }
#console-workspace SelectCurrent { background: #181818; color: #eeeeee; border: solid #444444; }
#console-workspace Select:focus SelectCurrent { border: solid #dddddd; }
SelectOverlay { background: #181818; color: #eeeeee; border: solid #777777; }
SelectOverlay > .option-list--highlighted { background: #dddddd; color: #080808; }
#console-workspace Button { width: 34; max-width: 100%; min-width: 0; height: 3;
    margin: 0; padding: 0 1; background: #111111; color: #eeeeee; border: solid #444444; }
#console-workspace Button:focus, #console-workspace Button:hover { background: #dddddd; color: #080808; border: solid #dddddd; }
#console-workspace Button:disabled { color: #777777; border: solid #222222; background: #080808; }
#console-workspace .buttons { layout: vertical; height: auto; width: 100%; align-horizontal: left; }
#console-workspace .field-row { height: 3; width: 64; max-width: 100%; }
#console-workspace .field-row Input { width: 1fr; }
#console-workspace .field-row Button { width: 13; }
#console-workspace Collapsible { padding: 0; margin: 1 0; border: none; background: #080808; }
#console-workspace CollapsibleTitle { background: #181818; color: #cccccc; }
#console-workspace .section-title { margin: 1 0 0 0; padding: 0; text-style: bold;
    color: #ffffff; border-top: solid #444444; }
#console-workspace .form-section { height: auto; width: 100%; border: solid #333333; padding: 0 1 1 1; margin: 0 0 1 0; }
#console-workspace .form-section .section-title { border: none; margin: 0; }
#console-workspace .field-help { color: #aaaaaa; margin-bottom: 1; }
#console-workspace .info-card { padding: 0; margin: 1 0; background: #080808; border: none; }
#console-workspace #setup-side { margin-top: 1; }
#console-workspace #data-root { width: 100%; }
#console-workspace Checkbox { background: #080808; color: #eeeeee; border: none; }
Checkbox > .toggle--button { color: #aaaaaa; background: #080808; }
#console-workspace DataTable { height: 22; width: 100%; background: #080808; color: #eeeeee; scrollbar-size: 1 1; scrollbar-background: #151515; scrollbar-color: #666666; }
#console-workspace #resolved-settings-table { height: 14; }
.console-compact #console-workspace #resolved-settings-table { height: 8; }
/* Keep the established shell and narrow-screen routes. Only Review's toolbar
   uses spare width; its same controls stack vertically on compact terminals. */
#console-workspace #review-table-actions { layout: grid; grid-size: 2;
    grid-columns: 1fr 1fr; grid-rows: 3; height: 9; }
#console-workspace #review-table-actions Button { width: 100%; }
.console-compact #console-workspace #review-table-actions { layout: vertical; height: auto; }
#console-workspace #review-file-location { border-left: solid #555555;
    padding: 0 1; margin-top: 1; }
#console-workspace #review-authority-legend { color: #bbbbbb; }
DataTable > .datatable--header { background: #333333; color: #ffffff; }
DataTable > .datatable--odd-row { background: #101010; }
DataTable > .datatable--cursor { background: #cccccc; color: #080808; }
#console-workspace TextArea { height: 20; width: 100%; border: solid #444444; }
/* Calibration status is semantic, not decoration. Text and symbols accompany colour. */
#calibration-stage-nav { layout: horizontal; height: 3; width: 100%; }
#console-workspace #calibration-stage-nav Button { width: 1fr; padding: 0; height: 3; border: none; }
#console-workspace #calibration-stage-nav Button.-success { color: #86b98c; }
#console-workspace #calibration-stage-nav Button.-warning { color: #d1b875; }
#console-workspace #calibration-stage-nav Button.-error { color: #d09393; }
#console-workspace #calibration-stage-nav Button.calibration-active { text-style: bold underline; }
.console-compact #console-workspace #calibration-stage-nav,
.console-compact #console-workspace #calibration-stage-nav Button { height: 1; }
DisplayCheckScreen #console-workspace #fixed-shell .buttons { layout: horizontal; height: 3; }
DisplayCheckScreen #console-workspace #fixed-shell .buttons Button { width: 1fr; padding: 0; }
DisplayCheckScreen.console-compact #console-workspace #fixed-shell .buttons,
DisplayCheckScreen.console-compact #console-workspace #fixed-shell .buttons Button { height: 1; border: none; }
#console-workspace .invalid-input { border: solid #d09393; }
#console-workspace .readiness-next, #console-workspace .readiness-blocked { border-left: solid #d1b875; }
#console-workspace .readiness-done { border-left: solid #86b98c; }
"""
