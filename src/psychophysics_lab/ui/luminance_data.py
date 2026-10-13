"""Focused active luminance editor: draft/preview first, explicit atomic Save."""
from copy import deepcopy
from pathlib import Path
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Header, Footer, Button, Input, Select, Checkbox, Static, Label
from ..config.calibration_dataset import (load_active,save_active,observation,summary,merge_observations,
    import_observations,luminance_state,physical_snapshot,active_directory)


class LuminanceDataScreen(Screen):
    def __init__(self,profile,*,experiment_id=None):
        super().__init__(); self.profile=profile; self.experiment_id=experiment_id

    def compose(self):
        self.saved=load_active(self.app.local_config_root,self.profile); self.draft=deepcopy(self.saved)
        with Vertical(id='fixed-shell'):
            yield Header()
            with Horizontal(classes='buttons'):
                yield Button('Discard draft / Back',id='dataset-back')
                yield Button('Save active dataset',id='dataset-save',variant='primary')
            yield Static('',id='dataset-feedback',markup=False)
        with VerticalScroll(classes='page-body'):
            yield Static('',id='dataset-state',markup=False)
            yield Static('',id='dataset-statistics',markup=False)
            yield Label('Edit mode — earlier readings are retained unless replacement is confirmed')
            yield Select([('Continue / add repetitions','merge'),('Add a new intensity','append'),('Replace selected intensity readings','replace_selected'),('Replace whole dataset / Reset','replace_all')],value='merge',allow_blank=False,id='dataset-mode')
            yield Label('Existing intensity to inspect/edit (New keeps manual command entry)')
            yield Select([('New intensity','new')]+[(f"{r['screen_intensity']:g} — {r['luminance_cdm2']:g} cd/m²",str(r['screen_intensity'])) for r in summary(self.draft)],value='new',allow_blank=False,id='dataset-selected')
            yield Button('Load selected raw readings for correction',id='dataset-load-readings')
            yield Label('Intensity command: allowed range 0–1, finite')
            yield Input(value='0.5',id='dataset-command')
            yield Label('Individual readings (comma separated cd/m², finite ≥ 0; means/SD calculated)')
            yield Input(value='',id='dataset-readings')
            yield Select([('Unspecified provenance — unverified','unspecified'),('Actual instrument observations — requires independent verification','genuine'),('Synthetic pilot / UI test values','synthetic')],value='unspecified',allow_blank=False,id='dataset-kind')
            yield Checkbox('I confirm replacement/reset; earlier saved data will remain in recovery history.',id='dataset-confirm')
            yield Button('Apply readings to unsaved draft',id='dataset-add')
            yield Button('Reset to empty draft (confirmation required)',id='dataset-reset')
            yield Label('Instrument / method (optional to save; required for physical verification)')
            yield Input(value=self.draft['method'],id='dataset-method')
            yield Label('Optional date (YYYY-MM-DD) and notes')
            yield Input(value=self.draft.get('date',''),id='dataset-date')
            yield Input(value=self.draft.get('notes',''),id='dataset-notes')
            yield Label('Earlier measurement JSON: select an edit mode, then preview import')
            yield Input(value='',id='dataset-import-path')
            yield Button('Preview import into draft',id='dataset-import')
            yield Label('Export copy path — only written when explicitly requested')
            yield Input(value='',id='dataset-export-path')
            yield Button('Export saved dataset copy',id='dataset-export')
            yield Button('Review physical photometry',id='dataset-verify')
        yield Footer()

    def on_mount(self): self.refresh_data()

    def on_screen_resume(self):
        if not self.is_mounted: return
        self.app.reload_profiles(); self.profile=self.app.monitor_profiles[self.profile.id]
        if self.draft==self.saved:
            self.saved=load_active(self.app.local_config_root,self.profile)
            self.draft=deepcopy(self.saved)
            for key in ('method','date','notes'): self.query_one('#dataset-'+key,Input).value=self.saved.get(key,'')
        self.refresh_data()

    def refresh_data(self):
        self.query_one('#dataset-state',Static).update(luminance_state(self.profile,self.saved)+'\nActive file: '+str(active_directory(self.app.local_config_root,self.profile)/'luminance.json')+'\nTest data are permitted for simulation and uncalibrated presentation, never physical certification. Replace readings explicitly with actual observations; metadata alone cannot convert synthetic readings.')
        rows=summary(self.draft)
        text='Draft measurements (not saved until Save):\nIntensity | n | mean cd/m² | sample SD cd/m²\n'
        text+='\n'.join(f"{r['screen_intensity']:g} | {r['n'] if r['n'] is not None else 'unknown (legacy summary)'} | {r['luminance_cdm2']:.6g} | "+('not estimated (single observation)' if r['sample_sd_cdm2'] is None else f"{r['sample_sd_cdm2']:.6g}") for r in rows)
        text+='\nRaw readings: '+ '; '.join(f"{r['screen_intensity']:g}: {r.get('readings_cdm2','unknown — legacy summary only')}" for r in rows)
        if any(r.get('source')=='legacy_summary_only' for r in self.draft['observations']): text+='\nLegacy means are labelled summary-only; raw repetitions were not present in the profile. Import original raw files to replace these summaries.'
        self.query_one('#dataset-statistics',Static).update(text)

    def on_select_changed(self,event):
        if event.select.id=='dataset-selected' and event.value!='new' and self.is_mounted:
            self.query_one('#dataset-command',Input).value=str(event.value)

    def on_input_changed(self,event):
        if not self.is_mounted: return
        try:
            observation(self.query_one('#dataset-command',Input).value,0)
            raw=self.query_one('#dataset-readings',Input).value.strip()
            if raw:
                for value in raw.split(','): observation(0,value)
            self.query_one('#dataset-feedback',Static).update('Allowed: intensity 0–1; readings finite ≥ 0. Values are retained for correction; nothing saved yet.')
            # The Apply handler revalidates every reading before changing the draft.
        except ValueError as exc:
            event.input.add_class('invalid-input'); self.query_one('#dataset-feedback',Static).update(str(exc))
            return
        event.input.remove_class('invalid-input')

    def _metadata(self):
        for key in ('method','date','notes'): self.draft[key]=self.query_one('#dataset-'+key,Input).value.strip()
        if self.draft['date']:
            from datetime import date
            date.fromisoformat(self.draft['date'])

    def on_button_pressed(self,event):
        key=event.button.id
        try:
            if key=='dataset-back': self.app.pop_screen(); return
            if key=='dataset-reset':
                self.draft=merge_observations(self.draft,[],mode='replace_all',confirmed=self.query_one('#dataset-confirm',Checkbox).value)
                self.draft['physical_snapshot']=physical_snapshot(self.profile)
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
                command=float(self.query_one('#dataset-command',Input).value)
                if key=='dataset-add':
                    rows=[observation(command,v,kind=str(self.query_one('#dataset-kind',Select).value)) for v in self.query_one('#dataset-readings',Input).value.split(',')]
                else:
                    rows,metadata=import_observations(self.query_one('#dataset-import-path',Input).value,self.profile,self.app.local_config_root)
                self.draft=merge_observations(self.draft,rows,mode=mode,selected_command=command,confirmed=confirmed)
                if mode=='replace_all': self.draft['physical_snapshot']=physical_snapshot(self.profile)
                if key=='dataset-import':
                    for target,source in (('method','calibration_method'),('date','calibration_date'),('notes','calibration_notes')):
                        if metadata[source]: self.query_one('#dataset-'+target,Input).value=metadata[source]
                self.refresh_data(); self.query_one('#dataset-feedback',Static).update('Preview applied to draft. Review statistics and provenance, then Save or Discard.'); return
            if key=='dataset-save':
                self._metadata()
                previous=self.saved
                self.profile,self.saved=save_active(self.app.local_config_root,self.profile,self.draft,expected_version=self.saved['version'])
                self.draft=deepcopy(self.saved); self.app.reload_profiles(); self.refresh_data()
                self.query_one('#dataset-feedback',Static).update('No changes to save.' if previous==self.saved else 'Active dataset saved. Changed observations require fresh laboratory verification and experiment qualification.'); return
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
