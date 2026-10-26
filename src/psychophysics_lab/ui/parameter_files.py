"""External editable copies of the existing parameter JSON formats."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from ..data.session import atomic_write_json
from ..data.identifiers import validate_path_component


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def working_path(root, experiment_id, slot=None):
    directory = Path(root)/"parameter_files"/validate_path_component(experiment_id, label="experiment")
    return directory / ((validate_path_component(slot, label="slot") if slot else "experiment") + ".json")


def parameter_info(fields, controlled=()):
    return {f.key: {"label":f.label, "units":f.units,
                   "source":"controlled by experiment each trial" if f.key in controlled else "editable parameter",
                   "help":f.help_text} for f in fields}


def ensure_json(path, document):
    """Create once; opening an editor never overwrites a user's existing file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except FileExistsError:
        pass
    return path


def replace_reviewed_json(path, document, expected_hash):
    """Save TUI edits only over the version just reviewed; retain original bytes."""
    path = Path(path)
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != expected_hash:
        raise ValueError("JSON changed in the editor. Reload saved JSON before Review; your file was not overwritten.")
    if json.loads(original.decode("utf-8-sig")) != document:
        history = path.parent/".history"
        history.mkdir(parents=True, exist_ok=True)
        backup = history/(path.stem+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"_"+uuid4().hex[:8]+".json")
        backup.write_bytes(original)
        atomic_write_json(path, document)
    return file_hash(path)


def load_experiment_json(path, spec):
    document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if (not isinstance(document, dict) or document.get("schema_version") != 1
            or document.get("experiment_id") != spec.id or not isinstance(document.get("values"), dict)):
        raise ValueError("Experiment JSON needs schema_version=1, the selected experiment_id and a values object.")
    if set(document) - {"schema_version", "experiment_id", "values", "parameter_info", "saved_utc"}:
        raise ValueError("Unknown experiment JSON section; edit the values object.")
    values = spec.normalise_input_keys(document["values"])
    # Explicit additive compatibility uses the declared historic default, not
    # the current saved preset. Missing original/unknown fields still fail.
    for field in spec.fields:
        if field.allow_legacy_default and field.key not in values:
            values[field.key] = field.default
    if set(values) != {f.key for f in spec.fields}:
        raise ValueError("Experiment JSON must list every declared experiment parameter, with no unknown keys.")
    return spec.normalise_values(values, use_config=False)


def ensure_unchanged(files):
    for path, expected in files.items():
        try:
            if file_hash(path) == expected:
                continue
        except OSError:
            pass
        raise ValueError(f"{Path(path).name} changed or disappeared. Go back, reload the JSON and Review again.")
