"""Focused active luminance editor: draft/preview first, explicit atomic Save."""
from copy import deepcopy
from pathlib import Path
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Header, Footer, Button, Input, Select, Checkbox, Static, Label, Collapsible
from ..config.calibration_dataset import (load_active,save_active,accept_active,observation,summary,merge_observations,
    import_observations,luminance_state,physical_snapshot,active_directory,
    physical_snapshot_differences,replacement_draft_for_current_display)


def open_luminance_editor(app, profile, *, experiment_id=None):
    """Open safely or return an actionable message instead of crashing Textual.

    An active dataset can be missing, unreadable or inconsistent with a
    committed profile. Such records must be inspected/recovered rather than
    silently overwritten on opening an editor.
    """
    try:
        dataset = load_active(app.local_config_root, profile)
        summary(dataset)  # Validate the rows needed to compose the editor.
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        return (
            "Cannot open the active luminance dataset: " + str(exc)
            + " Original profile history and observations are preserved. "
              "Inspect this display's current luminance.json and .history "
              "before replacing data; no measurements have been changed."
        )
    app.push_screen(LuminanceDataScreen(profile, experiment_id=experiment_id))
    return None


class LuminanceDataScreen(Screen):
    def __init__(self,profile,*,experiment_id=None):
        super().__init__(); self.profile=profile; self.experiment_id=experiment_id
        self._replacement_started = False
        self._physical_changes = {}

    def compose(self):
        self.saved=load_active(self.app.local_config_root,self.profile); self.draft=deepcopy(self.saved)
        self._physical_changes=physical_snapshot_differences(self.profile,self.saved)
        with Vertical(id='fixed-shell'):
            yield Header()
            with Horizontal(classes='buttons'):
                yield Button('Discard draft / Back',id='dataset-back')
                yield Button('Save active dataset',id='dataset-save',variant='primary')
            yield Button('Accept luminance values → Output precision',id='dataset-accept',variant='success')
            yield Static('',id='dataset-feedback',markup=False)
        with VerticalScroll(classes='page-body'):
            yield Static('[b]LUMINANCE[/b]   1. Enter intensity and luminance. 2. Add readings to draft. '
                         '3. Review the table and Accept luminance values. '
                         'To keep the existing mapping, simply accept it. '
                         'Acceptance retains test/meter source labels and does not physically verify them.',
                         markup=True, classes='info-card')
            yield Static('',id='dataset-replacement-guidance',markup=False,classes='info-card')
            yield Checkbox('Yes — keep the previous readings in history and start a NEW dataset for this screen.',
                           id='dataset-start-confirm')
            yield Button('Start new measurements for THIS display',id='dataset-start-current',variant='warning')
            yield Button('Continue without acceptance → Experiment Test mode',id='dataset-keep-test')
            yield Button('Discard draft; keep saved values',id='dataset-discard')
            yield Static('',id='dataset-next-step',markup=False,classes='info-card')
            yield Static('',id='dataset-state',markup=False)
            yield Static('',id='dataset-statistics',markup=False)
            yield Label('Choose an action')
            yield Select([('Add a luminance reading','add'),('Correct saved readings','correct'),('Import measurements (Advanced)','import')],
                         value='add',allow_blank=False,id='dataset-task')
            yield Label('Digital intensity (0–1)')
            yield Select([('New intensity','new')]+[(f"{r['screen_intensity']:g} — {r['luminance_cdm2']:g} cd/m²",str(r['screen_intensity'])) for r in summary(self.draft)],
                         value='new',allow_blank=False,id='dataset-selected')
            yield Input(value='0.5',id='dataset-command')
            yield Label('Luminance (cd/m²) — enter one value or repeat readings separated by commas')
            yield Input(value='',id='dataset-readings',placeholder='e.g. 25.1, 24.9, 25.2')
            yield Label('Where did these values come from?')
            yield Select([('Test values — not physically calibrated','synthetic'),
                          ('Actual photometer readings — verification still required','genuine'),
                          ('Source not recorded — unverified','unspecified')],
                         value='synthetic' if (self.draft.get('data_kind')=='synthetic' or 'fake' in self.draft.get('method','').lower()) else 'unspecified',
                         allow_blank=False,id='dataset-kind')
            yield Button('Use selected readings for correction',id='dataset-load-readings')
            yield Checkbox('Yes — replace this intensity’s old readings; history is kept.',id='dataset-confirm')
            yield Button('Add readings to draft',id='dataset-add')
            yield Static('Save active dataset keeps readings pending approval. Accept luminance values saves and approves the mapping.',markup=False)
            with Collapsible(title='Advanced — raw readings, JSON import/export, reset',collapsed=True):
                yield Static('',id='dataset-raw',markup=False)
                yield Static('',id='dataset-data-location',markup=False)
                yield Label('How to combine observations')
                yield Select([('Keep existing readings and add repetitions','merge'),
                              ('Add a new intensity','append'),
                              ('Replace readings at one intensity','replace_selected'),
                              ('Replace the entire dataset','replace_all')],
                             value='merge',allow_blank=False,id='dataset-mode')
                yield Button('Reset to empty draft (confirmation required)',id='dataset-reset')
                yield Label('Photometer instrument / method (optional for test data)')
                yield Input(value=self.draft.get('method',''),id='dataset-method')
                yield Label('Optional measurement date (YYYY-MM-DD)')
                yield Input(value=self.draft.get('date',''),id='dataset-date')
                yield Label('Optional notes')
                yield Input(value=self.draft.get('notes',''),id='dataset-notes')
                yield Label('Import existing measurement JSON (advanced)')
                yield Input(value='',id='dataset-import-path')
                yield Button('Preview JSON import into draft',id='dataset-import')
                yield Label('Export saved dataset to a new absolute JSON file')
                yield Input(value='',id='dataset-export-path')
                yield Button('Export saved dataset copy',id='dataset-export')
            yield Button('Review physical photometry (only for actual laboratory readings)',id='dataset-verify')
        yield Footer()

    def on_mount(self):
        from .setup import ReviewScreen
        if isinstance(self.app.screen_stack[-2], ReviewScreen):
            self.query_one('#dataset-accept',Button).label='Accept luminance values → Review'
        self.refresh_data()
        self._update_measurement_controls()

    def on_screen_resume(self):
        if not self.is_mounted: return
        self.app.reload_profiles(); self.profile=self.app.monitor_profiles[self.profile.id]
        if not self._has_unsaved_changes() and not self._has_pending_readings():
            self.saved=load_active(self.app.local_config_root,self.profile)
            self.draft=deepcopy(self.saved)
            for key in ('method','date','notes'): self.query_one('#dataset-'+key,Input).value=self.saved.get(key,'')
        self._physical_changes=physical_snapshot_differences(self.profile,self.saved)
        self.refresh_data()

    def _refresh_chronological_guidance(self):
        changed=self._physical_changes
        self.query_one('#dataset-start-confirm',Checkbox).display=bool(changed) and not self._replacement_started
        self.query_one('#dataset-start-current',Button).display=bool(changed) and not self._replacement_started
        has_saved=bool(self.saved['observations'])
        self.query_one('#dataset-keep-test',Button).disabled=not has_saved
        self.query_one('#dataset-accept',Button).disabled=len(summary(self.draft)) < 2
        self.query_one('#dataset-discard',Button).display=self._has_unsaved_changes() or self._has_pending_readings()
        summary_text=''
        if changed:
            changes='; '.join(
                f"{key.replace('_', ' ')}: saved {old} → current {new}"
                for key,(old,new) in changed.items()
            )
            summary_text=('SAVED DATA ARE FOR AN EARLIER DISPLAY CONFIGURATION.\n'
                          +changes+'\n'
                          'For software tests, keep these values labelled TEST; no new measurements are needed.\n'
                          'For new physical measurements, tick Yes and press Start new measurements. '
                          'Your old records are kept. They are not silently treated as physically verified.')
        else:
            summary_text=('Saved readings match the recorded display configuration. '
                          'Add new readings only when needed; opening this page does not require recalibration.')
        self.query_one('#dataset-replacement-guidance',Static).update(summary_text)
        if self._replacement_started:
            count=len(summary(self.draft))
            if count < 2:
                next_text=(f'STEP 2 OF 3 — {count} / 2 different intensities entered. '
                           'Enter a digital intensity, its cd/m² reading(s), and source; '
                           'click Add readings to draft. Two distinct intensities are '
                           'the minimum for a completed luminance stage. '
                           'You can save partial data, but the stage stays incomplete.')
            else:
                next_text=(f'STEP 3 OF 3 — {count} intensities ready. '
                           'Review the table, then choose Save active dataset (top right). '
                           'Synthetic values remain test-only.')
        elif changed:
            next_text=('STEP 1 OF 3 — Either Keep saved TEST values and return, or tick '
                       'Yes → Start new measurements for THIS display. '
                       'Do not simply press Save on old data.')
        elif self._has_unsaved_changes():
            next_text=('STEP 3 OF 3 — Review the readings then choose Accept luminance values. '
                       'Discard draft / Back keeps the previously saved mapping.')
        else:
            next_text=('Choose Accept luminance values to approve this existing mapping. '
                       'No re-entry is needed. Source labels remain unchanged.' if has_saved else
                       'Enter at least two intensity/cd/m² pairs, Add readings to draft, then Accept luminance values.')
        self.query_one('#dataset-next-step',Static).update(next_text)

    def refresh_data(self):
        state=luminance_state(self.profile,self.saved)
        self.query_one('#dataset-state',Static).update(
            state+'\nSaved values remain available for test presentation and simulation. '
            'Actual photometer measurements must be physically reviewed before human acquisition.')
        self.query_one('#dataset-data-location',Static).update(
            'Local dataset: '+str(active_directory(self.app.local_config_root,self.profile)/'luminance.json'))
        rows=summary(self.draft)
        picker=self.query_one('#dataset-selected',Select)
        previous=picker.value
        options=[('New intensity','new')]+[(f"{r['screen_intensity']:g} — {r['luminance_cdm2']:g} cd/m²",str(r['screen_intensity'])) for r in rows]
        with self.prevent(Select.Changed):
            picker.set_options(options)
            picker.value=previous if previous in [value for _,value in options] else 'new'
        text=('Unsaved draft — saved values unchanged until Save active dataset:\n'
              if self._has_unsaved_changes() else 'Saved values — no unsaved dataset changes:\n')
        text+='Intensity | readings | mean cd/m² | SD cd/m²\n'
        text+='\n'.join(f"{r['screen_intensity']:g} | {r['n'] if r['n'] is not None else 'unknown (legacy summary)'} | {r['luminance_cdm2']:.6g} | "+('not estimated (single observation)' if r['sample_sd_cdm2'] is None else f"{r['sample_sd_cdm2']:.6g}") for r in rows)
        raw='Raw readings by digital command:\n' + '; '.join(
            f"{r['screen_intensity']:g}: {r.get('readings_cdm2','unknown — legacy summary only')}"
            for r in rows)
        if any(r.get('source')=='legacy_summary_only' for r in self.draft['observations']):
            raw+='\nLegacy means have no recorded repetitions. Use Replace after reviewing original source data.'
        self.query_one('#dataset-statistics',Static).update(text)
        self.query_one('#dataset-raw',Static).update(raw)
        self._refresh_chronological_guidance()

    def on_select_changed(self,event):
        if not self.is_mounted:
            return
        if event.select.id=='dataset-selected' and event.value!='new':
            self.query_one('#dataset-command',Input).value=str(event.value)
        if event.select.id=='dataset-task':
            task=event.value
            if task=='correct':
                self.query_one('#dataset-mode',Select).value='replace_selected'
                self.query_one('#dataset-feedback',Static).update(
                    'Choose a saved intensity, load its readings, then confirm replacement. '
                    'Existing measurements stay saved until Save active dataset.')
            elif task=='add':
                self.query_one('#dataset-mode',Select).value='merge'
                self.query_one('#dataset-confirm',Checkbox).value=False
            else:
                self.query_one('#dataset-feedback',Static).update(
                    'Expand Advanced below to import an existing JSON measurement file.')
        self._update_measurement_controls()

    def _parsed_readings(self):
        raw=self.query_one('#dataset-readings',Input).value.strip()
        if not raw:
            raise ValueError('Enter one or more luminance readings (cd/m²), or leave this field empty until ready.')
        values=[value.strip() for value in raw.split(',')]
        if any(not value for value in values):
            raise ValueError('Separate readings with commas; remove empty entries.')
        command=self.query_one('#dataset-command',Input).value.strip()
        if not command:
            raise ValueError('Enter a digital intensity between 0 and 1.')
        try:
            return [observation(command,value,kind=str(self.query_one('#dataset-kind',Select).value))
                    for value in values]
        except ValueError as exc:
            raise ValueError('Use a digital intensity from 0 to 1 and nonnegative finite luminance readings.') from exc

    def _update_measurement_controls(self):
        if not self.is_mounted:
            return
        mode=self.query_one('#dataset-mode',Select).value
        self.query_one('#dataset-confirm',Checkbox).display=mode in ('replace_selected','replace_all')
        # Keep the button actionable even before queued Input.Changed events
        # run: programmatic/TUI rapid entry + immediate click must not get lost.
        # _parsed_readings provides a concise field-specific message for blanks.
        self.query_one('#dataset-add',Button).disabled=False

    def on_input_changed(self,event):
        if not self.is_mounted:
            return
        if event.input.id in ('dataset-method','dataset-date','dataset-notes'):
            self.refresh_data()
            return
        # Optional method, date, notes and JSON paths are not readings.
        # An empty readings field is a normal neutral state, never a float error.
        if event.input.id not in ('dataset-command','dataset-readings'):
            return
        self._update_measurement_controls()
        self._refresh_chronological_guidance()
        command=self.query_one('#dataset-command',Input).value.strip()
        raw=self.query_one('#dataset-readings',Input).value.strip()
        if not command or not raw:
            event.input.remove_class('invalid-input')
            return
        try:
            self._parsed_readings()
        except ValueError as exc:
            event.input.add_class('invalid-input')
            self.query_one('#dataset-feedback',Static).update(str(exc))
            return
        event.input.remove_class('invalid-input')
        self.query_one('#dataset-feedback',Static).update(
            'Readings valid. Select Add readings to draft, then Accept luminance values.')

    def _metadata(self):
        for key in ('method','date','notes'): self.draft[key]=self.query_one('#dataset-'+key,Input).value.strip()
        if self.draft['date']:
            from datetime import date
            date.fromisoformat(self.draft['date'])

    def _has_unsaved_changes(self):
        return self.draft!=self.saved or any(
            self.query_one('#dataset-'+key,Input).value.strip()!=self.saved.get(key,'')
            for key in ('method','date','notes'))

    def _has_pending_readings(self):
        return bool(self.query_one('#dataset-readings',Input).value.strip())

    def _accept_saved(self, *, experiment=False):
        if experiment:
            if not self.saved['observations']:
                raise ValueError('No saved values available for a test presentation.')
            if self._has_unsaved_changes() or self._has_pending_readings():
                raise ValueError('Unsaved edits remain. Add readings and Save, or Discard draft before continuing.')
        else:
            if self._has_pending_readings():
                raise ValueError('Click Add readings to draft, then Accept luminance values.')
            self._metadata()
            self.profile, self.saved = accept_active(
                self.app.local_config_root, self.profile, self.draft,
                expected_version=self.saved['version'], confirmed=True,
            )
            self.draft = deepcopy(self.saved)
            self._replacement_started = False
            self._physical_changes = physical_snapshot_differences(self.profile,self.saved)
            self.app.reload_profiles()
            self.refresh_data()
        from .setup import DisplayCheckScreen, ReviewScreen
        from ..config.local import save_preferences
        parent=self.app.screen_stack[-2]
        if not experiment and not isinstance(parent,ReviewScreen):
            save_preferences(self.app.local_config_root,active_monitor_profile_id=self.profile.id,
                             calibration_active_stage='precision')
        home=self.app.screen_stack[0]
        home.query_one('#monitor-profile',Select).value=self.profile.id
        if experiment:
            home.query_one('#run-intent',Select).value='test'
            self.app.run_intent='test'
            message=('Saved test luminance values retained unchanged for TEST presentation; no physical verification or '
                     'human qualification was recorded.')
            self.app.open_hub_page('setup')
            home.query_one('#setup-status',Static).update(message)
        else:
            message=('Mapping accepted by researcher for this display. Original test/meter source '
                     'labels remain intact; independent physical verification is separate.')
            if isinstance(parent,ReviewScreen):
                self.app.pop_screen()
                parent.query_one('#review-status',Static).update(message)
            elif isinstance(parent,DisplayCheckScreen):
                self.app.pop_screen()
            else:
                self.app.display_guide_target_profile_id=self.profile.id
                self.app.display_draft['geometry-monitor']=self.profile.id
                self.app.switch_screen(DisplayCheckScreen())
            self.app.notify(message,title='Luminance mapping accepted',timeout=8)

    def on_button_pressed(self,event):
        key=event.button.id
        try:
            if key=='dataset-back':
                self.app.pop_screen()
                return
            if key=='dataset-keep-test':
                self._accept_saved(experiment=True)
                return
            if key=='dataset-accept':
                self._accept_saved()
                return
            if key=='dataset-discard':
                self.draft=deepcopy(self.saved)
                self._replacement_started=False
                for field in ('method','date','notes'):
                    self.query_one('#dataset-'+field,Input).value=self.saved.get(field,'')
                self.query_one('#dataset-readings',Input).value=''
                self.refresh_data()
                self.query_one('#dataset-feedback',Static).update(
                    'Draft discarded. Saved values unchanged; choose Accept to approve the mapping.')
                return
            if key=='dataset-start-current':
                confirmed=self.query_one('#dataset-start-confirm',Checkbox).value
                if not self._physical_changes:
                    raise ValueError('Current display already matches the saved data. Use Add or Correct.')
                self.draft=replacement_draft_for_current_display(
                    self.profile,self.saved,confirmed=confirmed
                )
                self._replacement_started=True
                for field in ('method','date','notes'):
                    self.query_one('#dataset-'+field,Input).value=''
                with self.prevent(Select.Changed):
                    self.query_one('#dataset-mode',Select).value='merge'
                    self.query_one('#dataset-task',Select).value='add'
                    self.query_one('#dataset-kind',Select).value='synthetic'
                    self.query_one('#dataset-selected',Select).value='new'
                self.query_one('#dataset-readings',Input).value=''
                self.query_one('#dataset-confirm',Checkbox).value=False
                self.refresh_data()
                self.query_one('#dataset-feedback',Static).update(
                    'New UNSAVED dataset started for this physical display. '
                    'Step 2: enter fresh readings. Old records remain intact until you Save.')
                return
            if key=='dataset-reset':
                self.draft=merge_observations(self.draft,[],mode='replace_all',confirmed=self.query_one('#dataset-confirm',Checkbox).value)
                self.draft['physical_snapshot']=physical_snapshot(self.profile)
                self._replacement_started=self._replacement_started or bool(self._physical_changes)
                for field in ('method','date','notes'): self.query_one('#dataset-'+field,Input).value=''
                self.refresh_data(); self.query_one('#dataset-feedback',Static).update('Empty reset draft prepared. Saved readings remain intact until Save; Discard cancels.'); return
            if key=='dataset-load-readings':
                command=float(self.query_one('#dataset-command',Input).value)
                rows=[r for r in self.draft['observations'] if r['screen_intensity']==command]
                if not rows or any(r.get('source')=='legacy_summary_only' for r in rows): raise ValueError('Raw readings are not known for this selected intensity. Enter actual readings for explicit replacement instead.')
                self.query_one('#dataset-readings',Input).value=','.join(str(r['luminance_cdm2']) for r in rows)
                self.query_one('#dataset-mode',Select).value='replace_selected'
                self.query_one('#dataset-kind',Select).value='synthetic' if any(r['data_kind']=='synthetic' for r in rows) else rows[0]['data_kind']
                return
            if key in ('dataset-add','dataset-import'):
                mode=str(self.query_one('#dataset-mode',Select).value)
                confirmed=self.query_one('#dataset-confirm',Checkbox).value
                if key=='dataset-add':
                    rows=self._parsed_readings()
                    command=rows[0]['screen_intensity']
                else:
                    raw_path=self.query_one('#dataset-import-path',Input).value.strip()
                    if not raw_path:
                        raise ValueError('Select a measurement JSON file before importing.')
                    rows,metadata=import_observations(raw_path,self.profile,self.app.local_config_root)
                    selected=self.query_one('#dataset-command',Input).value.strip()
                    command=float(selected) if selected else None
                self.draft=merge_observations(self.draft,rows,mode=mode,selected_command=command,confirmed=confirmed)
                if mode=='replace_all': self.draft['physical_snapshot']=physical_snapshot(self.profile)
                if key=='dataset-import':
                    for target,source in (('method','calibration_method'),('date','calibration_date'),('notes','calibration_notes')):
                        if metadata[source]: self.query_one('#dataset-'+target,Input).value=metadata[source]
                self.refresh_data()
                self.query_one('#dataset-readings',Input).value=''
                self.query_one('#dataset-feedback',Static).update('Readings added to draft. Review the table, then Save active dataset (or Discard).')
                self._update_measurement_controls()
                return
            if key=='dataset-save':
                if not self._has_unsaved_changes() and not self.saved.get('_needs_recovery'):
                    self.query_one('#dataset-feedback',Static).update(
                        'No changes to save. Choose Accept luminance values to continue.'
                        if not self._physical_changes else
                        'No changes to save. Continue without acceptance, or Tick Yes → Start new measurements.')
                    return
                if self._physical_changes and not self._replacement_started:
                    raise ValueError(
                        'Old readings belong to another display setup. '
                        'Tick Yes → Start new measurements above, or return to TEST mode without saving.'
                    )
                if self._replacement_started and not self.draft['observations']:
                    raise ValueError(
                        'New dataset has no readings yet. Add at least one intensity '
                        'and luminance reading, or Discard to keep the old dataset.'
                    )
                self._metadata()
                previous=self.saved
                self.profile,self.saved=save_active(self.app.local_config_root,self.profile,self.draft,expected_version=self.saved['version'])
                self.draft=deepcopy(self.saved)
                self._replacement_started=False
                self._physical_changes=physical_snapshot_differences(self.profile,self.saved)
                self.app.reload_profiles()
                self.refresh_data()
                self.query_one('#dataset-feedback',Static).update(
                    'No changes to save.' if previous==self.saved
                    else 'Saved for the selected display. Previous readings retained in recovery '
                         'history. Test readings do NOT qualify human acquisition; Accept to approve the mapping.'
                )
                return
            if key=='dataset-verify':
                self._metadata()
                if self.draft!=self.saved: raise ValueError('Save or discard the measurement draft before physical verification.')
                from .calibration_review import PhysicalVerificationScreen
                self.app.push_screen(PhysicalVerificationScreen(self.profile,experiment_id=self.experiment_id,focus_category='calibration_status')); return
            if key=='dataset-export':
                from ..data.session import atomic_write_json
                path=Path(self.query_one('#dataset-export-path',Input).value).expanduser()
                if not path.is_absolute(): raise ValueError('Choose an absolute export file path.')
                if path.exists(): raise ValueError('Export path already exists; choose a new path to preserve that file.')
                from ..config.calibration_templates import FORMAT,VERSION,template_identity
                identity,revision=template_identity(self.profile)
                atomic_write_json(path,{'format':FORMAT,'schema_version':VERSION,'monitor_profile_id':identity,'based_on_revision':revision,
                    'photometer_model_and_method':self.saved['method'],'measurement_date':self.saved['date'],'notes':self.saved['notes'],
                    'data_kind':self.saved.get('data_kind','unspecified'),'physical_snapshot':self.saved['physical_snapshot'],'measurements':summary(self.saved)})
                self.query_one('#dataset-feedback',Static).update('Exported saved measurements; active file unchanged.')
        except (ValueError,OSError,KeyError,TypeError,IndexError) as exc: self.query_one('#dataset-feedback',Static).update(str(exc))
