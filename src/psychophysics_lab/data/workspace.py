"""Persistent workspace state and the PsyCoLab acquisition-data layout."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

from ..config.models import SetupRequest
from .session import atomic_write_json

DATA_CONFIG_FILENAME = "psycolab_data_config.json"
RUNS_INDEX_FILENAME = "runs_index.csv"
LOCAL_PREFERENCES_FILENAME = ".psycolab_local.json"
DATA_LAYOUT_SCHEMA_VERSION = 1

_RUN_RE = re.compile(r"^run_(\d+)$")


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
        # The selected data folder is machine-local context, not part of a
        # portable reusable experiment setup.
        data_root=None,
    )


def _safe_component(value: str, *, label: str) -> str:
    """Validate one human-readable folder component.

    Experiment definitions may choose grouping labels, but they may not inject
    path separators or traversal tokens into the acquisition hierarchy.
    """
    text = str(value).strip()
    if not text:
        raise ValueError(f"{label} folder component must not be empty.")
    if text in {".", ".."}:
        raise ValueError(f"{label} folder component is not valid: {text!r}")
    if "/" in text or "\\" in text:
        raise ValueError(f"{label} folder component must not contain path separators: {text!r}")
    if any(ord(char) < 32 for char in text):
        raise ValueError(f"{label} folder component contains a control character.")
    return text


def create_run_directory(
    data_root: Path,
    *,
    participant_id: str,
    experiment_id: str,
    monitor_profile_id: str,
    grouping_parts: Iterable[str] = (),
    now: datetime | None = None,
) -> Path:
    """Create one run directory using the stable PsyCoLab human-facing hierarchy.

    Layout contract v1:

        participant /
        experiment /
        display profile /
        experiment-defined run-level grouping folders /
        YYYY-MM-DD /
        run_NNN /

    Dates therefore occur only *after* the scientifically useful grouping
    levels, avoiding a top-level forest of date folders. ``run_NNN`` is for
    human navigation; a separate UUID is stored in manifest.json.
    """
    local_now = now or datetime.now()
    date_text = local_now.strftime("%Y-%m-%d")

    components = [
        _safe_component(participant_id, label="participant"),
        _safe_component(experiment_id, label="experiment"),
        _safe_component(monitor_profile_id, label="monitor profile"),
        *[
            _safe_component(part, label="experiment grouping")
            for part in grouping_parts
        ],
        date_text,
    ]
    base = data_root.joinpath(*components)
    base.mkdir(parents=True, exist_ok=True)

    existing_numbers: list[int] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        match = _RUN_RE.fullmatch(child.name)
        if match:
            existing_numbers.append(int(match.group(1)))

    candidate = max(existing_numbers, default=0) + 1
    # mkdir is the final authority, so two simultaneous processes cannot be
    # assigned the same run folder merely because they scanned at the same time.
    for _ in range(10_000):
        run_dir = base / f"run_{candidate:03d}"
        try:
            run_dir.mkdir()
            (run_dir / "state").mkdir()
            return run_dir
        except FileExistsError:
            candidate += 1

    raise RuntimeError("Could not allocate a unique PsyCoLab run number.")


def run_number_from_path(run_directory: Path) -> int:
    match = _RUN_RE.fullmatch(run_directory.name)
    if not match:
        raise ValueError(f"Not a PsyCoLab run_NNN directory: {run_directory}")
    return int(match.group(1))


def _relative_to_data_root(path: Path | None, data_root: Path) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(data_root.resolve()).as_posix()
    except ValueError:
        # Canonical data files should be inside data_root. Returning an absolute
        # path here is retained only as a defensive fallback for legacy callers.
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
    """Store the latest setup at the top of the chosen data workspace.

    This is convenience state, not the canonical scientific record. Every run
    owns immutable copies of its configuration inside its own run directory.
    """
    data_root.mkdir(parents=True, exist_ok=True)
    previous = load_workspace_state(data_root) or {}
    request_payload = asdict(request)
    request_payload["data_root"] = None

    payload: dict[str, Any] = {
        "schema_version": 3,
        "data_layout_schema_version": DATA_LAYOUT_SCHEMA_VERSION,
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
    """Remember only the last data-folder path in the local checkout."""
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
