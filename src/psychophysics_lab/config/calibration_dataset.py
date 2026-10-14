"""One active raw dataset per display, with optimistic locking and recovery history.

Profile revisions remain the acquisition authority. Dataset history is written
before the profile commit; a failed final active write is recoverable on Save.
Reading/migration preview never writes or deletes historical records.
"""
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
from uuid import uuid4
from .local import content_hash, save_profile
from .models import LuminanceCalibrationPoint, photometry_is_test_data
from .readiness import _DIAGNOSTIC_PHYSICAL_FIELDS
from ..data.identifiers import validate_path_component
from ..data.locking import file_lock
from ..data.session import atomic_write_json


def active_directory(root, profile):
    path=(Path(root)/'profiles'/validate_path_component(profile.id,label='profile')/'current').resolve()
    if not path.is_relative_to(Path(root).resolve()): raise ValueError('Active calibration path escapes the local configuration root.')
    return path


def physical_snapshot(profile):
    return {key:profile.to_dict()[key] for key in (*_DIAGNOSTIC_PHYSICAL_FIELDS,'profile_uuid','id')}



def physical_snapshot_differences(profile, dataset):
    """Explain incompatible measurement geometry without modifying old evidence.

    Only differences in the established physical snapshot are reported.
    Metadata-only revisions intentionally do not enter the comparison.
    """
    current = physical_snapshot(profile)
    saved = dataset.get('physical_snapshot')
    if not isinstance(saved, dict):
        return {'physical_snapshot': (saved, current)}
    return {key: (saved.get(key), value)
            for key, value in current.items() if saved.get(key) != value}


def observation(command, reading, *, kind='unspecified', source='manual', identifier=None, recorded_utc=None):
    if isinstance(command,bool) or isinstance(reading,bool): raise ValueError('Measurements must be numbers, not booleans.')
    point=LuminanceCalibrationPoint(float(command),float(reading)); point.validate()
    if kind not in ('genuine','synthetic','unspecified'): raise ValueError('Choose genuine, synthetic or unspecified provenance.')
    return {'observation_id':identifier or str(uuid4()),'screen_intensity':point.screen_intensity,
        'luminance_cdm2':point.luminance_cdm2,'data_kind':kind,'source':source,'recorded_utc':recorded_utc}


def summary(dataset):
    from ..core.luminance_session import summarise_readings
    rows=summarise_readings(dataset['observations'])
    for row in rows:
        raw=[r for r in dataset['observations'] if r['screen_intensity']==row['screen_intensity']]
        row['observation_ids']=[r['observation_id'] for r in raw]
        row['reading_data_kinds']=[r['data_kind'] for r in raw]
        row['reading_recorded_utc']=[r.get('recorded_utc') for r in raw]
        if all(r.get('source')=='legacy_summary_only' for r in raw):
            row['summary_only']=True; row['n']=None; row['sample_sd_cdm2']=None; row.pop('readings_cdm2',None)
    return rows


def dataset_hash(dataset):
    return content_hash({key:dataset[key] for key in ('observations','method','physical_snapshot')})


def load_active(root, profile):
    path=active_directory(root,profile)/'luminance.json'
    if path.exists():
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('monitor_profile_id')!=profile.id or data.get('schema_version')!=1:
            raise ValueError('Active luminance identity/schema is invalid; saved file was not changed.')
        if profile.luminance_source_hash and dataset_hash(data)!=profile.luminance_source_hash:
            for backup in sorted((path.parent/'.history').glob('luminance_*.json')):
                recovery=json.loads(backup.read_text(encoding='utf-8'))
                if recovery.get('monitor_profile_id')==profile.id and dataset_hash(recovery)==profile.luminance_source_hash:
                    recovery['_needs_recovery']=True
                    return recovery
            raise ValueError('Active raw measurements do not match the committed profile. Inspect recovery history; no data were changed.')
        return data
    if profile.luminance_source_hash:
        for backup in sorted((path.parent/'.history').glob('luminance_*.json')):
            recovery=json.loads(backup.read_text(encoding='utf-8'))
            if recovery.get('monitor_profile_id')==profile.id and dataset_hash(recovery)==profile.luminance_source_hash:
                recovery['_needs_recovery']=True
                return recovery
        raise ValueError('Committed raw calibration is missing; inspect recovery history before editing.')
    kind='synthetic' if photometry_is_test_data(profile) else 'unspecified'
    rows=[observation(p.screen_intensity,p.luminance_cdm2,kind=kind,source='legacy_summary_only',
        identifier=content_hash({'profile':profile.id,'command':p.screen_intensity,'legacy_mean':p.luminance_cdm2})) for p in profile.luminance_calibration]
    return {'schema_version':1,'monitor_profile_id':profile.id,'physical_snapshot':physical_snapshot(profile),
        'version':0,'observations':rows,'method':profile.calibration_method,'date':profile.calibration_date,
        'notes':profile.calibration_notes,'migration_notice':'Legacy mapping means retained as summary-only observations; earlier raw files remain intact. No repetitions were invented.'}


