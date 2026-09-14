"""Persistent local workspace state and per-run directory ownership."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config.models import SetupRequest
from .session import atomic_write_json

DATA_CONFIG_FILENAME = "psycolab_data_config.json"
LOCAL_PREFERENCES_FILENAME = ".psycolab_local.json"


def data_config_path(data_root: Path) -> Path:
    return data_root / DATA_CONFIG_FILENAME


def load_workspace_state(data_root: Path) -> dict[str, Any] | None:
    path = data_config_path(data_root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not read PsyCoLab data configuration: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"PsyCoLab data configuration must contain a JSON object: {path}")
    return payload


def request_from_workspace_state(state: dict[str, Any] | None) -> SetupRequest | None:
    if not state:
        return None
    raw = state.get("last_request")
    if not isinstance(raw, dict):
        return None
    required = {
        "participant_id",
        "session_mode",
        "experiment_id",
        "monitor_profile_id",
        "experiment_values",
    }
    if not required.issubset(raw):
        return None
    return SetupRequest(
        participant_id=str(raw["participant_id"]),
        session_mode=str(raw.get("session_mode", "reuse")),
        experiment_id=str(raw["experiment_id"]),
        monitor_profile_id=str(raw["monitor_profile_id"]),
        experiment_values=dict(raw["experiment_values"]),
        # The selected data folder is runtime/machine context, not part of a
        # reusable experiment setup. Keeping this None makes a copied data
        # workspace portable to another computer.
        data_root=None,
    )


def create_run_directory(
    data_root: Path,
    *,
    participant_id: str,
    experiment_id: str,
    now: datetime | None = None,
) -> Path:
    """Create one immutable directory that owns every artifact from one run."""
    local_now = now or datetime.now()
    date_text = local_now.strftime("%Y-%m-%d")
    stamp = local_now.strftime("%Y%m%d_%H%M%S")
    base = data_root / participant_id / experiment_id / date_text
    base.mkdir(parents=True, exist_ok=True)

    for _ in range(100):
        run_id = f"run_{stamp}_{uuid4().hex[:8]}"
        run_dir = base / run_id
        try:
            run_dir.mkdir()
            (run_dir / "state").mkdir()
            return run_dir
        except FileExistsError:
            continue
    raise RuntimeError("Could not allocate a unique PsyCoLab run directory.")


def _relative_to_data_root(path: Path | None, data_root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(data_root.resolve()))
    except ValueError:
        return str(path.resolve())


def save_workspace_state(
    data_root: Path,
    request: SetupRequest,
    *,
    status: str,
    run_directory: Path | None = None,
    legacy_setup: dict[str, Any] | None = None,
    manifest_file: Path | None = None,
) -> Path:
    """Store the latest setup at the top of the chosen data folder.

    This is a convenience index, not the canonical scientific record. Every run
    also owns immutable copies of its full configuration inside its run folder.
    """
    data_root.mkdir(parents=True, exist_ok=True)
    previous = load_workspace_state(data_root) or {}
    request_payload = asdict(request)
    # Machine-specific paths are deliberately not persisted in the portable
    # workspace state. .psycolab_local.json remembers the current machine's
    # selected folder separately and is ignored by Git.
    request_payload["data_root"] = None

    payload: dict[str, Any] = {
        "schema_version": 2,
        "project": "PsyCoLab — Psychophysics Collaborative Lab",
        "data_root": ".",
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "last_participant_id": request.participant_id,
        "last_experiment_id": request.experiment_id,
        "last_monitor_profile_id": request.monitor_profile_id,
        "last_experiment_values": dict(request.experiment_values),
        "last_request": request_payload,
        "last_status": status,
        "last_run": {
            "run_directory": _relative_to_data_root(run_directory, data_root),
            "manifest": _relative_to_data_root(manifest_file, data_root),
        },
    }
    if legacy_setup is not None:
        payload["last_legacy_setup"] = legacy_setup
    elif "last_legacy_setup" in previous:
        payload["last_legacy_setup"] = previous["last_legacy_setup"]

    path = data_config_path(data_root)
    atomic_write_json(path, payload)
    return path


def local_preferences_path(repo_root: Path) -> Path:
    return repo_root / LOCAL_PREFERENCES_FILENAME


def preferred_data_root(repo_root: Path, fallback: Path) -> Path:
    """Remember only the last data-folder path in the local checkout.

    The file is ignored by Git and contains no experiment data. An explicit
    PSYCOLAB_DATA_DIR environment variable continues to take precedence.
    """
    if os.environ.get("PSYCOLAB_DATA_DIR"):
        return fallback.resolve()
    path = local_preferences_path(repo_root)
    if not path.exists():
        return fallback.resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("last_data_root")
        if value:
            return Path(value).expanduser().resolve()
    except Exception:
        pass
    return fallback.resolve()


def remember_data_root(repo_root: Path, data_root: Path) -> None:
    atomic_write_json(
        local_preferences_path(repo_root),
        {
            "schema_version": 1,
            "last_data_root": str(data_root.resolve()),
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
