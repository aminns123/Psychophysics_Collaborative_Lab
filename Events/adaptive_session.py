"""Legacy CSF file/event adapter; not a universal experiment interface.

Pure staircase mechanics live in staircase.py. This adapter owns the existing
CSF correctness mapping and files until the broader experiment API is migrated.
"""

import json
import os
from pathlib import Path

from Events.adaptiveMethods import record_event
from Events.staircase import AdaptiveRun, StaircaseConfig
import Functions.functionsForUse as funcs


class LegacyStaircaseSession:
    def __init__(self, conditions_path, parameters_path, response_path, max_trials):
        conditions = funcs.read_JSON(conditions_path)
        self.parameters = funcs.read_JSON(parameters_path)
        self.metadata_path = Path(response_path).with_suffix('.session.json')
        self.conditions_path = conditions_path
        self.run = AdaptiveRun({
            identity: StaircaseConfig(
                n_down=self.parameters['n_dw'],
                n_up=self.parameters['n_up'],
                reversal_limit=conditions['reversal_termination'][identity])
            for identity in conditions['staircase_Identities']
        }, max_trials)
        self.save()

    def attach(self, trial):
        trial.adaptive_run = self.run
        return trial

    def save(self, status=None, error=None):
        metadata = self.run.snapshot()
        metadata.update({
            'schema_version': 1,
            'legacy_parameters': self.parameters,
            'reversal_basis': 'recorded_post_update_screen_intensity; flats ignored; no placeholder row',
        })
        if status is not None:
            metadata['status'] = status
        if error is not None:
            metadata['error'] = str(error)
        temporary = self.metadata_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(metadata, indent=4), encoding='utf-8')
        os.replace(temporary, self.metadata_path)

    def logger(self, window):
        def log(event, time, trial, args):
            previous_count = self.run.total_trials
            try:
                record_event(event, time, trial, args)
                if self.run.total_trials != previous_count:
                    self.save()
                    if self.run.status != 'running':
                        window.trials.clear()
                        window.exit()
            except Exception as exc:
                # The legacy engine catches logger errors and otherwise advances.
                # Stop this experiment instead of continuing with partial state.
                try:
                    self.save(status='error', error=exc)
                finally:
                    window.trials.clear()
                    window.exit()
                raise
        return log

    def finish(self):
        # Preserve an error recorded by the logger. Escape/close is not success.
        if self.metadata_path.exists():
            if json.loads(self.metadata_path.read_text(encoding='utf-8'))['status'] == 'error':
                return
        self.save(status='aborted' if self.run.status == 'running' else self.run.status)
