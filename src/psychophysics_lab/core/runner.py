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
from ..config.monitor import load_monitor_profiles
from ..data.index import upsert_run_index
from ..data.participants import validate_participant_id
from ..data.session import atomic_write_json, copy_snapshot
from ..data.trials import (
    TRIAL_DATA_DICTIONARY_FILENAME,
    TRIAL_SCHEMA_VERSION,
    write_trial_data_dictionary,
)
from ..data.workspace import (
    DATA_LAYOUT_SCHEMA_VERSION,
    create_run_directory,
    run_number_from_path,
    save_workspace_state,
)
from ..experiments.registry import get_experiment
from ..paths import default_data_root, find_repo_root, resolve_data_root


@dataclass(frozen=True)
class RunArtifacts:
    run_directory: Path
    trial_log_file: Path
    response_file: Path
    conditions_file: Path
    parameters_file: Path
    manifest_file: Path


@contextmanager
def _legacy_runtime_context(repo_root: Path) -> Iterator[None]:
    """Make legacy root imports and packages.zip resolution deterministic."""
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
    relative_paths = (
        "Experiments/contrast_sensitivity_function.py",
        "Events/adaptive_session.py",
        "Events/adaptiveMethods.py",
        "Events/display_contrast.py",
        "Events/staircase.py",
        "Events/stimuliC.py",
        "Interface/config.py",
        "Functions/functionsForUse.py",
        "libC.py",
        "packages.zip",
        "src/psychophysics_lab/core/runner.py",
        "src/psychophysics_lab/experiments/spec.py",
        "src/psychophysics_lab/experiments/contrast_sensitivity.py",
        "src/psychophysics_lab/config/models.py",
        "src/psychophysics_lab/config/monitor.py",
        "src/psychophysics_lab/data/index.py",
        "src/psychophysics_lab/data/trials.py",
        "src/psychophysics_lab/data/workspace.py",
    )
    fingerprints: dict[str, str] = {}
    for relative in relative_paths:
        path = repo_root / relative
        if path.is_file():
            fingerprints[relative] = _sha256(path)
    return fingerprints


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
                str(profile.get("calibration_status", "")).strip().lower() == "verified"
                and bool(profile.get("luminance_calibration"))
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
    request: SetupRequest,
    *,
    repo_root: Path | None = None,
    data_root: Path | None = None,
) -> RunArtifacts:
    """Configure and run one experiment in one self-contained run directory."""
    root = (repo_root or find_repo_root()).resolve()
    if data_root is not None:
        data_candidate = data_root
    elif request.data_root:
        data_candidate = Path(request.data_root).expanduser()
    else:
        data_candidate = default_data_root(root)
    data = resolve_data_root(data_candidate, root)
    data.mkdir(parents=True, exist_ok=True)

    participant_id = validate_participant_id(request.participant_id)

    spec = get_experiment(request.experiment_id)
    profiles = load_monitor_profiles(root)
    try:
        profile = profiles[request.monitor_profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown monitor profile: {request.monitor_profile_id}") from exc

    if spec.compatible_monitor_profiles and profile.id not in spec.compatible_monitor_profiles:
        raise ValueError(
            f"{spec.display_name} is not yet validated for monitor profile {profile.display_name!r}. "
            "Add/validate the display adapter before collecting data."
        )

    values = spec.normalise_values(request.experiment_values)
    grouping_parts = spec.data_path_parts(values, profile)
    setup = spec.build_legacy_setup(
        participant_id=participant_id,
        values=values,
        monitor_profile=profile,
    )

    local_started = datetime.now().astimezone()
    run_dir = create_run_directory(
        data,
        participant_id=participant_id,
        experiment_id=request.experiment_id,
        monitor_profile_id=profile.id,
        grouping_parts=grouping_parts,
        now=local_started,
    )
    run_uuid = str(uuid4())

    state_dir = run_dir / "state"
    manifest_file = run_dir / "manifest.json"
    experiment_config_file = run_dir / "experiment_config.json"
    monitor_profile_file = run_dir / "monitor_profile.json"
    trial_log_file = run_dir / "trials.tsv"
    trial_dictionary_file = run_dir / TRIAL_DATA_DICTIONARY_FILENAME
    runtime_display_file = run_dir / "runtime_display.json"
    adaptive_session_file = run_dir / "adaptive_session.json"

    atomic_write_json(
        experiment_config_file,
        {
            "schema_version": 2,
            "request": _portable_request_payload(request),
            "normalised_experiment_values": values,
            "legacy_setup": setup,
        },
    )
    atomic_write_json(monitor_profile_file, profile.to_dict())
    write_trial_data_dictionary(
        trial_dictionary_file,
        experiment_id=spec.id,
        overrides=spec.trial_column_overrides,
    )

    payload = _manifest_payload(
        request=request,
        setup=setup,
        profile=profile.to_dict(),
        run_dir=run_dir,
        data_root=data,
        repo_root=root,
        grouping_parts=grouping_parts,
        run_uuid=run_uuid,
        status="configuring",
    )
    started_utc = payload["created_utc"]
    payload["trial_schema_version"] = TRIAL_SCHEMA_VERSION
    payload["files"] = {
        "manifest": "manifest.json",
        "experiment_config": "experiment_config.json",
        "monitor_profile": "monitor_profile.json",
        "canonical_trials": "trials.tsv",
        "trial_data_dictionary": TRIAL_DATA_DICTIONARY_FILENAME,
        "runtime_display": "runtime_display.json",
        "resolved_experiment": "resolved_experiment.json",
        "adaptive_session": "adaptive_session.json",
        "legacy_response": "legacy_response.txt",
        "state_directory": "state/",
    }
    atomic_write_json(manifest_file, payload)

    save_workspace_state(
        data,
        request,
        status="configuring",
        run_directory=run_dir,
        legacy_setup=setup,
        manifest_file=manifest_file,
    )
    try:
        upsert_run_index(
            data,
            _index_row(
                run_uuid=run_uuid,
                request=request,
                grouping_parts=grouping_parts,
                run_dir=run_dir,
                data_root=data,
                status="configuring",
                started_utc=started_utc,
            ),
        )
    except Exception as index_error:
        payload["runs_index_error"] = repr(index_error)
        atomic_write_json(manifest_file, payload)

    conditions_file = state_dir / "conditions.runtime.json"
    parameters_file = state_dir / "parameters.runtime.json"
    response_file = run_dir / "legacy_response.txt"
    user_config_file = state_dir / "user_experiment_config.json"

    try:
        with _legacy_runtime_context(root):
            from Interface.config import run_configure_experiment

            conditions, parameters, response = run_configure_experiment(
                request.participant_id,
                str(data),
                setup,
                run_directory=str(run_dir),
            )
            conditions_file = Path(conditions).resolve()
            parameters_file = Path(parameters).resolve()
            response_file = Path(response).resolve()

            snapshots = {
                "conditions_initial": state_dir / "conditions.initial.json",
                "parameters_initial": state_dir / "parameters.initial.json",
                "user_config_initial": state_dir / "user_config.initial.json",
                "conditions_final": state_dir / "conditions.final.json",
                "parameters_final": state_dir / "parameters.final.json",
                "user_config_final": state_dir / "user_config.final.json",
            }
            copy_snapshot(conditions_file, snapshots["conditions_initial"])
            copy_snapshot(parameters_file, snapshots["parameters_initial"])
            copy_snapshot(user_config_file, snapshots["user_config_initial"])

            payload["status"] = "configured"
            payload["files"].update(
                {
                    "conditions_runtime": _relative(run_dir, conditions_file),
                    "parameters_runtime": _relative(run_dir, parameters_file),
                    "user_config_runtime": _relative(run_dir, user_config_file),
                    "snapshots": {
                        key: _relative(run_dir, value) for key, value in snapshots.items()
                    },
                }
            )
            atomic_write_json(manifest_file, payload)
            save_workspace_state(
                data,
                request,
                status="configured",
                run_directory=run_dir,
                legacy_setup=setup,
                manifest_file=manifest_file,
            )

            experiment = importlib.import_module(spec.legacy_module)
            experiment.run_experiment(
                str(conditions_file),
                str(parameters_file),
                str(response_file),
                str(state_dir),
            )

    except Exception as exc:
        payload["status"] = "error"
        payload["error"] = repr(exc)
        raise
    finally:
        if conditions_file.exists():
            copy_snapshot(conditions_file, state_dir / "conditions.final.json")
        if parameters_file.exists():
            copy_snapshot(parameters_file, state_dir / "parameters.final.json")
        if user_config_file.exists():
            copy_snapshot(user_config_file, state_dir / "user_config.final.json")

        adaptive_metadata = adaptive_session_file
        # Defensive compatibility with a partially migrated run.
        legacy_adaptive_metadata = response_file.with_suffix(".session.json")
        if not adaptive_metadata.exists() and legacy_adaptive_metadata.exists():
            adaptive_metadata = legacy_adaptive_metadata

        if adaptive_metadata.exists():
            try:
                adaptive = json.loads(adaptive_metadata.read_text(encoding="utf-8"))
                payload["adaptive_session"] = adaptive
                if payload.get("status") != "error":
                    payload["status"] = adaptive.get("status", "returned")
            except Exception as metadata_error:
                payload["adaptive_metadata_error"] = repr(metadata_error)
        elif payload.get("status") != "error":
            payload["status"] = "returned"

        if runtime_display_file.exists():
            try:
                payload["runtime_display"] = json.loads(
                    runtime_display_file.read_text(encoding="utf-8")
                )
            except Exception as display_error:
                payload["runtime_display_error"] = repr(display_error)

        finished_utc = datetime.now(timezone.utc).isoformat()
        payload["finished_utc"] = finished_utc
        payload["accepted_trials"] = _trial_count(trial_log_file)

        try:
            payload["output_sha256"] = _run_artifact_fingerprints(run_dir)
        except Exception as hash_error:
            payload["output_sha256_error"] = repr(hash_error)

        try:
            upsert_run_index(
                data,
                _index_row(
                    run_uuid=run_uuid,
                    request=request,
                    grouping_parts=grouping_parts,
                    run_dir=run_dir,
                    data_root=data,
                    status=str(payload.get("status", "returned")),
                    accepted_trials=payload["accepted_trials"],
                    started_utc=started_utc,
                    finished_utc=finished_utc,
                ),
            )
        except Exception as index_error:
            payload["runs_index_error"] = repr(index_error)

        atomic_write_json(manifest_file, payload)
        save_workspace_state(
            data,
            request,
            status=str(payload.get("status", "returned")),
            run_directory=run_dir,
            legacy_setup=setup,
            manifest_file=manifest_file,
        )

    return RunArtifacts(
        run_directory=run_dir,
        trial_log_file=trial_log_file,
        response_file=response_file,
        conditions_file=conditions_file,
        parameters_file=parameters_file,
        manifest_file=manifest_file,
    )
