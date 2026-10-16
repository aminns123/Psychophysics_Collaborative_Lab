"""Fail-closed separation between synthetic pipeline runs and human acquisition."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Callable

# Per-participant marker. The shared data-root itself is never marked synthetic:
# humans and virtual participants use the same external repository and index.
MARKER = ".psycolab_virtual_participant.json"
MARKER_CONTENT = {"schema_version": 1, "data_kind": "synthetic", "human_acquisition_allowed": False}
LEGACY_ROOT_MARKER = ".psycolab_synthetic.json"

# Fixed virtual origin for synthetic accepted-response events. Not an acquisition clock.
SYNTHETIC_CLOCK_EPOCH_UTC = datetime(2000, 1, 1, tzinfo=timezone.utc)


def synthetic_recorded_utc(event_time_s: float) -> str:
    """Translate virtual event seconds to stable ISO UTC for synthetic records.

    This helper is opt-in only: the human trial recorder must continue using
    actual wall-clock timestamps. These values must be labeled synthetic in
    the manifest, trial context and data dictionary.
    """
    if isinstance(event_time_s, bool):
        raise ValueError("Synthetic event time must be finite and nonnegative.")
    seconds = float(event_time_s)
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Synthetic event time must be finite and nonnegative.")
    return (SYNTHETIC_CLOCK_EPOCH_UTC + timedelta(seconds=seconds)).isoformat()



def is_synthetic_path(path: Path) -> bool:
    """Identify the historic dedicated simulation root (for safe migration)."""
    resolved = Path(path).resolve()
    return any((ancestor / LEGACY_ROOT_MARKER).exists() for ancestor in (resolved, *resolved.parents))


def simulation_workspace(path: Path, repo_root: Path) -> Path:
    """Validate the SHARED external data repository, without writing anything.

    The same root is used for human and synthetic runs. Synthetic provenance is
    attached to individual virtual participants/runs, never to this root.
    """
    from ..paths import resolve_data_root
    from ..config.local import config_root

    raw = Path(path).expanduser().absolute()
    if raw != raw.resolve() or any(part.is_symlink() for part in (raw, *raw.parents)):
        raise ValueError("Data root cannot use symlinks or redirected paths.")
    # Dedicated USER_env roots are tagged software-only. Normal human preflight
    # must reject them, while virtual participants are permitted explicitly.
    root = resolve_data_root(raw, repo_root, allow_synthetic=True)
    config_root(repo_root, root)
    if root.exists() and not root.is_dir():
        raise ValueError("The PsyCoLab data repository must be a directory.")
    return root


def register_virtual_participant(data_root: Path, participant_id: str) -> Path:
    """Reserve a synthetic participant ID inside the shared data hierarchy.

    Refuse pre-existing unmarked participant folders rather than risk mixing
    records. Lock protects simultaneous simulator processes on local disks.
    """
    from ..data.identifiers import validate_path_component
    from ..data.locking import file_lock

    identity = validate_path_component(participant_id, label="virtual participant")
    if not identity.startswith("synthetic_"):
        raise ValueError("Virtual participant IDs must start with synthetic_.")
    data_root.mkdir(parents=True, exist_ok=True)
    participant_dir = data_root / identity
    if participant_dir.is_symlink():
        raise ValueError("Virtual participant folder cannot be a symlink.")
    marker = participant_dir / MARKER
    with file_lock(data_root / ".psycolab_virtual_participants.lock"):
        if participant_dir.exists():
            if not participant_dir.is_dir() or not marker.is_file() or marker.is_symlink():
                raise ValueError("Existing participant folder is not marked synthetic; refusing to mix data.")
            try:
                content = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ValueError("Invalid virtual participant marker.") from exc
            if content != MARKER_CONTENT:
                raise ValueError("Virtual participant marker has unexpected content.")
        else:
            participant_dir.mkdir()
            with marker.open("x", encoding="utf-8") as stream:
                json.dump(MARKER_CONTENT, stream)
    return participant_dir


@dataclass(frozen=True)
class SimulationRun:
    workspace: Path
    metadata: dict
    runtime: Callable

    def validate(self, data: Path, repo_root: Path, request):
        if data.resolve() != simulation_workspace(self.workspace, repo_root):
            raise ValueError("Synthetic output must stay in the selected external data repository.")
        if not request.participant_id.startswith("synthetic_"):
            raise ValueError("Virtual participant IDs must start with synthetic_.")
        if not callable(self.runtime) or self.metadata.get("seed") is None:
            raise ValueError("Synthetic acquisition needs a seeded observer and headless runtime.")
        register_virtual_participant(data, request.participant_id)