def merge_observations(dataset, rows, *, mode='merge', selected_command=None, confirmed=False):
    if mode not in ('append','merge','replace_selected','replace_all'): raise ValueError('Unknown measurement edit mode.')
    result=deepcopy(dataset)
    if mode.startswith('replace'):
        if not confirmed: raise ValueError('Confirm replacement; the previous dataset will remain recoverable.')
        if mode=='replace_all': result['observations']=[]
        else:
            if selected_command is None or not any(r['screen_intensity']==float(selected_command) for r in result['observations']): raise ValueError('Select an existing intensity to replace, or choose Add a new intensity.')
            if any(float(r['screen_intensity'])!=float(selected_command) for r in rows): raise ValueError('Replacement observations must belong to the selected intensity.')
            result['observations']=[r for r in result['observations'] if float(r['screen_intensity'])!=float(selected_command)]
    if mode=='append' and set(r['screen_intensity'] for r in rows)&set(r['screen_intensity'] for r in result['observations']):
        raise ValueError('This intensity already exists. Choose merge/add repetitions to retain earlier readings.')
    by_id={r['observation_id']:r for r in result['observations']}
    if mode in ('merge','append'):
        unknown_commands={r['screen_intensity'] for r in result['observations'] if r.get('source')=='legacy_summary_only'}
        if any(r['screen_intensity'] in unknown_commands and r['observation_id'] not in by_id for r in rows):
            raise ValueError('Legacy means have unknown repetition counts. Replace the selected summary with original raw readings before adding repetitions; the earlier summary remains recoverable.')
    for row in rows:
        checked=observation(row['screen_intensity'],row['luminance_cdm2'],kind=row.get('data_kind','unspecified'),
            source=row.get('source','import'),identifier=row['observation_id'],recorded_utc=row.get('recorded_utc'))
        if checked['observation_id'] in by_id:
            if any(checked[k]!=by_id[checked['observation_id']][k] for k in ('screen_intensity','luminance_cdm2','data_kind')): raise ValueError('Observation identity has conflicting content; choose explicit replacement.')
        else: result['observations'].append(checked); by_id[checked['observation_id']]=checked
    return result


