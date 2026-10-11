"""Fail-closed separation between synthetic pipeline runs and human acquisition."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Callable

MARKER = ".psycolab_synthetic.json"
MARKER_CONTENT = {"schema_version": 1, "data_kind": "synthetic", "human_acquisition_allowed": False}

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
    return any((p / MARKER).exists() for p in (path.resolve(), *path.resolve().parents))


def simulation_workspace(path: Path, repo_root: Path) -> Path:
    """Create only a new dedicated directory, or reuse our marked directory.

    Never adopt a nonempty unmarked folder. Reject repository/config/data overlap
    and links before writing. A human runner rejects this marker and descendants.
    """
    from ..config.local import config_root
    root = Path(path).expanduser().absolute()
    if root != root.resolve() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("Synthetic workspace cannot use symlinks or redirected paths.")
    if root.name != "psycolab_simulations":
        raise ValueError("The isolated test root must be named psycolab_simulations.")
    for protected in (repo_root.resolve(), config_root(repo_root).resolve()):
        if root == protected or root.is_relative_to(protected) or protected.is_relative_to(root):
            raise ValueError("Synthetic test root must be separate from source and configuration.")
    for parent in root.parents:
        if any((parent / name).exists() for name in (MARKER, "psycolab_data_config.json", "runs_index.csv", "manifest.json")):
            raise ValueError("Synthetic workspace cannot be nested inside an acquisition workspace.")
    marker = root / MARKER
    if root.exists():
        if not marker.is_file() or marker.is_symlink():
            raise ValueError("Refusing an existing unmarked directory; choose a new isolated test root.")
        if json.loads(marker.read_text(encoding="utf-8")) != MARKER_CONTENT:
            raise ValueError("Invalid synthetic workspace marker.")
    else:
        root.mkdir(parents=True, exist_ok=False)
        with marker.open("x", encoding="utf-8") as stream:
            json.dump(MARKER_CONTENT, stream)
    return root


@dataclass(frozen=True)
class SimulationRun:
    workspace: Path
    metadata: dict
    runtime: Callable

    def validate(self, data: Path, repo_root: Path, request):
        if data.resolve() != simulation_workspace(self.workspace, repo_root):
            raise ValueError("Synthetic output must stay in the marked isolated test root.")
        if not request.participant_id.startswith("synthetic_"):
            raise ValueError("Virtual participant IDs must start with synthetic_.")
        if not callable(self.runtime) or self.metadata.get("seed") is None:
            raise ValueError("Synthetic acquisition needs a seeded observer and headless runtime.")
