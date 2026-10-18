from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Iterator
from uuid import uuid4

from .. import __version__ as source_version
from ..config.models import SetupRequest
from ..config.preflight import validate_setup
from ..config.local import config_root, content_hash, save_preferences
from ..config.monitor import load_monitor_profiles
from ..data.index import upsert_run_index
from ..data.participants import validate_participant_id
from ..data.session import atomic_write_json, copy_snapshot
from ..data.trials import (
    READABLE_TRIALS_FILENAME,
    TRIAL_DATA_DICTIONARY_FILENAME,
    TRIAL_COLUMN_DEFINITIONS,
    TRIAL_SCHEMA_VERSION,
    TrialLog,
    write_readable_trial_table,
    write_trial_data_dictionary,
    trial_dictionary_overrides,
)
from ..data.workspace import (
    DATA_LAYOUT_SCHEMA_VERSION,
    create_run_directory,
    run_number_from_path,
    save_workspace_state,
)
from psychophysics_lab.experiments._internal.registry import get_experiment
from ..paths import default_data_root, find_repo_root, resolve_data_root


@dataclass(frozen=True)
class RunArtifacts:
    run_directory: Path
    trial_log_file: Path
    response_file: Path
    conditions_file: Path
    parameters_file: Path
    manifest_file: Path
    status: str = "returned"
    accepted_trials: int = 0
    completed_staircase_ids: tuple = ()
    unfinished_staircase_ids: tuple = ()


@contextmanager
def _legacy_runtime_context(repo_root: Path) -> Iterator[None]:
    """Preserve working-directory semantics for the internally retained CSF presenter."""
    previous_cwd = Path.cwd()
    root_text = str(repo_root)
    added = False
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
        added = True
    os.chdir(repo_root)
    try:
        yield
    finally:
        os.chdir(previous_cwd)
        if added:
            try:
                sys.path.remove(root_text)
            except ValueError:
                pass


def _safe_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _git_provenance(repo_root: Path) -> dict:
    payload = {"commit": None, "working_tree_clean": None}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout
        payload["commit"] = commit or None
        payload["working_tree_clean"] = not bool(status.strip())
    except Exception as exc:
        payload["error"] = repr(exc)
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_source_fingerprints(repo_root: Path) -> dict[str, str]:
    """Hash the acquisition source inventory, independent of Git availability.

    All Python sources under the package and legacy runtime roots are included,
    along with the legacy dependency archive. Profiles are saved separately in
    each run; data, tooling, tests and local environment files are not sources.
    """
    repo_root = repo_root.resolve()
    roots = ("src/psychophysics_lab", "simulations")
    excluded = {"tests", "test", "__pycache__", "tmp", "temp", "node_modules"}
    paths = []
    for relative_root in roots:
        source_root = repo_root / relative_root
        if source_root.is_symlink() or source_root.resolve() != source_root:
            continue
        for directory, subdirectories, filenames in os.walk(source_root, followlinks=False):
            base = Path(directory)
            subdirectories[:] = sorted(
                name for name in subdirectories
                if not name.startswith(".") and name.lower() not in excluded
                and (name.lower() != "data" or
                     (relative_root == "src/psychophysics_lab" and base == source_root))
                and not (base / name).is_symlink()
                and (base / name).resolve() == base / name
                and (base / name).resolve().is_relative_to(source_root.resolve())
            )
            for name in filenames:
                path = base / name
                # Researcher-authored experiment/stimulus modules are legitimate
                # runtime sources even if a researcher calls one "test_*".
                # Exclude Python test helpers elsewhere, but never omit scientific
                # source from provenance merely because of its chosen name.
                within_package = (
                    relative_root == "src/psychophysics_lab"
                    and path.relative_to(source_root).parts[0] in
                    {"experiments", "stimuli", "adaptive"}
                )
                if (path.suffix == ".py" and not path.is_symlink()
                        and not name.startswith((".", "conftest."))
                        and (within_package or not name.startswith("test_"))
                        and (within_package or not name.endswith("_test.py"))):
                    paths.append(path)
    paths.extend(repo_root / name for name in ("src/psychophysics_lab/_reference_csf/packages.zip",)
                 if (repo_root / name).is_file() and not (repo_root / name).is_symlink())
    return {path.relative_to(repo_root).as_posix(): _sha256(path)
            for path in sorted(paths, key=lambda path: path.relative_to(repo_root).as_posix())}