def import_observations(path, profile, root):
    from .calibration_templates import read_luminance_measurements,parse_luminance_measurements,FORMAT,VERSION,MAX_IMPORT_BYTES
    target=Path(str(path).strip().strip('"')).expanduser()
    if not target.is_file() or target.stat().st_size>MAX_IMPORT_BYTES: raise ValueError('Choose a measurement JSON file of at most 128 KiB.')
    raw=json.loads(target.read_text(encoding='utf-8'))
    if not isinstance(raw,dict): raise ValueError('Measurement JSON must contain an object.')
    if raw.get('kind')=='physical_luminance_measurement_session':
        from .monitor import _profile_from_dict
        source=_profile_from_dict(raw['monitor_profile'])
        from .calibration_templates import template_identity
        if raw.get('monitor_profile_sha256')!=content_hash(raw['monitor_profile']) or profile.id not in (source.id,template_identity(source)[0]):
            raise ValueError('Raw session identity/snapshot is invalid for this display.')
        if any(source.to_dict()[key]!=profile.to_dict()[key] for key in _DIAGNOSTIC_PHYSICAL_FIELDS):
            raise ValueError('Raw session belongs to another physical display configuration.')
        observations=[]
        for i,row in enumerate(raw['readings']):
            observations.append(observation(row['screen_intensity'],row['luminance_cdm2'],kind='synthetic' if photometry_is_test_data(source) else row.get('data_kind','unspecified'),
                source='raw_session',identifier=row.get('observation_id') or content_hash({'session':raw['session_uuid'],'index':i,'reading':row}),recorded_utc=row.get('recorded_utc')))
        raw={'format':FORMAT,'schema_version':VERSION,'monitor_profile_id':profile.id,'based_on_revision':profile.revision,
            'photometer_model_and_method':source.calibration_method,'measurement_date':source.calibration_date,'notes':source.calibration_notes,
            'data_kind':'synthetic' if photometry_is_test_data(source) else 'unspecified','measurements':summary({'observations':observations}),
            'source_luminance_session_uuid':raw['session_uuid']}
        draft=parse_luminance_measurements(raw,profile,local_config_root=root,allow_partial=True)
    else:
        # Existing revision/physical compatibility and monotonicity remain authoritative.
        draft=read_luminance_measurements(str(target),profile,local_config_root=root,allow_partial=True)
    if 'physical_snapshot' in raw and raw['physical_snapshot']!=physical_snapshot(profile):
        raise ValueError('Imported raw dataset belongs to an earlier/different physical display configuration.')
    method=draft['calibration_method']
    kind='synthetic' if any(x in method.lower() for x in ('fake','demo','synthetic','simulated')) or raw.get('data_kind')=='synthetic' else 'unspecified'
    rows=[]
    for row in raw['measurements']:
        if row.get('luminance_cdm2') is None: continue
        samples=row.get('readings_cdm2', [row['luminance_cdm2']])
        for array in ('observation_ids','reading_data_kinds','reading_recorded_utc'):
            if array in row and (not isinstance(row[array],list) or len(row[array])!=len(samples)):
                raise ValueError('Raw observation metadata arrays must match the reading count.')
        if not isinstance(samples,list) or not samples: raise ValueError('Raw readings must be a nonempty list.')
        checked=[observation(row['screen_intensity'],v,kind=kind,source='legacy_summary_only' if row.get('summary_only') or 'readings_cdm2' not in row else 'import') for v in samples]
        import statistics
        if not math.isclose(statistics.fmean(r['luminance_cdm2'] for r in checked),float(row['luminance_cdm2']),rel_tol=1e-8,abs_tol=1e-8):
            raise ValueError('Imported mean contradicts raw readings; correct the source file before importing.')
        occurrences={}
        for i, r in enumerate(checked):
            r['observation_id']=row.get('observation_ids',[None]*len(samples))[i] or content_hash({'source_session':raw.get('source_luminance_session_uuid','legacy_import'),
                'command':r['screen_intensity'],'value':r['luminance_cdm2'],'occurrence':occurrences.get(r['luminance_cdm2'],0)})
            occurrences[r['luminance_cdm2']]=occurrences.get(r['luminance_cdm2'],0)+1
            r['data_kind']='synthetic' if kind=='synthetic' else row.get('reading_data_kinds',[kind]*len(samples))[i]
            r['recorded_utc']=row.get('reading_recorded_utc',[None]*len(samples))[i]
            rows.append(r)
    if any(not isinstance(r['observation_id'],str) or not r['observation_id'] for r in rows): raise ValueError('Invalid observation identifier.')
    return rows, draft


