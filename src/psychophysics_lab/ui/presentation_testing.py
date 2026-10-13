from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Static,Checkbox,Button

class PresentationTestScreen(ModalScreen):
    def __init__(self,request): super().__init__(); self.request=request
    def compose(self):
        with Vertical():
            yield Static('UNCALIBRATED PRESENTATION TEST\nReal fullscreen rendering and keyboard responses, isolated test files. These are not scientifically valid human participant records. This does not verify or qualify the monitor. Unsafe shader commands and framebuffer configurations remain blocked.',markup=False)
            yield Checkbox('I understand these are uncalibrated test records, excluded from human acquisition.',id='presentation-ack')
            yield Button('Launch uncalibrated presentation',id='presentation-launch',variant='warning')
            yield Button('Cancel',id='presentation-cancel')
            yield Static('',id='presentation-feedback',markup=False)
    def on_button_pressed(self,event):
        if event.button.id=='presentation-cancel': self.app.pop_screen(); return
        if event.button.id=='presentation-launch':
            try:
                if not self.query_one('#presentation-ack',Checkbox).value: raise ValueError('Acknowledge the test-data distinction before launch.')
                from ..core.presentation_testing import PresentationTestRequest,validate_presentation
                from ..config.monitor import load_monitor_profiles
                from ..experiments.registry import get_experiment
                profile=load_monitor_profiles(self.app.repo_root)[self.request.monitor_profile_id]
                validate_presentation(self.request,get_experiment(self.request.experiment_id),profile)
                self.app.exit(PresentationTestRequest(self.request))
            except (ValueError,OSError) as exc: self.query_one('#presentation-feedback',Static).update(str(exc))
