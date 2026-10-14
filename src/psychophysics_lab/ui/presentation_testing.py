from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Static,Checkbox,Button

class PresentationTestScreen(ModalScreen):
    def __init__(self,request): super().__init__(); self.request=request
    def compose(self):
        with Vertical():
            yield Static('TEST PRESENTATION — real fullscreen stimuli, isolated test files.\n'
                         'No photometer required. Monitor binding, framebuffer and digital '
                         'contrast safeguards still apply. NOT for real participant data.',markup=False)
            yield Checkbox('Yes — save this run as TEST DATA, not a human record.',id='presentation-ack')
            yield Button('Start test presentation',id='presentation-launch',variant='warning')
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
