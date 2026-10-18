from __future__ import annotations

import json
from pathlib import Path
import shutil
import os
import tempfile
from typing import Any


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, indent=2, default=str, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=path.name+".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def append_json_record(path: Path, payload: dict[str, Any]) -> None:
    """Append one durable journal record; never rewrite preceding trials.

    Called only at a completed/interrupted trial boundary, outside presentation.
    A process interrupted during this write may leave an incomplete final line.
    """
    encoded = json.dumps(payload, default=str, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def read_json_records(path: Path):
    """Yield complete journal records; reject rather than hide a truncated tail.

    Earlier newline-terminated records remain independently readable after an
    interrupted write. Recovery must explicitly report an incomplete final line.
    """
    with path.open("rb") as handle:
        for number, line in enumerate(handle, 1):
            if not line.endswith(b"\n"):
                raise ValueError(f"Incomplete final journal record at line {number}.")
            payload = json.loads(line.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"Journal record {number} must be an object.")
            yield payload


def copy_snapshot(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def response_owned_path(response_file: Path, suffix: str) -> Path:
    """Return a file next to the response file, uniquely tied to that run."""
    return response_file.with_name(f"{response_file.stem}{suffix}")
