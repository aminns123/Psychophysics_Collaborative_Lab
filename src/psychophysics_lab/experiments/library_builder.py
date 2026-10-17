"""Library-first, JSON-only experiments using the ordinary TrialTimeline/RunContext.

This builder deliberately supports *simple two-choice spatial tasks*. Arbitrary
scientific updates remain Python, not executable strings in JSON. Every human
run still uses normal PsyCoLab calibration and participant-data preflight.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import random

from ..data.identifiers import validate_path_component
from ..experiments.responses import ResponseParadigm
from ..experiments.spec import ConfigField
from ..researcher import experiment, TrialTimeline, Show, Stimulus, RecordState, CollectResponse, UpdateState
from ..stimuli.registry import get_stimulus, list_stimuli
from ..paths import find_repo_root

BUILTIN = ("probe_above_below",)
CATALOG = Path("authoring/library_experiments.json")
DESIGNS = Path("configs/experiment_designs")
VALUE_KEYS = {"trial_count", "random_seed", "fixation_ms", "stimulus_ms",
              "interval_ms", "response_timeout_ms"}
SHOW_SLOTS = {"fixation", "probe"}


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _design_path(root: Path, identity: str):
    validate_path_component(identity, label="experiment")
    return Path(root) / DESIGNS / (identity + ".json")


def _catalog(root: Path):
    path = Path(root) / CATALOG
    if not path.exists():
        return []
    data = _read(path)
    if not isinstance(data, dict) or set(data) != {"schema_version", "experiments"} or data["schema_version"] != 1 or not isinstance(data["experiments"], list):
        raise ValueError("Invalid library experiment catalog.")
    records, seen = [], set()
    for row in data["experiments"]:
        if not isinstance(row, dict) or set(row) != {"id", "status", "tested_sha256"}:
            raise ValueError("Invalid library experiment catalog entry.")
        validate_path_component(row["id"], label="experiment")
        if (row["id"] in seen or row["id"] in BUILTIN or row["status"] not in ("draft", "ready")
                or not isinstance(row["tested_sha256"], str)):
            raise ValueError("Duplicate or invalid library experiment entry.")
        seen.add(row["id"])
        records.append(row)
    return records


def _write_catalog(root: Path, records):
    from ..data.session import atomic_write_json
    path = Path(root) / CATALOG
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, {"schema_version": 1, "experiments": records})


def validate_design(doc: dict, *, require_registered=True):
    """Validate the entire scientific design, without executing arbitrary JSON."""
    expected = {"schema_version", "experiment_id", "display_name", "description",
                "stimuli", "conditions", "response", "values", "actions"}
    if not isinstance(doc, dict) or set(doc) != expected or type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise ValueError("Library experiment requires schema_version=1 and the documented nine fields.")
    validate_path_component(doc["experiment_id"], label="experiment")
    if not isinstance(doc["display_name"], str) or not doc["display_name"].strip() or not isinstance(doc["description"], str):
        raise ValueError("Supply a readable experiment name and description.")
    stimuli = doc["stimuli"]
    if not isinstance(stimuli, dict) or set(stimuli) != SHOW_SLOTS:
        raise ValueError("Select exactly the fixation and probe stimulus roles.")
    if len(set(stimuli.values())) != len(stimuli) or any(not isinstance(v, str) for v in stimuli.values()):
        raise ValueError("Fixation and probe must be two distinct registered stimuli.")
    if require_registered:
        registered = {s.id: s for s in list_stimuli()}
        for role, identity in stimuli.items():
            if identity not in registered or registered[identity].render is None:
                raise ValueError(f"{role}: choose a Ready, raster-renderable stimulus from the library.")
    response = doc["response"]
    if not isinstance(response, dict) or set(response) != {"alternatives", "keys"}:
        raise ValueError("Response requires alternatives and keys.")
    if not isinstance(response["alternatives"], list) or not isinstance(response["keys"], list):
        raise ValueError("Response alternatives and keys must be arrays.")
    paradigm = ResponseParadigm(doc["experiment_id"], tuple(response["alternatives"]), tuple(response["keys"]))
    if len(paradigm.alternatives) != 2:
        raise ValueError("The basic library builder supports two alternatives.")
    conditions = doc["conditions"]
    if not isinstance(conditions, list) or len(conditions) != 2:
        raise ValueError("Supply exactly two conditions in response-alternative order.")
    positions = []
    for index, condition in enumerate(conditions):
        if not isinstance(condition, dict) or set(condition) != {"alternative", "probe_position_deg"}:
            raise ValueError("Each condition needs alternative and probe_position_deg.")
        if condition["alternative"] != paradigm.alternatives[index]:
            raise ValueError("Condition order must match the response alternatives.")
        pos = condition["probe_position_deg"]
        if not isinstance(pos, list) or len(pos) != 2 or any(
            type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 20 for v in pos
        ):
            raise ValueError("Probe positions must be finite [x_deg, y_deg] within 20 degrees.")
        positions.append(pos)
    if positions[0] == positions[1]:
        raise ValueError("Conditions must present distinct probe positions.")
    values = doc["values"]
    if not isinstance(values, dict) or set(values) != VALUE_KEYS:
        raise ValueError("Specify trial_count, random_seed and the four timing values.")
    fields = _fields(values)
    for field in fields:
        field.coerce(values[field.key])
    actions = doc["actions"]
    if not isinstance(actions, list) or len(actions) < 3 or len(actions) > 24:
        raise ValueError("Specify a short chronological list of trial actions.")
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("name"), str):
            raise ValueError("Each action needs a valid name.")
        kind = action.get("type")
        if kind == "show":
            if set(action) != {"type", "name", "duration", "slots"} or action["duration"] not in values:
                raise ValueError("Show actions require name, timing-field duration and slots.")
            if not isinstance(action["slots"], list) or len(set(action["slots"])) != len(action["slots"]) or set(action["slots"]) - SHOW_SLOTS:
                raise ValueError("Show slots must be a list of fixation/probe roles.")
        elif kind == "collect_response":
            if set(action) != {"type", "name", "timeout"} or action["timeout"] not in values:
                raise ValueError("Response action requires name and timing-field timeout.")
        elif kind == "record_state":
            if set(action) != {"type", "name"}:
                raise ValueError("RecordState requires only type and name.")
        elif kind == "update_correct_count":
            if set(action) != {"type", "name"}:
                raise ValueError("The built-in correct-count update requires only type and name.")
        else:
            raise ValueError(f"Unsupported basic-builder action: {kind!r}. Use Python for custom science.")
    _make_timeline(actions, values, (0.0, 1.0), paradigm.alternatives)
    return doc


def _fields(values):
    return (
        ConfigField("trial_count", "Number of trials", "int", values["trial_count"], minimum=1, maximum=1000),
        ConfigField("random_seed", "Condition seed", "int", values["random_seed"], minimum=0),
        ConfigField("fixation_ms", "Fixation time", "int", values["fixation_ms"], minimum=1, maximum=3600000, units="ms", section="Timing"),
        ConfigField("stimulus_ms", "Probe time", "int", values["stimulus_ms"], minimum=1, maximum=3600000, units="ms", section="Timing"),
        ConfigField("interval_ms", "Blank time", "int", values["interval_ms"], minimum=1, maximum=3600000, units="ms", section="Timing"),
        ConfigField("response_timeout_ms", "Response timeout (0 means unlimited)", "int", values["response_timeout_ms"], minimum=0, maximum=3600000, units="ms", section="Timing"),
    )


def _increment_correct(state, response):
    return dict(state) | {"correct_count": state["correct_count"] + int(response["correct"])}


def _make_timeline(actions, values, probe_position, alternatives):
    phases = []
    for item in actions:
        kind, name = item["type"], item["name"]
        if kind == "show":
            placements = tuple(Stimulus(slot, *(probe_position if slot == "probe" else (0.0, 0.0)))
                               for slot in item["slots"])
            phases.append(Show(name, duration=item["duration"], stimuli=placements))
        elif kind == "collect_response":
            phases.append(CollectResponse(name=name, actions=tuple(alternatives), timeout=item["timeout"]))
        elif kind == "record_state":
            phases.append(RecordState(name))
        elif kind == "update_correct_count":
            phases.append(UpdateState(_increment_correct, name=name))
    return TrialTimeline(tuple(phases)).resolve(values).validate_slots(SHOW_SLOTS)


def _document(root, identity):
    path = _design_path(root, identity)
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError(f"Missing or unsafe library experiment: {identity}")
    doc = validate_design(_read(path))
    if doc["experiment_id"] != identity:
        raise ValueError("Experiment ID does not match its design filename.")
    return doc


def _digest(root, identity):
    doc = _document(root, identity)
    files = [_design_path(root, identity)]
    for stim_id in doc["stimuli"].values():
        stim = get_stimulus(stim_id)
        files.append(Path(root) / stim.source_path)
        if stim.default_config:
            files.append(Path(root) / stim.default_config)
        files += [Path(root) / dependency for dependency in stim.source_dependencies]
    digest = sha256()
    for path in files:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(Path(root).resolve()):
            raise ValueError(f"Missing library dependency: {path}")
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def make_spec(root: Path, identity: str):
    """One generic Python executor for unlimited validated basic JSON designs."""
    root = Path(root).resolve()
    doc = _document(root, identity)
    expected_hash = _digest(root, identity)
    alternatives = tuple(doc["response"]["alternatives"])

    def procedure(run):
        if _digest(root, identity) != expected_hash:
            raise ValueError("Library design/stimulus changed. Restart and retest before running.")
        order = [i % 2 for i in range(run.values["trial_count"])]
        random.Random(run.values["random_seed"]).shuffle(order)
        run.initialise(expected_trials=len(order), resolution={
            "task": doc["description"], "condition_order": [alternatives[i] for i in order],
            "library_design": doc, "library_design_sha256": expected_hash,
            "stimulus_slots": run.stimulus_snapshots,
        })
        state = {"correct_count": 0}
        for selected in order:
            condition = doc["conditions"][selected]
            position = condition["probe_position_deg"]
            timeline = _make_timeline(doc["actions"], run.values, position, alternatives)
            run.play_trial(
                timeline, target=selected, condition=condition["alternative"],
                state=state, measurements={"probe_x_deg": float(position[0]), "probe_y_deg": float(position[1])},
                instructions="  ".join(f"{alt}: {key}" for alt, key in zip(alternatives, run.responses.keys)),
            )
            state = dict(run.trial_state)
        run.complete()

    # The same public spec, slots, calibration and recording as Python-authored tasks.
    return experiment(
        id=identity, name=doc["display_name"], description=doc["description"],
        procedure=procedure, fields=_fields(doc["values"]),
        responses=ResponseParadigm(identity, alternatives, tuple(doc["response"]["keys"])),
        stimulus_slots={role: get_stimulus(stim_id).family for role, stim_id in doc["stimuli"].items()},
        stimulus_defaults=dict(doc["stimuli"]), calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"), supports_simulation=True,
        source_paths=("src/psychophysics_lab/experiments/library_builder.py",),
    )


def load_library(root=None, *, include_drafts=False, tolerate_errors=True):
    """Explicit built-in + catalog allowlist, never arbitrary disk auto-execution."""
    from .registry import _REGISTRY, register_experiment
    root = Path(root or find_repo_root()).resolve()
    records = [{"id": name, "status": "ready", "tested_sha256": ""} for name in BUILTIN] + _catalog(root)
    problems = {}
    for record in records:
        if record["status"] != "ready" and not include_drafts:
            continue
        name = record["id"]
        try:
            if name not in BUILTIN and not include_drafts:
                if record["tested_sha256"] != _digest(root, name):
                    raise ValueError("Library design or stimulus changed since validation.")
            spec = make_spec(root, name)
            if name in _REGISTRY:
                # A catalog refresh must not reject existing loaded versions.
                # The running interpreter keeps its previous version; a source
                # edit is detected by the procedure hash guard or on restart.
                existing = _REGISTRY[name]
                if getattr(existing.procedure, "__module__", "") == __name__:
                    continue
                raise ValueError(f"Experiment ID already belongs to another module: {name}")
            register_experiment(spec)
        except Exception as exc:
            if not tolerate_errors:
                raise
            problems[name] = f"{type(exc).__name__}: {exc}"
    return problems


def create_design(root, name, probe="vertical_line_probe", fixation="fixation_cross", separation_deg=2.0):
    """Create JSON only; user-generated experiments need NO new Python file."""
    root = Path(root).resolve()
    validate_path_component(name, label="experiment")
    from .registry import _REGISTRY
    if name in BUILTIN or name in _REGISTRY or any(r["id"] == name for r in _catalog(root)):
        raise ValueError("Experiment name already exists. Choose a new ID.")
    if not isinstance(separation_deg, (int, float)) or isinstance(separation_deg, bool) or not math.isfinite(separation_deg) or not 0.7 <= separation_deg <= 10:
        raise ValueError("Probe separation must be 0.7–10 degrees.")
    if probe == fixation:
        raise ValueError("Choose different probe and fixation stimuli.")
    doc = default_design(name, probe, fixation, float(separation_deg))
    validate_design(doc)
    path = _design_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, allow_nan=False)
        f.write("\n")
    entries = _catalog(root)
    entries.append({"id": name, "status": "draft", "tested_sha256": ""})
    _write_catalog(root, entries)
    return path


def default_design(name, probe="vertical_line_probe", fixation="fixation_cross", separation_deg=2.0):
    return {
        "schema_version": 1, "experiment_id": name,
        "display_name": name.replace("_", " ").title(),
        "description": "Was the vertical probe above or below the fixation cross?",
        "stimuli": {"fixation": fixation, "probe": probe},
        "conditions": [
            {"alternative": "above", "probe_position_deg": [0.0, separation_deg]},
            {"alternative": "below", "probe_position_deg": [0.0, -separation_deg]},
        ],
        "response": {"alternatives": ["above", "below"], "keys": ["F", "J"]},
        "values": {"trial_count": 6, "random_seed": 123,
                   "fixation_ms": 500, "stimulus_ms": 200,
                   "interval_ms": 150, "response_timeout_ms": 0},
        "actions": [
            {"type": "show", "name": "fixation", "duration": "fixation_ms", "slots": ["fixation"]},
            {"type": "record_state", "name": "before_probe"},
            {"type": "show", "name": "probe", "duration": "stimulus_ms", "slots": ["fixation", "probe"]},
            {"type": "show", "name": "blank", "duration": "interval_ms", "slots": []},
            {"type": "collect_response", "name": "answer", "timeout": "response_timeout_ms"},
            {"type": "record_state", "name": "response_received"},
            {"type": "update_correct_count", "name": "update_correct_count"},
        ],
    }


def inventory(root):
    return [{"id": name, "status": "ready", "builtin": True} for name in BUILTIN] + [
        dict(item, builtin=False) for item in _catalog(root)
    ]


def test_design(root, name):
    """Software-only simulation, canonical validation, then fingerprint test."""
    root = Path(root).resolve()
    if name in BUILTIN:
        raise ValueError("Built-in demos are already versioned and tested in CI.")
    if name not in [r["id"] for r in _catalog(root)]:
        raise ValueError("Unknown library draft.")
    from .registry import _REGISTRY
    spec = make_spec(root, name)
    previous = _REGISTRY.get(name)
    # Virtual validation must exercise the CURRENT design, even if a Ready
    # version of the same ID was previously loaded in this interpreter.
    _REGISTRY[name] = spec
    try:
        from simulations.run import simulate
        from scripts.validate_run import validate_run
        from ..development import user_data_root
        workspace = user_data_root(root)
        workspace.mkdir(parents=True, exist_ok=True)
        marker = workspace / ".psycolab_user_env.json"
        expected = {"schema_version": 1, "purpose": "development_only", "human_acquisition_allowed": False}
        if marker.exists():
            if marker.is_symlink() or _read(marker) != expected:
                raise ValueError("Unsafe development output marker.")
        else:
            marker.write_text(json.dumps(expected) + "\n", encoding="utf-8")
        artifacts, _ = simulate(repo_root=root, data_root=workspace, experiment_id=name, analyse=False)
        if artifacts.status != "completed":
            raise ValueError(f"Virtual run not completed: {artifacts.status}")
        errors = [item for item in validate_run(artifacts.run_directory) if not item.passed]
        if errors:
            raise ValueError("Saved run failed validation: " + "; ".join(str(e) for e in errors))
    finally:
        if previous is None:
            _REGISTRY.pop(name, None)
        else:
            _REGISTRY[name] = previous
    digest = _digest(root, name)
    records = _catalog(root)
    for row in records:
        if row["id"] == name:
            row["status"] = "draft"
            row["tested_sha256"] = digest
    _write_catalog(root, records)
    return artifacts.run_directory


def mark_ready(root, name):
    root = Path(root).resolve()
    records = _catalog(root)
    target = next((item for item in records if item["id"] == name), None)
    if target is None:
        raise ValueError("No researcher-created experiment with that name.")
    if not target["tested_sha256"] or target["tested_sha256"] != _digest(root, name):
        raise ValueError("Test the current JSON and stimulus sources before marking Ready.")
    target["status"] = "ready"
    _write_catalog(root, records)
    return _design_path(root, name)
