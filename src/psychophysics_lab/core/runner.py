from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Iterator

from ..config.models import SetupRequest
from ..config.monitor import load_monitor_profiles
from ..data.participants import participant_directory, validate_participant_id
from ..data.session import atomic_write_json, copy_snapshot, response_owned_path
from ..experiments.registry import get_experiment
from ..paths import default_data_root, find_repo_root


@dataclass(frozen=True)
class RunArtifacts:
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


def _session_manifest_payload(
    *,
    request: SetupRequest,
    setup: dict,
    response_file: Path,
    conditions_file: Path,
    parameters_file: Path,
    repo_root: Path,
    status: str,
) -> dict:
    return {
        "schema_version": 1,
        "project": "PsyCoLab — Psychophysics Collaborative Lab",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "participant_id": request.participant_id,
        "session_mode": request.session_mode,
        "experiment_id": request.experiment_id,
        "monitor_profile_id": request.monitor_profile_id,
        "experiment_values": request.experiment_values,
        "legacy_setup": setup,
        "files": {
            "response": str(response_file),
            "conditions_runtime": str(conditions_file),
            "parameters_runtime": str(parameters_file),
        },
        "repository_root": str(repo_root),
    }


def run_request(
    request: SetupRequest,
    *,
    repo_root: Path | None = None,
    data_root: Path | None = None,
) -> RunArtifacts:
    """Configure and run one experiment.

    Textual has already exited before this function imports Pyglet or any legacy
    experiment module.
    """
    root = (repo_root or find_repo_root()).resolve()
    data = (data_root or default_data_root(root)).resolve()
    data.mkdir(parents=True, exist_ok=True)

    participant_id = validate_participant_id(request.participant_id)
    participant_dir = participant_directory(data, participant_id, create=True)

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

    setup = spec.build_legacy_setup(
        participant_id=participant_id,
        values=request.experiment_values,
        monitor_profile=profile,
    )

    legacy_setup_file = participant_dir / "experiment_defined.json"
    atomic_write_json(legacy_setup_file, setup)

    with _legacy_runtime_context(root):
        # Delayed imports are intentional: Textual must be fully closed before
        # Pyglet/OpenGL modules are imported.
        from Interface.config import run_configure_experiment

        conditions, parameters, response = run_configure_experiment(
            participant_id,
            str(data),
            setup,
        )

        conditions_file = Path(conditions).resolve()
        parameters_file = Path(parameters).resolve()
        response_file = Path(response).resolve()

        manifest_file = response_owned_path(response_file, ".psycolab.json")
        initial_conditions = response_owned_path(response_file, ".conditions.initial.json")
        initial_parameters = response_owned_path(response_file, ".parameters.initial.json")
        initial_user_config = response_owned_path(response_file, ".user_config.initial.json")
        final_conditions = response_owned_path(response_file, ".conditions.final.json")
        final_parameters = response_owned_path(response_file, ".parameters.final.json")
        final_user_config = response_owned_path(response_file, ".user_config.final.json")

        copy_snapshot(conditions_file, initial_conditions)
        copy_snapshot(parameters_file, initial_parameters)
        copy_snapshot(data / "user_experiment_config.json", initial_user_config)

        payload = _session_manifest_payload(
            request=request,
            setup=setup,
            response_file=response_file,
            conditions_file=conditions_file,
            parameters_file=parameters_file,
            repo_root=root,
            status="configured",
        )
        payload["snapshots"] = {
            "conditions_initial": str(initial_conditions),
            "parameters_initial": str(initial_parameters),
            "user_config_initial": str(initial_user_config),
            "conditions_final": str(final_conditions),
            "parameters_final": str(final_parameters),
            "user_config_final": str(final_user_config),
        }
        atomic_write_json(manifest_file, payload)

        experiment = importlib.import_module(spec.legacy_module)
        try:
            experiment.run_experiment(
                str(conditions_file),
                str(parameters_file),
                str(response_file),
                str(data),
            )
        except Exception as exc:
            payload["status"] = "error"
            payload["error"] = repr(exc)
            raise
        finally:
            copy_snapshot(conditions_file, final_conditions)
            copy_snapshot(parameters_file, final_parameters)
            copy_snapshot(data / "user_experiment_config.json", final_user_config)

            adaptive_metadata = response_file.with_suffix(".session.json")
            if adaptive_metadata.exists():
                try:
                    adaptive = json.loads(adaptive_metadata.read_text(encoding="utf-8"))
                    payload["adaptive_session"] = adaptive
                    payload["status"] = adaptive.get("status", payload.get("status", "returned"))
                except Exception as metadata_error:
                    payload["adaptive_metadata_error"] = repr(metadata_error)
            elif payload.get("status") != "error":
                payload["status"] = "returned"

            payload["finished_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_write_json(manifest_file, payload)

    return RunArtifacts(
        response_file=response_file,
        conditions_file=conditions_file,
        parameters_file=parameters_file,
        manifest_file=manifest_file,
    )
