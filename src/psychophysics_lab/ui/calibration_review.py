"""Focused laboratory declarations and registered experiment qualification."""
from textual.app import ComposeResult
from .console import ConsoleScreen as Screen
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.widgets import Button, Checkbox, Input, Select, Static, Label, Collapsible
from .checkbox import ExplicitCheckbox as Checkbox

from ..config.calibration_review import save_verification, save_one_verification, qualify_experiment
from ..config.preflight import qualification_checks
from psychophysics_lab.experiments._internal.registry import list_experiments, get_experiment


class PhysicalVerificationScreen(Screen):
    def __init__(self, profile, *, experiment_id=None, focus_category=None):
        super().__init__()
        self.profile = profile
        self.experiment_id = experiment_id
        self.focus_category = focus_category

    def compose_content(self) -> ComposeResult:
        from ..config.calibration_review import luminance_verification_guidance
        from ..config.calibration_progress import calibration_progress
        from ..config.models import photometry_is_test_data
        progress=calibration_progress(self.profile,self.app.local_config_root)
        category=self.focus_category if self.focus_category in (
            'geometry_status','calibration_status','timing_status') else 'geometry_status'
        with Vertical(id='fixed-shell'):
            with Horizontal(classes='buttons'):
                yield Button('Back to Review', id='verification-back')
                yield Button('Save this check', id='verification-save-category', variant='primary')
            yield Static('', id='verification-feedback', markup=False)
        with VerticalScroll(classes='page-body'):
            yield Static('Select one check. Choose No / Saved / Yes. '
                         'Save each category independently. Test data are never physical proof.',
                         markup=False)
            yield Label('Which measurement are you reviewing?')
            yield Select([('Geometry — ruler and measured display','geometry_status'),
                          ('Photometry — actual luminance meter','calibration_status'),
                          ('Photon timing — external sensor','timing_status')],
                         value=category, allow_blank=False, id='verification-category')
            yield Static('',id='verification-category-guidance',markup=False)
            for key,label,detail in (
                ('geometry_status','Geometry','Check measured active image size, eye distance and the saved ruler error.'),
                ('calibration_status','Photometry','Actual photometer readings are required for physical verification.'),
                ('timing_status','Photon timing','Independent photodiode or equivalent timing evidence is required.'),
            ):
                with Vertical(id='verification-panel-'+key):
                    yield Static(label+' — '+detail,markup=False)
                    stage={'geometry_status':'geometry',
                           'calibration_status':'luminance',
                           'timing_status':'timing'}[key]
                    evidence=(f"{len(self.profile.luminance_calibration)} intensity/luminance pairs saved"
                              if stage=='luminance' else
                              'Compatible reports: '+(', '.join(progress[stage].get('reports',())) or 'none'))
                    yield Static('Current: '+getattr(self.profile,key).replace('_',' ')+'\n'+evidence,
                                 markup=False,id='verification-evidence-'+key)
                    if key=='calibration_status':
                        yield Static(luminance_verification_guidance(
                            self.profile,self.app.local_config_root),
                            markup=False,id='verification-luminance-guidance')
                        yield Button('Inspect saved luminance readings',id='verification-open-luminance')
                    options=[('No — not verified','unverified'),
                             ('Measurements saved — not verified','manual_unverified'),
                             ('Yes — I have reviewed physical evidence','verified')]
                    if key=='calibration_status' and photometry_is_test_data(self.profile):
                        options=options[:-1]  # Synthetic readings cannot be certified.
                    initial=getattr(self.profile,key)
                    if key=='calibration_status' and initial=='accepted':
                        options.append(('Mapping accepted by researcher (physical verification still pending)','accepted'))
                    if initial not in [value for _,value in options]:
                        initial='manual_unverified'
                    yield Select(options,value=initial,allow_blank=False,id='verification-'+key)
                    if key=='calibration_status':
                        yield Label('Photometer name / model (only for actual readings)')
                        yield Input(value=self.profile.calibration_method,id='verification-method')
            yield Checkbox('Yes — I reviewed real laboratory evidence for this check.',
                           id='verification-reviewed')
            with Collapsible(title='Advanced — save all declarations together',collapsed=True):
                yield Button('Save verification declarations',id='verification-save')

    def _refresh_category(self):
        if not self.is_mounted:
            return
        selected=self.query_one('#verification-category',Select).value
        labels={'geometry_status':'Geometry','calibration_status':'Photometry','timing_status':'Photon timing'}
        for key in labels:
            self.query_one('#verification-panel-'+key,Vertical).display=key==selected
        if selected not in labels:
            return
        from ..config.models import photometry_is_test_data
        if selected=='calibration_status' and self.profile.calibration_status=='accepted':
            explanation='Mapping accepted; this does NOT verify physical photometry. Fake/example values remain test evidence only.'
        elif selected=='calibration_status' and photometry_is_test_data(self.profile):
            explanation='TEST VALUES SAVED — real photometer readings required before physical verification. Do not change their source label.'
        elif selected=='geometry_status':
            explanation='Review the saved ruler measurement and actual screen geometry, then choose Yes only when they agree under laboratory criteria.'
        elif selected=='timing_status':
            explanation='Software timing is not photon timing. Choose Yes only with independently measured physical timing evidence.'
        else:
            explanation='Check actual photometer readings and the current display before choosing Yes. Saved values alone are not a physical certificate.'
        self.query_one('#verification-category-guidance',Static).update(explanation)

    def on_select_changed(self,event):
        if event.select.id=='verification-category' and self.is_mounted:
            self.query_one('#verification-reviewed',Checkbox).value=False
            self._refresh_category()

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
            from ..config.models import photometry_is_test_data
            photo=self.query_one('#verification-calibration_status',Select)
            with self.prevent(Select.Changed):
                choices=[('No — not verified','unverified'),
                         ('Measurements saved — not verified','manual_unverified')]
                if not photometry_is_test_data(current):
                    choices.append(('Yes — I have reviewed physical evidence','verified'))
                if current.calibration_status=='accepted':
                    choices.append(('Mapping accepted by researcher (not physically verified)','accepted'))
                photo.set_options(choices)
                for key in ('geometry_status', 'calibration_status', 'timing_status'):
                    selector=self.query_one('#verification-' + key,Select)
                    status=getattr(current,key)
                    selector.value=status if status in [val for _,val in selector._options] else 'manual_unverified'
            self.query_one('#verification-method', Input).value = current.calibration_method
            self.query_one('#verification-feedback', Static).update(
                'Saved calibration has changed. Verification fields were refreshed; '
                'review instrument evidence before making declarations.'
            )
        self.query_one('#verification-luminance-guidance', Static).update(
            luminance_verification_guidance(self.profile, self.app.local_config_root)
        )
        self._refresh_category()

    def on_mount(self):
        self._refresh_category()
        if self.focus_category in ('geometry_status','calibration_status','timing_status'):
            self.call_after_refresh(self.query_one('#verification-category',Select).focus)

    def on_button_pressed(self,event):
        if event.button.id=='verification-back':
            self.app.pop_screen()
        elif event.button.id=='verification-open-luminance':
            from .luminance_data import open_luminance_editor
            error = open_luminance_editor(
                self.app, self.profile, experiment_id=self.experiment_id
            )
            if error:
                self.query_one('#verification-feedback', Static).update(error)
        elif event.button.id=='verification-save-category':
            try:
                category=str(self.query_one('#verification-category',Select).value)
                status=str(self.query_one('#verification-'+category,Select).value)
                result=save_one_verification(
                    self.profile,self.app.local_config_root,category=category,
                    status=status,reviewed=self.query_one('#verification-reviewed',Checkbox).value,
                    calibration_method=(self.query_one('#verification-method',Input).value
                                        if category=='calibration_status' else None),
                )
                self.app.reload_profiles()
                if self.app.monitor_profiles.get(result.id)!=result:
                    raise RuntimeError('Saved verification could not be reloaded.')
                changed=result.revision!=self.profile.revision
                self.profile=result
                for key in ('geometry_status','calibration_status','timing_status'):
                    selector=self.query_one('#verification-'+key,Select)
                    if getattr(result,key) in [value for _,value in selector._options]:
                        selector.value=getattr(result,key)
                    self.query_one('#verification-evidence-'+key,Static).update(
                        'Current: '+getattr(result,key).replace('_',' '))
                self.query_one('#verification-reviewed',Checkbox).value=False
                self.query_one('#verification-feedback',Static).update(
                    ('Saved '+{'geometry_status':'Geometry','calibration_status':'Photometry',
                               'timing_status':'Photon timing'}[category]+'. Other categories unchanged.'
                     if changed else 'Already saved — nothing changed.')
                )
                self._refresh_category()
            except (OSError,ValueError,RuntimeError,TypeError) as exc:
                self.query_one('#verification-feedback',Static).update(str(exc))
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

    def compose_content(self) -> ComposeResult:
        with Vertical(id='fixed-shell'):
            with Horizontal(classes='buttons'):
                yield Button('Back to Review',id='qualification-back')
                yield Button('Explicitly qualify selected experiment',id='qualification-save',variant='primary')
            yield Static('',id='qualification-feedback',markup=False)
        with VerticalScroll(classes='page-body'):
            yield Static(f'Selected display: {self.profile.display_name}. Qualification applies only to this saved display and selected experiment. Verified flags are manually declared, not independently measured by PsyCoLab. Final human preflight still checks the actual experiment settings and connected display.')
            specs=list_experiments(include_historical=self.app.include_historical)
            yield Select([(spec.display_name,spec.id) for spec in specs],value=self.experiment_id or specs[0].id,allow_blank=False,id='qualification-experiment')
            yield Static('',id='qualification-overview',markup=False)
            for key,label in [('binding','Bind display / resolution'),('geometry','Review geometry evidence'),('luminance','Open luminance measurements and verification'),('timing','Review photon timing evidence'),('contrast','Edit starting probe intensity / current range')]:
                yield Button(label,id='qualification-resolve-'+key)
            yield Checkbox('Yes — I reviewed this experiment and its physical evidence.',id='qualification-reviewed')
            with Collapsible(title='Advanced — detailed scientific qualification checks',collapsed=True):
                yield Static('',id='qualification-checks',markup=False)

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
            self.query_one('#qualification-resolve-'+key,Button).display=key=='binding' or key in spec.calibration_requirements or key=='contrast' and spec.id=='legacy_contrast_sensitivity'
        self.query_one('#qualification-checks',Static).update(text)
        failures=[item for item in checks if not item['passed']]
        self.query_one('#qualification-overview',Static).update(
            'Ready to qualify this experiment.' if not failures else
            str(len(failures))+' requirement(s) still need attention: '+
            ', '.join(item['name'] for item in failures)+
            '. Use the corresponding action above; details are under Advanced.'
        )
        self.query_one('#qualification-save',Button).disabled=bool(failures)

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
            from .setup import ReviewScreen,ExperimentParametersScreen
            parent=self.app.screen_stack[-2]
            if isinstance(parent,ReviewScreen) and parent.request.experiment_id==spec.id:
                self.app.pop_screen(); parent.resolve_requirement(key); return
            if key=='luminance':
                from .luminance_data import open_luminance_editor
                error = open_luminance_editor(self.app, self.profile, experiment_id=spec.id)
                if error:
                    self.query_one('#qualification-feedback', Static).update(error)
            elif key=='binding':
                from .profiles import ProfileScreen
                self.app.push_screen(ProfileScreen(profile=self.profile,focus_field='profile-binding'))
            elif key=='contrast':
                self.app.push_screen(ExperimentParametersScreen(data_root=self.app.data_root,participant_id='synthetic_preview',session_mode='new',experiment=spec,monitor_profile_id=self.profile.id,defaults=values or spec.field_defaults(),focus_field='starting_probe_intensity' if spec.id=='legacy_contrast_sensitivity' else None))
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