def save_active(root, profile, dataset, *, expected_version):
    if profile.origin!='local': raise ValueError('Save a local display copy before editing its active calibration.')
    directory=active_directory(root,profile)
    with file_lock(Path(root)/'calibration_datasets.lock'):
        existing=load_active(root,profile)
        if existing['version']!=expected_version: raise ValueError('Calibration dataset changed. Reload before saving.')
        if dataset['monitor_profile_id']!=profile.id or dataset['physical_snapshot']!=physical_snapshot(profile):
            raise ValueError('Physical display configuration changed. Start an explicitly confirmed replacement dataset for this configuration.')
        data=deepcopy(dataset)
        recovery=data.pop('_needs_recovery',False)
        if len({r['observation_id'] for r in data['observations']})!=len(data['observations']): raise ValueError('Duplicate observation identifiers.')
        for r in data['observations']: observation(r['screen_intensity'],r['luminance_cdm2'],kind=r['data_kind'])
        if any(marker in data['method'].lower() for marker in ('fake','demo','synthetic','simulated')):
            for row in data['observations']: row['data_kind']='synthetic'
        summaries=summary(data)
        points=tuple(LuminanceCalibrationPoint(r['screen_intensity'],r['luminance_cdm2']) for r in summaries)
        kind='synthetic' if any(r['data_kind']=='synthetic' for r in data['observations']) else 'genuine' if data['observations'] and all(r['data_kind']=='genuine' for r in data['observations']) else 'unspecified'
        changed_measurements=dataset_hash(existing)!=dataset_hash(data)
        legacy_equivalent = all(r.get('source')=='legacy_summary_only' for r in existing['observations']) and all(r.get('source')=='legacy_summary_only' for r in data['observations']) and (
            [(r['screen_intensity'],r['luminance_cdm2'],r['data_kind']) for r in existing['observations']]==
            [(r['screen_intensity'],r['luminance_cdm2'],r['data_kind']) for r in data['observations']]) and existing['method']==data['method']
        if legacy_equivalent: changed_measurements=False
        candidate=replace(profile,luminance_calibration=points,calibration_method=data['method'].strip(),
            calibration_date=data.get('date',''),calibration_notes=data.get('notes',''),luminance_data_kind=kind,
            luminance_source_hash=dataset_hash(data) if changed_measurements or profile.luminance_source_hash else '',calibration_status='manual_unverified' if changed_measurements else profile.calibration_status,
            qualified_experiments=() if changed_measurements else profile.qualified_experiments)
        candidate.validate()
        # Reusing an existing active document is a true no-op, including its mtime.
        same=all(data.get(k)==existing.get(k) for k in ('observations','method','date','notes','physical_snapshot'))
        if same and ((directory/'luminance.json').exists() or recovery):
            saved=save_profile(root,candidate,expected_revision=profile.revision)
            if recovery:
                data['profile_revision']=saved.revision
                atomic_write_json(directory/'luminance.json',data)
                return saved,data
            return saved, existing
        data['version']=expected_version+1; data['summary']=summaries; data['data_kind']=kind
        history=directory/'.history'
        if (directory/'luminance.json').exists(): atomic_write_json(history/f"luminance_{content_hash(existing)}.json",existing)
        # Recovery copy is durable before committing the matching profile revision.
        atomic_write_json(history/f"luminance_{content_hash(data)}.json",data)
        saved=save_profile(root,candidate,expected_revision=profile.revision)
        data['profile_revision']=saved.revision
        atomic_write_json(directory/'luminance.json',data)
        return saved,data


def luminance_state(profile, dataset=None):
    if dataset is not None and (dataset['physical_snapshot']!=physical_snapshot(profile) or [(r['screen_intensity'],r['luminance_cdm2']) for r in summary(dataset)]!=[(p.screen_intensity,p.luminance_cdm2) for p in sorted(profile.luminance_calibration,key=lambda p:p.screen_intensity)]): return 'INVALIDATED — physical display configuration changed'
    if not profile.luminance_calibration: return 'No luminance measurements saved'
    if photometry_is_test_data(profile): return 'TEST DATA — NOT PHYSICALLY VERIFIED'
    if profile.has_verified_luminance_mapping: return 'Genuine measurements explicitly verified (laboratory declaration)'
    if profile.calibration_method.strip(): return 'Measurements saved — awaiting independent laboratory verification'
    return 'Measurements entered and saved — provenance/verification outstanding'
