"""Portable containers for existing experiment/stimulus JSON, never source code."""
from dataclasses import replace
from copy import deepcopy
from importlib.metadata import version, PackageNotFoundError
import json
import hashlib
import os
from pathlib import Path
import shutil
from uuid import uuid4

from ..operational_compatibility import portable_engine_inventory
from .stimulus_parameters import digest, resolve_stimuli, snapshot, validate_document, load_parameters
from .preflight import validate_setup

FORMAT = "psycolab.experiment.configuration"
SCHEMA_VERSION = 2
MAX_BYTES = 1024 * 1024
CALIBRATION_NOTICE = (
    "Scientific settings only. Your participant, data location, local display and calibration are retained. "
    "Matching JSON does not establish equivalent physical stimuli. Review local geometry, photometry, "
    "timing and apparatus qualification, then Test before Run. Researcher overrides are not transferred."
)


def software_identity(root, spec, snapshots):
    from .. import __version__, extensions
    from ..experiment_reference import source_digest
    from ..core.runner import _runtime_source_fingerprints
    from ..experiments._internal.library_builder import portable_design_fingerprint

    root = Path(root).resolve()
    # Reuse existing source inventories. UI/docs changes need not invalidate
    # science. Include shared analysis and framework-local scientific helpers
    # even when a procedure imports them indirectly.
    framework = "src/psychophysics_lab/"
    prefixes = ("simulations/",) + tuple(framework + part for part in
        ("core/", "adaptive/", "methods/", "config/", "experiments/", "stimuli/", "data/", "analysis/"))
    shared = {framework + name for name in ("researcher.py", "stimulus_library.py", "extensions.py")}
    inventory = {path: _normalized_source_hash(root/path, recorded)
                 for path, recorded in _runtime_source_fingerprints(root).items()
                 if path.startswith(prefixes) or path in shared}
    if framework + "analysis/primary.py" not in inventory:
        raise ValueError("Installed scientific engine source is unavailable; configuration compatibility cannot be checked.")

    selected = replace(spec, stimulus_defaults={s: v["document"]["stimulus_id"] for s, v in snapshots.items()})
    sources = {"declared": source_digest(root, selected, normalize_newlines=True)}
    design = portable_design_fingerprint(root, spec)
    if design is not None:
        sources["library_design"] = design
    # The existing Ready check covers indirect laboratory helpers and presets,
    # including an external stimulus selected by an otherwise official study.
    laboratory = extensions.check_run(root, spec, snapshots)
    if laboratory is not None:
        configured = extensions.configured(root)
        if configured is None or configured[1] != laboratory["namespace"]:
            raise ValueError("Laboratory extension selection changed during configuration verification.")
        sources["laboratory"] = {
            path: _normalized_source_hash(extensions.source_at(configured[0], path), recorded)
            for path, recorded in laboratory["source_sha256"].items()
        }
        if extensions.fingerprint(root) != laboratory["fingerprint"]:
            raise ValueError("Laboratory source changed during configuration verification; restart and retest.")

    try:
        dependencies = {name: version(name) for name in ("numpy", "pyglet")}
    except PackageNotFoundError as exc:
        raise ValueError("A required installed scientific dependency is missing; repair the local installation first.") from exc
    return {"psycolab_version": __version__, "source_sha256": digest(sources),
            "engine_sha256": digest(portable_engine_inventory(inventory)), "dependencies": dependencies}


