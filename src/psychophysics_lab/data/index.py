"""Human-readable top-level index of PsyCoLab acquisition runs.

``runs_index.csv`` is a convenience catalogue. The canonical scientific record
remains the self-contained run directory and its manifest/trials files.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

from .workspace import RUNS_INDEX_FILENAME

RUN_INDEX_FIELDS = (
    "run_uuid",
    "participant_id",
    "experiment_id",
    "monitor_profile_id",
    "condition_path",
    "date",
    "run_number",
    "status",
    "accepted_trials",
    "relative_path",
    "started_utc",
    "finished_utc",
)


def runs_index_path(data_root: Path) -> Path:
    return data_root / RUNS_INDEX_FILENAME


def upsert_run_index(data_root: Path, row: dict[str, Any]) -> Path:
    """Insert/update one run row atomically, keyed by ``run_uuid``."""
    data_root.mkdir(parents=True, exist_ok=True)
    path = runs_index_path(data_root)

    normalized = {field: row.get(field, "") for field in RUN_INDEX_FIELDS}
    if not str(normalized["run_uuid"]).strip():
        raise ValueError("runs_index row requires a run_uuid.")

    rows: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(RUN_INDEX_FIELDS):
                raise ValueError(
                    f"Unexpected {RUNS_INDEX_FILENAME} header. "
                    "Refusing to rewrite an unknown index format."
                )
            rows = [dict(item) for item in reader]

    replaced = False
    run_uuid = str(normalized["run_uuid"])
    for index, existing in enumerate(rows):
        if existing.get("run_uuid") == run_uuid:
            rows[index] = {key: str(value) for key, value in normalized.items()}
            replaced = True
            break
    if not replaced:
        rows.append({key: str(value) for key, value in normalized.items()})

    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return path
