"""Machine-local configuration; reading never creates files or migrates data."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from ..data.identifiers import validate_path_component
from ..data.session import atomic_write_json
from ..data.locking import file_lock

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
        if previous is not None:
            geometry_changed = any(getattr(previous, field) != getattr(profile, field) for field in
                ("physical_width_m", "physical_height_m", "viewing_distance_m", "expected_resolution_px"))
            binding_changed = previous.display_binding != profile.display_binding
            timing_changed = previous.refresh_rate_hz != profile.refresh_rate_hz
            luminance_changed = previous.luminance_calibration != profile.luminance_calibration
            changes = {}
            if geometry_changed or binding_changed:
                changes["geometry_status"] = "manual_unverified"
            if timing_changed or binding_changed:
                changes["timing_status"] = "manual_unverified"
            if luminance_changed or binding_changed:
                changes["calibration_status"] = "manual_unverified"
            if geometry_changed or binding_changed or timing_changed or luminance_changed:
                changes["qualified_experiments"] = ()
            profile = replace(profile, **changes)
        saved=replace(profile,revision=revision+1,profile_uuid=previous.profile_uuid if previous else str(uuid4()),origin='local')
        atomic_write_json(directory/f'revision_{saved.revision:06d}.json',saved.to_dict())
        save_preferences(root,active_monitor_profile_id=saved.id)
        return saved

def save_preset(root: Path, name: str, experiment_id: str, values: dict) -> Path:
    name=validate_path_component(name,label='preset')
    exp=validate_path_component(experiment_id,label='experiment')
    path=(root/'presets'/exp/f'{name}.json').resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError('Preset path escapes local configuration.')
    atomic_write_json(path,{'schema_version':1,'experiment_id':exp,'values':values,'saved_utc':datetime.now(timezone.utc).isoformat()})
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
        if (previous.get("experiment_id") != experiment
                or not isinstance(previous.get("values"), dict)):
            raise ValueError("Existing preset has unexpected content; it was not overwritten.")
        history_dir = base / ".history"
        history_dir.mkdir(parents=True, exist_ok=True)
        backup = history_dir / f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')}_{uuid4().hex[:8]}.json"
        atomic_write_json(backup, previous)
        atomic_write_json(path, {
            "schema_version": 1, "experiment_id": experiment,
            "values": values, "saved_utc": datetime.now(timezone.utc).isoformat(),
        })
    return path


def load_presets(root: Path, experiment_id: str) -> dict[str, dict]:
    result={}
    directory=root/'presets'/validate_path_component(experiment_id,label='experiment')
    for path in sorted(directory.glob('*.json')):
        try:
            value=json.loads(path.read_text())
            if value.get('experiment_id')==experiment_id and isinstance(value.get('values'), dict):
                result[path.stem]=value['values']
        except (OSError,ValueError,KeyError,AttributeError): pass
    return result
