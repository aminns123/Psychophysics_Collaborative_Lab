"""Append-only canonical trial records for PsyCoLab experiments."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Mapping


TRIAL_COLUMNS = (
    "trial_index",
    "recorded_utc",
    "event_time_s",
    "staircase_id",
    "staircase_trial_index",
    "stimulus_condition",
    "stimulus_position_px",
    "target_alternative",
    "participant_response",
    "response_key",
    "correct",
    "presented_display_contrast",
    "presented_screen_intensity",
    "step",
    "reversal",
    "reversal_count",
    "next_display_contrast",
    "next_screen_intensity",
    "staircase_complete",
    "run_status",
)


class TrialLog:
    """Append one durable TSV row per accepted participant response."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            with self.path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=TRIAL_COLUMNS, delimiter="\t")
                writer.writeheader()
                handle.flush()
                os.fsync(handle.fileno())

    def append(self, row: Mapping[str, Any]) -> None:
        unknown = set(row) - set(TRIAL_COLUMNS)
        if unknown:
            raise ValueError(f"Unknown trial-log columns: {sorted(unknown)}")
        payload = {column: row.get(column, "") for column in TRIAL_COLUMNS}
        payload["recorded_utc"] = payload["recorded_utc"] or datetime.now(timezone.utc).isoformat()
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRIAL_COLUMNS, delimiter="\t")
            writer.writerow(payload)
            handle.flush()
            os.fsync(handle.fileno())
