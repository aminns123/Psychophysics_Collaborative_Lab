"""Focused laboratory declarations and registered experiment qualification."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.widgets import Button, Checkbox, Header, Footer, Input, Select, Static, Label

from ..config.calibration_review import save_verification, qualify_experiment
from ..config.preflight import qualification_checks
from ..experiments.registry import list_experiments, get_experiment


class PhysicalVerificationScreen(Screen):
    def __init__(self, profile, *, experiment_id=None, focus_category=None):
        super().__init__()
        self.profile = profile
        self.experiment_id = experiment_id
        self.focus_category = focus_category

    def compose(self) -> ComposeResult:
        with Vertical(id='fixed-shell'):
            yield Header()
            with Horizontal(classes='buttons'):
                yield Button('Back to Review', id='verification-back')
                yield Button('Save verification declarations', id='verification-save', variant='primary')
            yield Static('', id='verification-feedback', markup=False)
        with VerticalScroll(classes='page-body'):
            yield Static('Physical verification is an explicit laboratory declaration. Saved software tests and a green setup page do not measure emitted light or photon timing. Changing verification does not qualify an experiment.')
            from ..config.calibration_review import luminance_verification_guidance
            yield Static(luminance_verification_guidance(self.profile, self.app.local_config_root),
                         markup=False, id='verification-luminance-guidance')
            yield Button('Inspect existing luminance measurements', id='verification-open-luminance')
            for key, label, explanation in (
                ('geometry_status','Geometry','Review the compatible ruler measurement, measured active dimensions and eye distance against your laboratory criteria.'),
                ('calibration_status','Photometry','Use actual photometer observations. Test/fake data cannot be verified. Notes are optional for setup completion.'),
                ('timing_status','Photon timing','Use independently recorded photodiode or equivalent evidence. OS refresh and software flips are insufficient.'),
            ):
                yield Label(label)
                from ..config.calibration_progress import calibration_progress
                state_key = {"geometry_status":"geometry","calibration_status":"luminance","timing_status":"timing"}[key]
                state = calibration_progress(self.profile,self.app.local_config_root)[state_key]
                required = self.experiment_id is not None and state_key in get_experiment(self.experiment_id).calibration_requirements
                evidence = (f"{len(self.profile.luminance_calibration)} pairs saved; method: {self.profile.calibration_method or 'not recorded'}" if state_key=="luminance" else
                            "Compatible diagnostic reports: " + (", ".join(state.get("reports",())) or "none"))
                yield Static(explanation + "\nCurrent status: " + getattr(self.profile,key) + "\n" + evidence
                    + ("\nRequired for selected experiment." if required else "\nNot required by a selected experiment / independent laboratory review."),markup=False)
                yield Select([('Unverified','unverified'),('Measurements entered; unverified','manual_unverified'),('Verified — manually declared','verified')],value=getattr(self.profile,key),allow_blank=False,id='verification-'+key)
            yield Label('Actual photometer instrument / method (needed to declare photometry verified)')
            yield Input(value=self.profile.calibration_method,id='verification-method')
            yield Checkbox('I independently reviewed the changed Verified declarations with actual instruments and the laboratory criteria; supporting evidence is retained by the laboratory.',id='verification-reviewed')
        yield Footer()

    def on_screen_resume(self):
        """Refresh saved evidence after a child editor, without creating revisions."""
        if not self.is_mounted:
            return
        from ..config.calibration_review import luminance_verification_guidance
        self.app.reload_profiles()
        current = self.app.monitor_profiles.get(self.profile.id)
        if current is None:
            self.query_one('#verification-feedback', Static).update(
                'Selected monitor profile is no longer available. Return to Calibrate and select it explicitly.'
            )
            return
        if current != self.profile:
            self.profile = current
            for key in ('geometry_status', 'calibration_status', 'timing_status'):
                self.query_one('#verification-' + key, Select).value = getattr(current, key)
            self.query_one('#verification-method', Input).value = current.calibration_method
            self.query_one('#verification-feedback', Static).update(
                'Saved calibration has changed. Verification fields were refreshed; '
                'review instrument evidence before making declarations.'
            )
        self.query_one('#verification-luminance-guidance', Static).update(
            luminance_verification_guidance(self.profile, self.app.local_config_root)
        )

    def on_mount(self):
        if self.focus_category:
            target=self.query_one('#verification-'+self.focus_category,Select)
            self.call_after_refresh(target.scroll_visible)
            self.call_after_refresh(target.focus)

    def on_button_pressed(self,event):
        if event.button.id=='verification-back':
            self.app.pop_screen()
        elif event.button.id=='verification-open-luminance':
            from ..config.calibration_dataset import load_active
            try:
                load_active(self.app.local_config_root, self.profile)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.query_one('#verification-feedback', Static).update(
                    'Could not load current readings: ' + str(exc)
                    + ' Original records remain intact. Review the selected '
                      'display under Calibrate → Luminance.'
                )
            else:
                from .luminance_data import LuminanceDataScreen
                self.app.push_screen(
                    LuminanceDataScreen(self.profile, experiment_id=self.experiment_id)
                )
        elif event.button.id=='verification-save':
            try:
                result=save_verification(self.profile,self.app.local_config_root,
                    **{key:str(self.query_one('#verification-'+key,Select).value) for key in ('geometry_status','calibration_status','timing_status')},
                    calibration_method=self.query_one('#verification-method',Input).value,
                    reviewed=self.query_one('#verification-reviewed',Checkbox).value)
                self.app.reload_profiles()
                if self.app.monitor_profiles.get(result.id)!=result:
                    raise RuntimeError('Saved verification could not be reloaded. Inspect local configuration.')
                self.app.notify('No changes to save.' if result.revision==self.profile.revision else 'Verification declarations saved. Experiment qualification remains separate.',timeout=10)
                self.app.pop_screen()
            except (OSError,ValueError,RuntimeError) as exc:
                self.query_one('#verification-feedback',Static).update(str(exc))


class ExperimentQualificationScreen(Screen):
    def __init__(self,profile,*,experiment_id=None,values=None):
        super().__init__()
        self.profile=profile
        self.experiment_id=experiment_id
        self.values=values

    def compose(self) -> ComposeResult:
        with Vertical(id='fixed-shell'):
            yield Header()
            with Horizontal(classes='buttons'):
                yield Button('Back to Review',id='qualification-back')
                yield Button('Explicitly qualify selected experiment',id='qualification-save',variant='primary')
            yield Static('',id='qualification-feedback',markup=False)
        with VerticalScroll(classes='page-body'):
            yield Static(f'Selected display: {self.profile.display_name}. Qualification applies only to this saved display and selected experiment. Verified flags are manually declared, not independently measured by PsyCoLab. Final human preflight still checks the actual experiment settings and connected display.')
            specs=list_experiments()
            yield Select([(spec.display_name,spec.id) for spec in specs],value=self.experiment_id or specs[0].id,allow_blank=False,id='qualification-experiment')
            yield Static('',id='qualification-checks',markup=False)
            for key,label in [('binding','Bind display / resolution'),('geometry','Review geometry evidence'),('luminance','Open luminance measurements and verification'),('timing','Review photon timing evidence'),('contrast','Edit starting probe intensity / current range')]:
                yield Button(label,id='qualification-resolve-'+key)
            yield Checkbox('The laboratory reviewed this experiment on this display, including its stimulus/protocol requirements and supporting physical evidence.',id='qualification-reviewed')
        yield Footer()

    def _spec_values(self):
        spec=get_experiment(str(self.query_one('#qualification-experiment',Select).value))
        # Use an actual existing draft, never invent scientific parameter values.
        candidates=[values for (_,experiment,profile),values in self.app.config_drafts.items() if experiment==spec.id and profile==self.profile.id]
        return spec,self.values if spec.id==self.experiment_id and self.values is not None else candidates[-1] if candidates else None

    def _refresh(self):
        if not self.is_mounted: return
        spec,values=self._spec_values()
        checks=qualification_checks(spec,self.profile,values)
        text='\n\n'.join(('PASS' if item['passed'] else 'BLOCKED')+': '+item['name']+'\n'+item['detail'] for item in checks)
        if values is None:
            text+='\n\nNo experiment parameter draft is available. Qualification covers declared hardware requirements; configure and Review the experiment before acquisition.'
        if spec.id in self.profile.qualified_experiments:
            text+='\n\nQualification is already declared; unchanged Save will not create a revision.'
        for key in ('binding','geometry','luminance','timing','contrast'):
            self.query_one('#qualification-resolve-'+key,Button).display=key=='binding' or key in spec.calibration_requirements or key=='contrast' and spec.id=='contrast_sensitivity'
        self.query_one('#qualification-checks',Static).update(text)
        self.query_one('#qualification-save',Button).disabled=not all(item['passed'] for item in checks)

    def on_mount(self): self._refresh()

    def on_screen_resume(self):
        if self.is_mounted:
            self.app.reload_profiles(); self.profile=self.app.monitor_profiles[self.profile.id]; self._refresh()

    def on_select_changed(self,event):
        if event.select.id=='qualification-experiment':
            self.query_one('#qualification-reviewed',Checkbox).value=False
            self._refresh()

    def on_button_pressed(self,event):
        if (event.button.id or '').startswith('qualification-resolve-'):
            key=event.button.id.removeprefix('qualification-resolve-')
            spec,values=self._spec_values()
            from .setup import ReviewScreen,ExperimentConfigScreen
            parent=self.app.screen_stack[-2]
            if isinstance(parent,ReviewScreen) and parent.request.experiment_id==spec.id:
                self.app.pop_screen(); parent.resolve_requirement(key); return
            if key=='luminance':
                from .luminance_data import LuminanceDataScreen
                self.app.push_screen(LuminanceDataScreen(self.profile,experiment_id=spec.id))
            elif key=='binding':
                from .profiles import ProfileScreen
                self.app.push_screen(ProfileScreen(profile=self.profile,focus_field='profile-binding'))
            elif key=='contrast':
                self.app.push_screen(ExperimentConfigScreen(data_root=self.app.data_root,participant_id='synthetic_preview',session_mode='new',experiment=spec,monitor_profile_id=self.profile.id,defaults=values or spec.field_defaults(),focus_field='starting_probe_intensity' if spec.id=='contrast_sensitivity' else None))
            else: self.app.push_screen(PhysicalVerificationScreen(self.profile,experiment_id=spec.id,focus_category=key+'_status'))
            return
        if event.button.id=='qualification-back':
            self.app.pop_screen()
        elif event.button.id=='qualification-save':
            try:
                spec,values=self._spec_values()
                result=qualify_experiment(self.profile,self.app.local_config_root,spec,
                    reviewed=self.query_one('#qualification-reviewed',Checkbox).value,values=values)
                self.app.reload_profiles()
                if self.app.monitor_profiles.get(result.id)!=result:
                    raise RuntimeError('Saved qualification could not be reloaded.')
                self.app.notify('No changes to save.' if result.revision==self.profile.revision else f'Explicit qualification saved for {spec.display_name}.',timeout=10)
                self.app.pop_screen()
            except (OSError,ValueError,RuntimeError) as exc:
                self.query_one('#qualification-feedback',Static).update(str(exc))
