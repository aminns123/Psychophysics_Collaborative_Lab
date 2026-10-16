"""JSON values validated by registered stimulus declarations, with portable snapshots."""
import hashlib
import json
from pathlib import Path
from ..stimuli.registry import get_stimulus
from ..data.identifiers import validate_path_component


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_document(document, stimulus):
    if not isinstance(document, dict) or set(document) != {"schema_version", "stimulus_id", "parameters"}:
        raise ValueError("Stimulus JSON needs exactly schema_version, stimulus_id and parameters.")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("Unsupported stimulus JSON schema_version; use 1.")
    if document["stimulus_id"] != stimulus.id:
        raise ValueError(f"Selected stimulus is {stimulus.id}; JSON identifies {document['stimulus_id']}.")
    return {**document, "parameters": stimulus.validate_parameters(document["parameters"])}


def document_for(stimulus, parameters=None):
    return validate_document({"schema_version": 1, "stimulus_id": stimulus.id,
        "parameters": parameters if parameters is not None else {f.key: f.default for f in stimulus.parameters}}, stimulus)


def snapshot(document, *, file_identity, file_sha256=None):
    result = {"document": document, "file_identity": file_identity,
              "file_sha256": file_sha256, "resolved_sha256": digest(document)}
    return result


def load_parameters(path, stimulus):
    path = Path(path)
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Cannot load stimulus JSON {path.name}: {exc}") from exc
    document = validate_document(document, stimulus)
    return snapshot(document, file_identity=path.name, file_sha256=hashlib.sha256(raw).hexdigest())


def save_parameter_preset(root, name, stimulus, document):
    validate_path_component(name, label="stimulus preset")
    document = validate_document(document, stimulus)
    directory = Path(root) / "stimulus_presets" / stimulus.id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return path


def resolve_stimuli(spec, values, snapshots=None, *, repo_root=None):
    """Resolve each independent slot. Old CSF values remain authoritative on legacy calls."""
    snapshots = snapshots or {}
    if set(snapshots) - set(spec.stimulus_slots):
        raise ValueError("Stimulus configuration contains an unknown experiment slot.")
    result = {}
    for slot, family in spec.stimulus_slots.items():
        selected = snapshots.get(slot)
        identity = selected["document"]["stimulus_id"] if selected else spec.stimulus_defaults[slot]
        stimulus = get_stimulus(identity)
        if stimulus.family != family:
            raise ValueError(f"{slot}: stimulus {identity} is incompatible with {family}.")
        if selected:
            document = validate_document(selected["document"], stimulus)
            if digest(document) != selected.get("resolved_sha256"):
                raise ValueError(f"{slot}: stimulus snapshot changed; reload and validate its JSON.")
            # File identity is portable metadata, never an absolute source path.
            if Path(selected["file_identity"]).name != selected["file_identity"] or "/" in selected["file_identity"] or "\\" in selected["file_identity"]:
                raise ValueError("Stimulus file identity must be a filename, not a path.")
        elif spec.stimulus_field_bindings.get(slot):
            parameters = {key: values[field] for key, field in spec.stimulus_field_bindings[slot].items()}
            selected = snapshot(document_for(stimulus, parameters), file_identity="experiment_values")
        else:
            if repo_root is None:
                from ..paths import find_repo_root
                repo_root = find_repo_root()
            selected = load_parameters(Path(repo_root) / stimulus.default_config, stimulus)
        for key, field in spec.stimulus_field_bindings.get(slot, {}).items():
            if selected["document"]["parameters"][key] != values[field]:
                raise ValueError(f"{slot}.{key} differs from experiment values; reload the stimulus configuration.")
        result[slot] = selected
    return result
