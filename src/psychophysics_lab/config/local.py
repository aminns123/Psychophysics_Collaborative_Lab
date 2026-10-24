"""Machine-local configuration; reading never creates files or migrates data."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
import warnings
from pathlib import Path
from uuid import uuid4
from ..data.identifiers import validate_path_component
from ..data.session import atomic_write_json
from ..data.locking import file_lock

PRESET_SCHEMA_VERSION = 1

def config_root(repo_root: Path, data_root: Path | None = None) -> Path:
    override=os.environ.get('PSYCOLAB_CONFIG_DIR')
    if not override:
        try:
            override=json.loads((repo_root/'.psycolab_local.json').read_text()).get('config_root')
        except (OSError, ValueError, AttributeError):
            pass
    root=Path(os.path.expandvars(override)).expanduser() if override else repo_root.parent/'local_psychophysics_config'
    if not root.is_absolute(): root=repo_root.parent/root
    root=root.resolve()
    for protected in [repo_root.resolve(), *([data_root.resolve()] if data_root else [])]:
        if root==protected or root.is_relative_to(protected) or protected.is_relative_to(root):
            raise ValueError('Local configuration, source and data folders must be separate.')
    return root

def content_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def preferences(root: Path) -> dict:
    try:
        value=json.loads((root/'preferences.json').read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError): return {}

def save_preferences(root: Path, **updates) -> None:
    with file_lock(root/'preferences.lock'):
        atomic_write_json(root/'preferences.json',preferences(root)|updates)

def save_profile(root: Path, profile, *, expected_revision: int = 0):
    from .monitor import _profile_from_dict
    from .models import photometry_is_test_data
    profile.validate()
    if profile.origin != 'local': raise ValueError('Save an explicitly local profile copy.')
    if profile.id == 'legacy_reference_display': raise ValueError('A local profile cannot use the shared reference ID.')
    directory=(root/'profiles'/validate_path_component(profile.id,label='profile')).resolve()
    if not directory.is_relative_to(root.resolve()): raise ValueError('Profile path escapes local configuration.')
    with file_lock(root/'profiles.lock'):
        existing=sorted(directory.glob('revision_*.json')) if directory.exists() else []
        previous=_profile_from_dict(json.loads(existing[-1].read_text(encoding="utf-8"))) if existing else None
        revision=previous.revision if previous else 0
        if revision!=expected_revision: raise ValueError('Profile changed. Reload before saving another revision.')
        materially_changed=previous is None or replace(profile,revision=previous.revision,profile_uuid=previous.profile_uuid)!=previous
        if photometry_is_test_data(profile) and materially_changed:
            profile=replace(profile,luminance_data_kind='synthetic')
        if previous is not None:
            if materially_changed and photometry_is_test_data(previous) and previous.luminance_calibration==profile.luminance_calibration and previous.luminance_source_hash==profile.luminance_source_hash:
                profile=replace(profile,luminance_data_kind='synthetic')
            geometry_changed = any(getattr(previous, field) != getattr(profile, field) for field in
                ("physical_width_m", "physical_height_m", "viewing_distance_m", "expected_resolution_px"))
            binding_changed = previous.display_binding != profile.display_binding
            timing_changed = previous.refresh_rate_hz != profile.refresh_rate_hz
            luminance_changed = previous.luminance_calibration != profile.luminance_calibration or (
                bool(previous.luminance_source_hash) and previous.luminance_source_hash != profile.luminance_source_hash) or (
                previous.luminance_data_kind != profile.luminance_data_kind and previous.luminance_data_kind != "unspecified") or (
                previous.has_verified_luminance_mapping and previous.calibration_method != profile.calibration_method)
            changes = {}
            if geometry_changed or binding_changed:
                changes["geometry_status"] = "manual_unverified"
            if timing_changed or binding_changed:
                changes["timing_status"] = "manual_unverified"
            if luminance_changed or binding_changed or geometry_changed or timing_changed:
                changes["calibration_status"] = "manual_unverified"
            active=directory/'current'/'luminance.json'
            if active.exists() and profile.calibration_status=='verified':
                recorded=json.loads(active.read_text(encoding='utf-8'))
                from .calibration_dataset import physical_snapshot
                if recorded['physical_snapshot']!=physical_snapshot(profile):
                    changes['calibration_status']='manual_unverified'
                    changes['qualified_experiments']=()
            if geometry_changed or binding_changed or timing_changed or luminance_changed:
                changes["qualified_experiments"] = ()
            profile = replace(profile, **changes)
        if previous is not None:
            normalised = replace(profile, revision=previous.revision, profile_uuid=previous.profile_uuid)
            if normalised == previous:
                current=directory/'current'
                if not (current/'profile.json').exists():
                    atomic_write_json(current/'profile.json',previous.to_dict())
                    for kind,keys in {'geometry':('physical_width_m','physical_height_m','viewing_distance_m','expected_resolution_px','display_binding','geometry_status'),'timing':('refresh_rate_hz','pyglet_wakeup_rate_hz','timing_status')}.items():
                        atomic_write_json(current/(kind+'.json'),{'profile_revision':previous.revision,**{key:previous.to_dict()[key] for key in keys}})
                    atomic_write_json(current/'snapshot.json',{'profile_revision':previous.revision,'profile_sha256':content_hash(previous.to_dict())})
                return previous  # No revision or preference write for a no-op Save.
        active_update=None
        active=directory/'current'/'luminance.json'
        if previous is not None and active.exists() and previous.luminance_source_hash==profile.luminance_source_hash and any(getattr(previous,key)!=getattr(profile,key) for key in ('luminance_calibration','calibration_method','calibration_date','calibration_notes')):
            # Older callers edit mean-only profiles. Keep that supported, but
            # synchronize the active record explicitly as summary-only evidence;
            # earlier raw observations remain in immutable recovery history.
            from .calibration_dataset import load_active,observation,physical_snapshot,dataset_hash,summary
            old=load_active(root,previous)
            mean_edit=previous.luminance_calibration!=profile.luminance_calibration
            kind=('synthetic' if previous.luminance_data_kind=='synthetic' else 'unspecified') if mean_edit else previous.luminance_data_kind
            active_update={**old,'version':old['version']+1,'physical_snapshot':physical_snapshot(profile) if mean_edit else old['physical_snapshot'],
                'observations':[observation(p.screen_intensity,p.luminance_cdm2,kind=kind,source='legacy_summary_only') for p in profile.luminance_calibration] if mean_edit else old['observations'],
                'method':profile.calibration_method,'date':profile.calibration_date,'notes':profile.calibration_notes,'data_kind':kind}
            active_update.pop('_needs_recovery',None)
            active_update['summary']=summary(active_update)
            profile=replace(profile,luminance_source_hash=dataset_hash(active_update),luminance_data_kind=kind,
                calibration_status='manual_unverified' if mean_edit or previous.calibration_method!=profile.calibration_method else profile.calibration_status,
                qualified_experiments=() if mean_edit or previous.calibration_method!=profile.calibration_method else profile.qualified_experiments)
            history=active.parent/'.history'
            atomic_write_json(history/f"luminance_{content_hash(old)}.json",old)
            atomic_write_json(history/f"luminance_{content_hash(active_update)}.json",active_update)
        saved=replace(profile,revision=revision+1,profile_uuid=previous.profile_uuid if previous else str(uuid4()),origin='local')
        atomic_write_json(directory/f'revision_{saved.revision:06d}.json',saved.to_dict())
        if active_update is not None:
            active_update['profile_revision']=saved.revision
            atomic_write_json(active,active_update)
        # Active projections are derived from the immutable committed revision.
        # A manifest-last update identifies a complete snapshot; history is untouched.
        current=directory/'current'
        atomic_write_json(current/'profile.json',saved.to_dict())
        for kind,keys in {'geometry':('physical_width_m','physical_height_m','viewing_distance_m','expected_resolution_px','display_binding','geometry_status'),
                          'timing':('refresh_rate_hz','pyglet_wakeup_rate_hz','timing_status')}.items():
            path=current/(kind+'.json')
            diagnostics=json.loads(path.read_text(encoding='utf-8')).get('diagnostics',{}) if path.exists() else {}
            atomic_write_json(path,{'profile_revision':saved.revision,**{key:saved.to_dict()[key] for key in keys},'diagnostics':diagnostics})
        atomic_write_json(current/'snapshot.json',{'profile_revision':saved.revision,'profile_sha256':content_hash(saved.to_dict())})
        save_preferences(root,active_monitor_profile_id=saved.id)
        return saved

def save_preset(root: Path, name: str, experiment_id: str, values: dict) -> Path:
    name=validate_path_component(name,label='preset')
    exp=validate_path_component(experiment_id,label='experiment')
    path=(root/'presets'/exp/f'{name}.json').resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError('Preset path escapes local configuration.')
    atomic_write_json(path,{'schema_version':PRESET_SCHEMA_VERSION,'experiment_id':exp,'values':values,'saved_utc':datetime.now(timezone.utc).isoformat()})
    return path

def update_preset(root: Path, name: str, experiment_id: str, values: dict) -> Path:
    """Explicitly update one existing preset, retaining its previous JSON.

    Saving a new preset and replacing the currently selected preset are
    distinct UI operations. Every update archives the old document first,
    allowing researchers to recover parameters used previously.
    """
    name = validate_path_component(name, label="preset")
    experiment = validate_path_component(experiment_id, label="experiment")
    base = (root / "presets" / experiment).resolve()
    path = (base / f"{name}.json").resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Preset path escapes local configuration.")
    with file_lock(root / "presets.lock"):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Preset '{name}' does not exist. Use Save new preset.")
        previous = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            raise ValueError("Existing preset must be a JSON object; it was not overwritten.")
        if type(previous.get("schema_version")) is not int or previous["schema_version"] != PRESET_SCHEMA_VERSION:
            raise ValueError(
                f"Preset '{name}' has missing or unsupported schema_version "
                f"{previous.get('schema_version')!r}; it was not overwritten. "
                "Keep the original and save a new preset instead."
            )
        if (previous.get("experiment_id") != experiment
                or not isinstance(previous.get("values"), dict)):
            raise ValueError("Existing preset has unexpected content; it was not overwritten.")
        history_dir = base / ".history"
        history_dir.mkdir(parents=True, exist_ok=True)
        backup = history_dir / f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')}_{uuid4().hex[:8]}.json"
        atomic_write_json(backup, previous)
        atomic_write_json(path, {
            "schema_version": PRESET_SCHEMA_VERSION, "experiment_id": experiment,
            "values": values, "saved_utc": datetime.now(timezone.utc).isoformat(),
        })
    return path


def load_presets(root: Path, experiment_id: str) -> dict[str, dict]:
    result={}
    directory=root/'presets'/validate_path_component(experiment_id,label='experiment')
    for path in sorted(directory.glob('*.json')):
        try:
            value=json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                continue
            version = value.get("schema_version")
            if "schema_version" in value and (
                type(version) is not int or version != PRESET_SCHEMA_VERSION
            ):
                warnings.warn(
                    f"Ignoring preset '{path.name}': unsupported schema_version {version!r}. "
                    "The original file was left unchanged.",
                    RuntimeWarning, stacklevel=2,
                )
                continue
            if value.get('experiment_id')==experiment_id and isinstance(value.get('values'), dict):
                if "schema_version" not in value:
                    warnings.warn(
                        f"Preset '{path.name}' has no schema_version (legacy unversioned). "
                        "Review scientific parameter meanings before using; the file remains unchanged.",
                        RuntimeWarning, stacklevel=2,
                    )
                result[path.stem]=value['values']
        except (OSError,ValueError,KeyError,AttributeError): pass
    return result