def _run_artifact_fingerprints(run_dir: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.name == "manifest.json" or path.name.endswith(".tmp"):
            continue
        relative = path.relative_to(run_dir).as_posix()
        fingerprints[relative] = _sha256(path)
    return fingerprints


def _software_provenance(repo_root: Path) -> dict:
    return {
        "psycolab_version": source_version,
        "installed_distribution_version": _safe_version("psychophysics-lab"),
        "python_version": platform.python_version(),
        "python_executable_name": Path(sys.executable).name,
        "platform": platform.platform(),
        "packages": {
            "numpy": _safe_version("numpy"),
            "pyglet": _safe_version("pyglet"),
            "textual": _safe_version("textual"),
        },
        "git": _git_provenance(repo_root),
        "runtime_source_sha256": _runtime_source_fingerprints(repo_root),
    }


def _loaded_graphics_provenance(repo_root: Path) -> dict:
    """Describe the actual loaded module without importing/changing a renderer.

    Distribution metadata can differ from the retained archive's Pyglet. Paths
    are portable source identities, not the laboratory computer's home path.
    """
    module = sys.modules.get("pyglet")
    if module is None:
        return {"loaded": False, "installed_distribution_version": _safe_version("pyglet")}
    source = str(getattr(module, "__file__", "")).replace("\\", "/")
    root = repo_root.resolve().as_posix().rstrip("/") + "/"
    if source.lower().startswith(root.lower()):
        origin = source[len(root):]
    elif "/site-packages/" in source:
        origin = "site-packages/" + source.split("/site-packages/", 1)[1]
    else:
        origin = "external/" + Path(source).name
    return {"loaded": True, "version": getattr(module, "version", None), "origin": origin,
            "installed_distribution_version": _safe_version("pyglet"),
            "module_file_sha256": _sha256(Path(source)) if Path(source).is_file() else None}


def _relative(run_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(run_dir.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _portable_request_payload(request: SetupRequest) -> dict:
    payload = asdict(request)
    payload["data_root"] = None
    return payload


def _trial_count(trial_log_file: Path) -> int:
    if not trial_log_file.exists():
        return 0
    with trial_log_file.open("r", encoding="utf-8") as handle:
        count = sum(1 for _ in handle)
    return max(0, count - 1)  # subtract TSV header


def _index_row(
    *,
    run_uuid: str,
    request: SetupRequest,
    grouping_parts: tuple[str, ...],
    run_dir: Path,
    data_root: Path,
    status: str,
    started_utc: str,
    finished_utc: str = "",
    accepted_trials: int | str = "",
) -> dict:
    return {
        "run_uuid": run_uuid,
        "participant_id": request.participant_id,
        "experiment_id": request.experiment_id,
        "monitor_profile_id": request.monitor_profile_id,
        "condition_path": "/".join(grouping_parts),
        "date": run_dir.parent.name,
        "run_number": run_number_from_path(run_dir),
        "status": status,
        "accepted_trials": accepted_trials,
        "relative_path": run_dir.relative_to(data_root).as_posix(),
        "started_utc": started_utc,
        "finished_utc": finished_utc,
    }


def _manifest_payload(
    *,
    request: SetupRequest,
    setup: dict,
    profile: dict,
    run_dir: Path,
    data_root: Path,
    repo_root: Path,
    grouping_parts: tuple[str, ...],
    run_uuid: str,
    status: str,
) -> dict:
    from ..config.monitor import _profile_from_dict
    relative_run_path = run_dir.relative_to(data_root).as_posix()
    return {
        "schema_version": 3,
        "data_layout_schema_version": DATA_LAYOUT_SCHEMA_VERSION,
        "project": "PsyCoLab — Psychophysics Collaborative Lab",
        "run_uuid": run_uuid,
        "run_label": run_dir.name,
        "run_number": run_number_from_path(run_dir),
        "date": run_dir.parent.name,
        "relative_run_path": relative_run_path,
        "storage_hierarchy": {
            "participant_id": request.participant_id,
            "experiment_id": request.experiment_id,
            "monitor_profile_id": request.monitor_profile_id,
            "experiment_grouping_folders": list(grouping_parts),
        },
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "participant_id": request.participant_id,
        "session_mode": request.session_mode,
        "experiment_id": request.experiment_id,
        "monitor_profile_id": request.monitor_profile_id,
        "experiment_values": request.experiment_values,
        "legacy_setup": setup,
        "monitor_profile": profile,
        "calibration": {
            "status": profile.get("calibration_status", "unverified"),
            "has_encoded_luminance_mapping": bool(profile.get("luminance_calibration")),
            "has_verified_luminance_mapping": (
                _profile_from_dict(profile).has_verified_luminance_mapping
            ),
            "notes": profile.get("calibration_notes", ""),
        },
        "path_policy": (
            "run file references are relative; data-root/repository absolute paths "
            "are not part of canonical scientific metadata"
        ),
        "software": _software_provenance(repo_root),
    }


def run_request(
    request: SetupRequest, *, repo_root: Path | None = None, data_root: Path | None = None,
    simulation=None, presentation=None,
) -> RunArtifacts:
    """Validate first; allocate a new record; preserve primary and cleanup errors."""
    import random
    root = (repo_root or find_repo_root()).resolve()
    candidate = data_root or (Path(request.data_root).expanduser() if request.data_root else default_data_root(root))
    data = resolve_data_root(candidate, root, allow_synthetic=simulation is not None or presentation is not None)
    if presentation is not None:
        from .presentation_testing import PresentationTestRequest,MARKER
        if not isinstance(presentation,PresentationTestRequest) or simulation is not None:
            raise TypeError("Use the dedicated presentation-test facility.")
        expected=(config_root(root).parent/'psycolab_presentation_tests').resolve()
        if data!=expected or not (data/MARKER).is_file() or not request.participant_id.startswith('presentation_test_'):
            raise ValueError("Presentation testing requires its isolated marked root and reserved identity.")
    elif request.participant_id.startswith('presentation_test_'):
        raise ValueError("Presentation-test identities cannot be used for human or simulated acquisition.")
    if simulation is None and request.participant_id.lower().startswith("synthetic_"):
        raise ValueError("Participant IDs beginning synthetic_ are reserved for virtual observers.")
    if simulation is not None:
        from .synthetic import SimulationRun
        if not isinstance(simulation, SimulationRun):
            raise TypeError("Use the dedicated simulations facility for synthetic acquisition.")
        simulation.validate(data, root, request)
    data_kind = "uncalibrated_presentation_test" if presentation is not None else "synthetic" if simulation is not None else "human"
    config_root(root, data)  # Never mix machine configuration with source/data.
    spec = get_experiment(request.experiment_id)
    profiles = load_monitor_profiles(root)
    if request.monitor_profile_id not in profiles:
        raise ValueError(f"Unknown monitor profile: {request.monitor_profile_id}")
    profile = profiles[request.monitor_profile_id]
    if presentation is not None:
        from .presentation_testing import validate_presentation
        request = validate_presentation(request,spec,profile)
    else:
        request = validate_setup(request, spec, profile, mode="simulation" if simulation is not None else "human")
    values = request.experiment_values
    grouping_parts = spec.data_path_parts(values, profile)
    setup = spec.build_legacy_setup(participant_id=request.participant_id, values=values, monitor_profile=profile)
    if presentation is not None: setup['data_kind']='uncalibrated_presentation_test'
    run_dir = create_run_directory(data, participant_id=request.participant_id, experiment_id=spec.id,
                                   monitor_profile_id=profile.id, grouping_parts=grouping_parts,
                                   now=datetime.now().astimezone())
    run_uuid = str(uuid4())
    state_dir = run_dir / "state"
    manifest_file = run_dir / "manifest.json"
    trial_log_file = run_dir / "trials.tsv"
    response_file = run_dir / "legacy_response.txt"
    conditions_file = state_dir / "conditions.runtime.json"
    parameters_file = state_dir / "parameters.runtime.json"
    user_config_file = state_dir / "user_experiment_config.json"
    adaptive_session_file = run_dir / "adaptive_session.json"
    runtime_display_file = run_dir / "runtime_display.json"
    started_utc = datetime.now(timezone.utc).isoformat()
    payload = {"schema_version": 3, "run_uuid": run_uuid, "created_utc": started_utc,
               "status": "configuring", "data_kind": data_kind, "participant_id": request.participant_id,
               "experiment_id": spec.id, "monitor_profile_id": profile.id}
    primary_error = None
    procedure_context = None

    def convenience(name, operation):
        try:
            operation()
        except Exception as exc:
            payload[name + "_error"] = repr(exc)

    def update_index():
        upsert_run_index(data, _index_row(run_uuid=run_uuid, request=request, grouping_parts=grouping_parts,
                         run_dir=run_dir, data_root=data, status=payload["status"], started_utc=started_utc,
                         finished_utc=payload.get("finished_utc", ""), accepted_trials=payload.get("accepted_trials", "")))

    def workspace():
        save_workspace_state(data, request, status=payload["status"], run_directory=run_dir,
                             legacy_setup=setup, manifest_file=manifest_file)

    try:
        # A minimal manifest survives failure while building rich provenance.
        atomic_write_json(manifest_file, payload)
        payload = _manifest_payload(request=request, setup=setup, profile=profile.to_dict(), run_dir=run_dir,
                    data_root=data, repo_root=root, grouping_parts=grouping_parts, run_uuid=run_uuid, status="configuring")
        payload["created_utc"] = started_utc
        payload["data_kind"] = data_kind
        if presentation is not None:
            payload['presentation_test']={'test_response_limit':presentation.trial_limit,'physical_certification':False,'scientific_human_data':False,'warning':'UNCALIBRATED PRESENTATION TEST — NOT HUMAN EXPERIMENTAL DATA'}
            atomic_write_json(run_dir/'UNCALIBRATED_TEST_DATA.json',payload['presentation_test']|{'data_kind':data_kind})
        if simulation is not None:
            payload["simulation"] = simulation.metadata
            atomic_write_json(run_dir / "SYNTHETIC_DATA.json", {"data_kind": "synthetic", **simulation.metadata})
        payload["monitor_profile_sha256"] = content_hash(profile.to_dict())
        from ..config.background_mapping import background_provenance
        mapping_evidence = background_provenance(config_root(root, data), profile, values)
        if mapping_evidence is not None:
            payload["background_mapping"] = mapping_evidence
        from ..config.readiness import profile_readiness
        payload["display_readiness"] = profile_readiness(spec, profile, repo_root=root, values=values)
        registered_sources = {}
        for relative in spec.source_paths:
            source = (root / relative).resolve()
            if not source.is_relative_to(root) or not source.is_file():
                raise ValueError(f"Registered experiment source is missing or outside the repository: {relative}")
            registered_sources[relative] = _sha256(source)
        payload["registered_source_sha256"] = registered_sources
        payload["adaptive_algorithm"] = asdict(spec.adaptive) if spec.adaptive else None
        payload["response_paradigm"] = asdict(spec.response_paradigm) if spec.response_paradigm else None
        payload["random_provenance"] = {"algorithm": "python.random MT19937", "initial_state": random.getstate()}
        payload["trial_schema_version"] = TRIAL_SCHEMA_VERSION
        payload["files"] = {"manifest": "manifest.json", "experiment_config": "experiment_config.json",
            "monitor_profile": "monitor_profile.json", "canonical_trials": "trials.tsv",
            "readable_trials": READABLE_TRIALS_FILENAME, "trial_data_dictionary": TRIAL_DATA_DICTIONARY_FILENAME,
            "runtime_display": "runtime_display.json", "resolved_experiment": "resolved_experiment.json",
            "adaptive_session": "adaptive_session.json", "legacy_response": "legacy_response.txt", "state_directory": "state/"}
        atomic_write_json(manifest_file, payload)
        atomic_write_json(run_dir / "experiment_config.json", {"schema_version": 2,
            "request": _portable_request_payload(request), "data_kind": data_kind, "normalised_experiment_values": values, "legacy_setup": setup,
            **({"background_mapping": mapping_evidence} if mapping_evidence is not None else {})})
        atomic_write_json(run_dir / "monitor_profile.json", profile.to_dict())
        atomic_write_json(run_dir / "stimulus_parameters.json", {"schema_version": 1, "slots": request.stimulus_snapshots})
        payload["files"]["stimulus_parameters"] = "stimulus_parameters.json"
        TrialLog(trial_log_file)  # Header remains valid even when no response is accepted.
        atomic_write_json(run_dir / "trial_context.json", {
            "schema_version": 1, "data_kind": data_kind, "run_uuid": run_uuid, "trial_schema_version": TRIAL_SCHEMA_VERSION,
            "canonical_trials": "trials.tsv", "applies_to": "all accepted-response rows in this new run",
            "monitor_profile": "monitor_profile.json", "monitor_profile_sha256": content_hash(profile.to_dict()),
            "profile_uuid": profile.profile_uuid, "profile_revision": profile.revision,
            "runtime_display": "runtime_display.json", "resolved_experiment": "resolved_experiment.json",
            "geometry_status": profile.geometry_status, "timing_status": profile.timing_status,
            "photon_timing_verified": False,
            **({"synthetic_clock": {
                "kind": "deterministic_virtual_utc",
                "epoch_utc": "2000-01-01T00:00:00+00:00",
                "source": "synthetic event_time_s",
                "not_wall_clock": True,
            }} if simulation is not None else {}),
        })
        payload["files"]["trial_context"] = "trial_context.json"
        dictionary_overrides = trial_dictionary_overrides(
            spec.trial_column_overrides, synthetic=simulation is not None
        )
        payload["trial_dictionary_overrides"] = {
            column: asdict(definition) | dictionary_overrides.get(column, {})
            for column, definition in TRIAL_COLUMN_DEFINITIONS.items()
        }
        write_trial_data_dictionary(run_dir / TRIAL_DATA_DICTIONARY_FILENAME, experiment_id=spec.id, overrides=dictionary_overrides)
        if simulation is None and presentation is None:
            convenience("workspace", workspace)
            convenience("local_preferences", lambda: save_preferences(config_root(root, data), active_monitor_profile_id=profile.id))
        convenience("runs_index", update_index)
        with _legacy_runtime_context(root):
            adapter = importlib.import_module(spec.configure_module)
            configure = getattr(adapter, spec.configure_function)
            conditions, parameters, response = configure(request.participant_id, str(data), setup, run_directory=str(run_dir))
            conditions_file, parameters_file, response_file = map(lambda value: Path(value).resolve(), (conditions, parameters, response))
            if any(not path.is_relative_to(run_dir.resolve()) for path in (conditions_file, parameters_file, response_file)):
                raise ValueError("Runtime adapter returned a file outside its new run.")
            snapshots = {}
            for name, source in (("conditions", conditions_file), ("parameters", parameters_file), ("user_config", user_config_file)):
                for phase in ("initial", "final"):
                    snapshots[f"{name}_{phase}"] = state_dir / f"{name}.{phase}.json"
                copy_snapshot(source, snapshots[f"{name}_initial"])
            payload["files"].update({"conditions_runtime": _relative(run_dir, conditions_file),
                "parameters_runtime": _relative(run_dir, parameters_file), "user_config_runtime": _relative(run_dir, user_config_file),
                "snapshots": {key: _relative(run_dir, value) for key, value in snapshots.items()}})
            payload["status"] = "configured"
            atomic_write_json(manifest_file, payload)
            if simulation is None and presentation is None:
                convenience("workspace", workspace)
            if spec.procedure is not None:
                from ..researcher import RunContext
                procedure_context = RunContext(values, profile, spec, run_dir,
                    synthetic=simulation is not None, data_kind=data_kind,
                    stimulus_snapshots=request.stimulus_snapshots,
                    observer_parameters=simulation.metadata.get("observer_parameters", {}) if simulation is not None else {},
                    seed=simulation.metadata["seed"] if simulation is not None else (0 if spec.historical else __import__("secrets").randbits(64)),
                    observer_probability=simulation.response_probability if simulation is not None else None,
                    test_trial_limit=presentation.trial_limit if presentation is not None else None)
                spec.procedure(procedure_context)
                if procedure_context.status not in {"completed", "max_trials_reached"}:
                    raise ValueError("Procedure returned without complete(); initialise, record all planned responses, then complete, or abort explicitly.")
                payload["status"] = procedure_context.status
            elif simulation is not None:
                simulation.runtime(str(conditions_file), str(parameters_file), str(response_file), str(state_dir))
            else:
                experiment = importlib.import_module(spec.legacy_module)
                experiment.run_experiment(str(conditions_file), str(parameters_file), str(response_file), str(state_dir))
    except BaseException as exc:
        # Preserve interrupts through finalisation without recording success.
        from ..researcher import ParticipantAbort
        from .presentation_testing import PresentationTestComplete
        if isinstance(exc, PresentationTestComplete) and presentation is not None:
            payload["status"] = "test_finished"
            payload["test_stop_reason"] = str(exc)
            procedure_context.status = "test_finished"
            procedure_context._save_lifecycle(str(exc))
        elif isinstance(exc, ParticipantAbort) and not getattr(procedure_context, "_persistence_errors", ()):
            payload["status"] = "aborted_by_user"
            payload["abort_reason"] = str(exc)
            if procedure_context is not None:
                procedure_context.status = "aborted_by_user"
                convenience("procedure_lifecycle", lambda: procedure_context._save_lifecycle(str(exc)))
        else:
            primary_error = exc
            payload["status"] = "error"
            payload["error"] = repr(exc)
            if procedure_context is not None:
                procedure_context.status = "error"
                convenience("procedure_lifecycle", lambda: procedure_context._save_lifecycle(str(exc)))
    finally:
        if procedure_context is not None:
            try:
                procedure_context.close()
            except Exception as exc:
                payload["status"] = "error"
                payload.setdefault("error", "Run finalisation failed: " + repr(exc))
                payload.setdefault("finalisation_errors", []).append({"operation": "trial summaries/display cleanup", "error": repr(exc)})
                if primary_error is not None:
                    primary_error.add_note(f"Run finalisation also failed: {exc!r}")
            if getattr(procedure_context, "_persistence_errors", ()):
                payload["persistence_errors"] = procedure_context._persistence_errors
                payload["status"] = "error"
            if (run_dir / "trial_events.jsonl").exists():
                payload["files"]["trial_events"] = "trial_events.jsonl"
            for name in ("trial_presentations", "adaptive_history", "trial_actions", "primary_thresholds"):
                if (run_dir / (name + ".json")).exists():
                    payload["files"][name] = name + ".json"
        for name, source in (("conditions", conditions_file), ("parameters", parameters_file), ("user_config", user_config_file)):
            try:
                copy_snapshot(source, state_dir / f"{name}.final.json")
            except Exception as exc:
                payload.setdefault("finalisation_errors", []).append({"operation": name + " snapshot", "error": repr(exc)})
                payload["status"] = "error"
        adaptive_path = adaptive_session_file if adaptive_session_file.exists() else response_file.with_suffix(".session.json")
        if adaptive_path.exists():
            try:
                adaptive = json.loads(adaptive_path.read_text(encoding="utf-8"))
                payload["adaptive_session"] = adaptive
                if payload["status"] != "error" and spec.procedure is None: payload["status"] = adaptive.get("status", "returned")
            except Exception as exc:
                payload["adaptive_metadata_error"] = repr(exc)
                payload["status"] = "error"
        elif spec.procedure is not None:
            payload.get("files", {}).pop("adaptive_session", None)
            if (run_dir / "procedure_lifecycle.json").exists():
                payload["files"]["procedure_lifecycle"] = "procedure_lifecycle.json"
        elif payload["status"] != "error":
            payload["status"] = "returned"
            if spec.id != "contrast_sensitivity":
                payload.get("files", {}).pop("adaptive_session", None)
        if runtime_display_file.exists():
            if spec.procedure is not None and (run_dir / "procedure_lifecycle.json").exists():
                payload["files"]["procedure_lifecycle"] = "procedure_lifecycle.json"
            try: payload["runtime_display"] = json.loads(runtime_display_file.read_text(encoding="utf-8"))
            except Exception as exc:
                payload["runtime_display_error"] = repr(exc)
                payload["status"] = "error"
        payload["finished_utc"] = datetime.now(timezone.utc).isoformat()
        if "software" in payload:
            convenience("runtime_dependency_provenance", lambda: payload["software"].update(
                pyglet_runtime=_loaded_graphics_provenance(root)))
        try: payload["accepted_trials"] = _trial_count(trial_log_file)
        except Exception as exc:
            payload["trial_count_error"] = repr(exc)
            payload["accepted_trials"] = 0
            payload["status"] = "error"
        # A successful procedure is not a valid primary result if acquisition
        # finalisation subsequently fails (for example display cleanup).
        primary_path = run_dir / "primary_thresholds.json"
        if payload["status"] == "error" and primary_path.exists():
            from ..analysis.primary import from_run
            resolved_path = run_dir / "resolved_experiment.json"
            resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
            result = from_run(run_dir, resolved["primary_estimator"], resolved["expected_staircases"], "error")
            atomic_write_json(primary_path, result)
            atomic_write_json(resolved_path, resolved | result)
        if trial_log_file.exists():
            convenience("readable_trials", lambda: write_readable_trial_table(trial_log_file, run_dir / READABLE_TRIALS_FILENAME))
        convenience("output_sha256", lambda: payload.update(output_sha256=_run_artifact_fingerprints(run_dir)))
        if payload["status"] == "error" and "error" not in payload:
            payload["error"] = "Acquisition or finalisation reported an error; see recorded diagnostics."
        convenience("runs_index", update_index)
        if simulation is None and presentation is None:
            convenience("workspace", workspace)
        try: atomic_write_json(manifest_file, payload)
        except Exception as exc:
            if primary_error is None: primary_error = exc
            else: primary_error.add_note(f"Final manifest could not be written: {exc!r}")
    if primary_error is not None:
        raise primary_error

    # Post-acquisition figures belong to the SAME run directory for humans
    # and simulations. They are derived AFTER the immutable trial log and
    # final manifest are written, and never affect acquisition success.
    if spec.id == "contrast_sensitivity" and presentation is None and payload.get("accepted_trials", 0) and payload.get("status") != "error":
        from ..analysis.previews import create_staircase_preview
        try:
            create_staircase_preview(data_root=data, run_directory=run_dir)
        except Exception as exc:
            import warnings
            warnings.warn(f"Staircase quick-look unavailable for {run_dir.name}: {exc}", RuntimeWarning)
        # The legacy CSF threshold analyser is valid for this named experiment
        # only; other experiments may have completely different estimators.
        if simulation is None and spec.id == "contrast_sensitivity":
            from ..analysis.thresholds import analyse_thresholds
            try:
                analyse_thresholds(data_root=data, run_directory=run_dir, create_plot=True)
            except ValueError as exc:
                if "No reversal observations" not in str(exc):
                    import warnings
                    warnings.warn(f"Quick-look THC unavailable: {exc}", RuntimeWarning)
            except Exception as exc:
                import warnings
                warnings.warn(f"Quick-look THC unavailable: {exc}", RuntimeWarning)

    adaptive = payload.get("adaptive_session") or {}
    return RunArtifacts(run_directory=run_dir, trial_log_file=trial_log_file, response_file=response_file,
        conditions_file=conditions_file, parameters_file=parameters_file, manifest_file=manifest_file,
        status=payload["status"], accepted_trials=payload["accepted_trials"],
        completed_staircase_ids=tuple(adaptive.get("completed_staircase_ids", ())),
        unfinished_staircase_ids=tuple(adaptive.get("unfinished_staircase_ids", ())))