def _normalized_source_hash(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Scientific source changed during configuration verification; retry with verified source.")
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def _object(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{label}: expected exactly {', '.join(keys)}.")


def _complete(values, fields, label):
    if not isinstance(values, dict):
        raise ValueError(f"{label}: values must be an object.")
    keys = {f.key for f in fields}
    if set(values) != keys:
        raise ValueError(f"{label}: missing parameters {sorted(keys-set(values))}; unsupported parameters {sorted(set(values)-keys)}.")
    # Existing validators remain authoritative. Do not coerce nested downloaded
    # objects into strings or fill omitted/null inputs from unspecified defaults.
    for field in fields:
        value = values[field.key]
        if (value is None or isinstance(value, (dict, list))
                or (isinstance(value, bool) and not any(type(choice) is bool for choice in field.choices))
                or (value == "" and field.kind != "text")):
            raise ValueError(f"{label}.{field.key}: supply an explicit {field.kind} value.")


def make_document(root, request, profile):
    from ..experiments._internal.registry import get_experiment
    spec = get_experiment(request.experiment_id)
    request = validate_setup(request, spec, profile, mode="configuration")
    snapshots = resolve_stimuli(spec, request.experiment_values, request.stimulus_snapshots, repo_root=root)
    # Rebuild existing documents from scientific values only: no paths,
    # participant data, calibration, arbitrary parameter_info or run results.
    document = {"format": FORMAT, "schema_version": SCHEMA_VERSION,
                "experiment": {"schema_version": 1, "experiment_id": spec.id, "values": dict(request.experiment_values)},
                "stimuli": {slot: {k: deepcopy(selected["document"][k]) for k in ("schema_version", "stimulus_id", "parameters")}
                            for slot, selected in snapshots.items()},
                "presentation": {"show_response_instructions": request.show_response_instructions},
                "software": software_identity(root, spec, snapshots)}
    validate_portable(document, root, request, profile)
    return document


def validate_portable(document, root, current, profile):
    """Pure validation against the installed catalogue; no downloaded imports."""
    from ..experiments._internal.registry import list_experiments
    from ..stimuli.registry import list_stimuli
    from ..ui.parameter_files import validate_experiment_json
    from ..ui.settings_review import describe_settings
    experiments = {s.id: s for s in list_experiments(include_historical=True)}
    stimuli = {s.id: s for s in list_stimuli()}
    _object(document, ("format", "schema_version", "experiment", "stimuli", "presentation", "software"), "Configuration")
    if document["format"] == FORMAT and type(document["schema_version"]) is int and document["schema_version"] == 1:
        raise ValueError("Portable configuration version 1 lacks complete scientific fingerprints. "
                         "Ask the sender to open the verified original settings in Review and export again with this version of PsyCoLab.")
    if document["format"] != FORMAT or type(document["schema_version"]) is not int or document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported portable configuration format/schema; use a supported PsyCoLab export.")
    experiment = document["experiment"]
    _object(experiment, ("schema_version", "experiment_id", "values"), "Experiment")
    if type(experiment["schema_version"]) is not int or experiment["schema_version"] != 1:
        raise ValueError("Unsupported experiment JSON schema.")
    identity = experiment["experiment_id"]
    if not isinstance(identity, str) or identity not in experiments:
        raise ValueError(f"Required experiment {identity!r} is not installed/enabled locally. Install and verify it separately; JSON does not install source code.")
    spec = experiments[identity]
    _complete(experiment["values"], spec.fields, "Experiment")
    values = validate_experiment_json(experiment, spec)
    if not isinstance(document["stimuli"], dict) or set(document["stimuli"]) != set(spec.stimulus_slots):
        raise ValueError("Configuration must contain every declared stimulus slot, with no unknown slots.")
    snapshots = {}
    for slot, data in document["stimuli"].items():
        _object(data, ("schema_version", "stimulus_id", "parameters"), f"Stimulus {slot}")
        sid = data["stimulus_id"]
        if not isinstance(sid, str) or sid not in stimuli:
            raise ValueError(f"{slot}: required stimulus {sid!r} is not installed/enabled locally. Install and verify it separately.")
        _complete(data["parameters"], stimuli[sid].parameters, slot)
        snapshots[slot] = snapshot(validate_document(data, stimuli[sid]), file_identity="configuration.json") | {
            "configuration_origin": {"document_sha256": digest(document),
                                     "schema_version": document["schema_version"],
                                     "software": deepcopy(document["software"])}}
    presentation = document["presentation"]
    _object(presentation, ("show_response_instructions",), "Presentation")
    if type(presentation["show_response_instructions"]) is not bool:
        raise ValueError("Response guidance must be a boolean.")
    local = software_identity(root, spec, snapshots)
    incoming = document["software"]
    _object(incoming, tuple(local), "Software identity")
    if not isinstance(incoming["psycolab_version"], str) or not incoming["psycolab_version"]:
        raise ValueError("Missing PsyCoLab software version.")
    if any(incoming[k] != local[k] for k in ("source_sha256", "engine_sha256", "dependencies")):
        raise ValueError("Incompatible experiment/stimulus source revision, scientific engine or dependency version. Use compatible, separately verified software; settings were not applied.")
    candidate = replace(current, experiment_id=identity, experiment_values=values, stimulus_snapshots=snapshots,
                        monitor_profile_hash=None, researcher_override=None,
                        show_response_instructions=presentation["show_response_instructions"])
    candidate = validate_setup(candidate, spec, profile, mode="configuration")
    describe_settings(spec, candidate.experiment_values, candidate.stimulus_snapshots, profile=profile)
    warnings = (["PsyCoLab version differs; declared scientific sources, engine and dependency fingerprints match."]
                if incoming["psycolab_version"] != local["psycolab_version"] else [])
    return candidate, warnings


def read_document(path):
    path = Path(path).expanduser()
    if path.suffix.lower() != ".json" or not path.is_file():
        raise ValueError("Select an existing JSON configuration file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Configuration exceeds the 1 MiB size limit.")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}.")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("Non-finite JSON numbers are unsupported.")
    try:
        document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=invalid_constant)
        digest(document)  # Reject numeric overflows such as 1e999 as well.
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise ValueError(f"Cannot read configuration JSON: {exc}") from exc
    return document


