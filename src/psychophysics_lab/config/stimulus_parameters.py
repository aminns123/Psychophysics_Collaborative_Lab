"""JSON values validated by registered stimulus declarations, with portable snapshots."""
import hashlib
import json
from pathlib import Path
from ..stimuli.registry import get_stimulus
from ..data.identifiers import validate_path_component


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_document(document, stimulus):
    if not isinstance(document, dict) or (set(document) - {"parameter_info"}) != {"schema_version", "stimulus_id", "parameters"}:
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



def migrate_legacy_detection_snapshots(spec, values, snapshots):
    """Safely translate a saved pre-atomic *configuration* to independent slots.

    This is an explicit, bounded migration of user-selected stimulus dimensions,
    not a reinterpretation of historical trial data. The original snapshots
    remain unmodified and their identities/hashes are preserved in migration
    metadata. Do not infer a per-trial probe position, target or increment from
    saved DetectionScene defaults: those belong to trial_events/prepare_stimuli.
    """
    old_slots = {"first", "second"}
    if not old_slots.intersection(snapshots):
        return snapshots
    supported = {
        "ellipse_centre", "ellipse_major_axis",
        "line_position_baseline", "line_position_flanker",
    }
    if spec.id not in supported:
        raise ValueError(
            "Legacy DetectionScene snapshots cannot be migrated for this experiment."
        )
    expected = {"fixation", "first"}
    if spec.id.startswith("ellipse_"):
        expected.add("second")
    if not expected <= snapshots.keys():
        raise ValueError(
            f"Legacy {spec.id} configuration is missing source snapshots: "
            f"{sorted(expected - snapshots.keys())}. Keep the original files "
            "and recreate the configuration; no parameters were inferred."
        )
    if set(snapshots) - (expected | {"ready_fixation"}):
        raise ValueError(
            "Mixed legacy/current stimulus slots cannot be migrated automatically. "
            "Load one complete configuration version."
        )
    for slot in expected:
        if snapshots[slot]["document"]["stimulus_id"] != "detection_scene":
            raise ValueError(
                "Mixed legacy/current stimulus identities cannot be migrated. "
                "Keep the original snapshots unchanged."
            )

    source = snapshots["first"]["document"]["parameters"]
    # Pre-2026 DetectionScene JSON omitted these two fields. Its documented
    # historical raster dimensions were 0.133 and 0.013 degrees.
    historical_defaults = {"probe_length_deg": 0.133, "probe_width_deg": 0.013}
    common = ("size_deg", "probe_length_deg", "probe_width_deg")
    if spec.id.startswith("ellipse_"):
        common += ("ring_radius_deg",)
    for slot in expected - {"first"}:
        other = snapshots[slot]["document"]["parameters"]
        if any(other.get(key, historical_defaults.get(key)) !=
               source.get(key, historical_defaults.get(key)) for key in common):
            raise ValueError(
                f"Legacy DetectionScene {slot}/first dimensions disagree. "
                "The atomic experiment has one shared probe/ring definition; "
                "edit these independently rather than silently picking a slot."
            )

    background = values["background_intensity"]
    if any(
        snapshots[slot]["document"]["parameters"].get("background") != background
        for slot in expected
    ):
        raise ValueError(
            "Legacy scene background differs from the experiment's background. "
            "Choose the intended scientific intensity explicitly before migration."
        )
    from ..stimuli.registry import get_stimulus

    def converted(slot, overrides):
        stimulus = get_stimulus(spec.stimulus_defaults[slot])
        params = {field.key: field.default for field in stimulus.parameters}
        document = document_for(stimulus, params | overrides)
        original = {
            old: {
                "file_identity": snapshots[old]["file_identity"],
                "resolved_sha256": snapshots[old]["resolved_sha256"],
                "file_sha256": snapshots[old].get("file_sha256"),
            }
            for old in sorted(expected)
        }
        return snapshot(
            document, file_identity="migrated_legacy_detection_scene"
        ) | {"migrated_from": original}

    probe = {
        "length_deg": source.get("probe_length_deg", 0.133),
        "width_deg": source.get("probe_width_deg", 0.013),
        "background": background,
    }
    migrated = dict(snapshots)
    for old in expected:
        del migrated[old]
    migrated["probe"] = converted("probe", probe)
    migrated["fixation"] = converted(
        "fixation", {"background": background},
    )
    if "ellipse" in spec.stimulus_defaults:
        migrated["ellipse"] = converted(
            "ellipse", {
                "background": background,
                "size_deg": source["size_deg"],
                "outer_radius_deg": values["ring_radius_deg"],
                "aspect_ratio": 1.0,
                "display_contrast": (
                    values["ring_increment"] / (1 - background)
                    if background < 1 and values["ring_increment"] is not None
                    else 0.0
                ),
            },
        )
    if "flanker" in spec.stimulus_defaults:
        migrated["flanker"] = converted(
            "flanker", {
                "background": background,
                "spatial_frequency_cpd": values["flanker_cpd"],
            },
        )
    return migrated

def resolve_stimuli(spec, values, snapshots=None, *, repo_root=None):
    """Resolve current atomic slots; migrate only explicitly supported old setups."""
    snapshots = migrate_legacy_detection_snapshots(spec, values, snapshots or {})
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
            if digest(selected["document"]) != selected.get("resolved_sha256"):
                raise ValueError(f"{slot}: stimulus snapshot changed; reload and validate its JSON.")
            document = validate_document(selected["document"], stimulus)
            if document != selected["document"]:
                # Preserve the original source identity/hash while making formerly
                # hard-coded defaults explicit in the NEW run's resolved snapshot.
                selected = dict(selected) | {
                    "document": document, "resolved_sha256": digest(document),
                    "source_resolved_sha256": selected["resolved_sha256"],
                }
            # File identity is portable metadata, never an absolute source path.
            if Path(selected["file_identity"]).name != selected["file_identity"] or "/" in selected["file_identity"] or "\\" in selected["file_identity"]:
                raise ValueError("Stimulus file identity must be a filename, not a path.")
        elif spec.stimulus_field_bindings.get(slot):
            # Bind declared inputs while retaining the stimulus class's other
            # defaults. Saved JSON documents still require every original key.
            parameters = {f.key: f.default for f in stimulus.parameters} | {
                key: values[field] for key, field in spec.stimulus_field_bindings[slot].items()}
            selected = snapshot(document_for(stimulus, parameters), file_identity="experiment_values")
        else:
            if repo_root is None:
                from ..paths import find_repo_root
                repo_root = find_repo_root()
            # One-file shared classes can declare defaults without a new JSON.
            if stimulus.default_config:
                from ..extensions import source_path
                selected = load_parameters(source_path(repo_root, stimulus, stimulus.default_config), stimulus)
            else:
                selected = snapshot(document_for(stimulus), file_identity="library_defaults")
        for key, field in spec.stimulus_field_bindings.get(slot, {}).items():
            if selected["document"]["parameters"][key] != values[field]:
                raise ValueError(f"{slot}.{key} differs from experiment values; reload the stimulus configuration.")
        result[slot] = selected
    return result