def write_export(path, document):
    """Create exclusively; never replace an existing file or symlink."""
    path = Path(path).expanduser()
    if not path.is_absolute() or path.suffix.lower() != ".json":
        raise ValueError("Choose an absolute JSON export filename.")
    encoded = json.dumps(document, indent=2, allow_nan=False) + "\n"
    if len(encoded.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Configuration exceeds the 1 MiB size limit.")
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ValueError("Export file already exists. Choose a new filename; existing files are preserved.") from exc
    return path


def save_local(root, repo, document, current, profile, *, preserve_origin=False):
    """Stage existing JSON files, validate them, then publish one new directory."""
    from ..data.session import atomic_write_json
    from ..data.identifiers import validate_path_component
    from ..stimuli.registry import get_stimulus
    from ..experiments._internal.registry import get_experiment
    from ..ui.parameter_files import file_hash
    document = deepcopy(document)
    candidate, _ = validate_portable(document, repo, current, profile)
    token = uuid4().hex[:10]
    parent = Path(root).resolve()/"parameter_files"/validate_path_component(candidate.experiment_id, label="experiment")
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent/(".configuration_" + token)
    destination = parent/("configuration_" + token)
    staging.mkdir()
    try:
        atomic_write_json(staging/"experiment.json", document["experiment"])
        atomic_write_json(staging/"configuration.json", document)
        snapshots = {}
        for slot, data in document["stimuli"].items():
            name = validate_path_component(slot, label="slot") + "_" + token + ".json"
            atomic_write_json(staging/name, data)
            origin = candidate.stimulus_snapshots[slot]["configuration_origin"]
            previous = current.stimulus_snapshots.get(slot)
            if (preserve_origin and current.experiment_id == candidate.experiment_id and previous
                    and previous["document"]["stimulus_id"] == data["stimulus_id"]):
                origin = previous.get("configuration_origin", origin)
            snapshots[slot] = load_parameters(staging/name, get_stimulus(data["stimulus_id"])) | {
                "configuration_origin": deepcopy(origin)}
        candidate = validate_setup(replace(candidate, stimulus_snapshots=snapshots),
                                   get_experiment(candidate.experiment_id), profile, mode="configuration")
        # Both paths are newly allocated children of this local configuration
        # directory; rename exposes only a fully validated, complete save.
        if destination.exists():
            raise ValueError("Configuration save collided; try again. Existing saves are preserved.")
        staging.rename(destination)
    finally:
        if staging.exists():
            assert staging.resolve().parent == parent.resolve() and staging.name == ".configuration_" + token
            shutil.rmtree(staging)
    files = {str(p): file_hash(p) for p in destination.glob("*.json")}
    return candidate, files, destination/"configuration.json"
