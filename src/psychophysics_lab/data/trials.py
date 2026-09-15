"""Append-only canonical trial records and their data dictionary."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Mapping


TRIAL_SCHEMA_VERSION = 1
TRIAL_DATA_DICTIONARY_FILENAME = "trial_data_dictionary.tsv"


@dataclass(frozen=True)
class TrialColumnDefinition:
    """Human-readable definition of one canonical ``trials.tsv`` column."""

    logical_type: str
    units_or_encoding: str
    meaning: str
    notes: str = ""


TRIAL_COLUMN_DEFINITIONS: dict[str, TrialColumnDefinition] = {
    "trial_index": TrialColumnDefinition(
        "integer",
        "1-based index",
        "Accepted-response number across the whole run.",
        "Counts accepted participant responses, not fixation/stimulus phases.",
    ),
    "recorded_utc": TrialColumnDefinition(
        "ISO 8601 datetime",
        "UTC",
        "UTC timestamp at which this canonical row was written to disk.",
    ),
    "event_time_s": TrialColumnDefinition(
        "float",
        "seconds",
        "Runtime event time supplied by the experiment engine for the accepted response.",
        "This is an experiment/runtime clock value, not a replacement for recorded_utc.",
    ),
    "staircase_id": TrialColumnDefinition(
        "integer",
        "experiment-defined staircase identifier",
        "Identity of the adaptive staircase active for this response.",
        "May be blank/not applicable for future non-adaptive experiments.",
    ),
    "staircase_trial_index": TrialColumnDefinition(
        "integer",
        "1-based within staircase",
        "Accepted-response count within the active staircase after this response.",
        "May be blank/not applicable for future non-adaptive experiments.",
    ),
    "stimulus_condition": TrialColumnDefinition(
        "number or text",
        "experiment-defined",
        "Experiment-specific stimulus condition associated with the accepted response.",
        "Interpret using the experiment-specific notes in this dictionary and resolved_experiment.json.",
    ),
    "stimulus_position_px": TrialColumnDefinition(
        "number or text",
        "pixels; experiment-defined coordinate",
        "Experiment-specific stimulus position recorded for the accepted response.",
        "Interpret using the experiment-specific notes in this dictionary and resolved_experiment.json.",
    ),
    "target_alternative": TrialColumnDefinition(
        "integer or text",
        "experiment-defined response code",
        "Correct/target alternative for the accepted response.",
        "The experiment-specific encoding is stated in this dictionary.",
    ),
    "participant_response": TrialColumnDefinition(
        "integer or text",
        "experiment-defined response code",
        "Participant's encoded response for this accepted response.",
        "The experiment-specific encoding is stated in this dictionary.",
    ),
    "response_key": TrialColumnDefinition(
        "text",
        "keyboard/input label",
        "Actual accepted input key or response label recorded by the experiment.",
    ),
    "correct": TrialColumnDefinition(
        "integer",
        "0 = incorrect; 1 = correct",
        "Whether participant_response matched target_alternative.",
    ),
    "presented_display_contrast": TrialColumnDefinition(
        "float",
        "dimensionless C_disp",
        "Normalised display contrast actually presented for this accepted response.",
        "C_disp = (I_n - I_b) / (I_M - I_b). This is not conventional Weber contrast.",
    ),
    "presented_screen_intensity": TrialColumnDefinition(
        "float",
        "normalised digital display command",
        "Digital screen intensity actually presented for this accepted response.",
        "For the current renderer this is a normalised command value; physical luminance interpretation requires a verified monitor calibration.",
    ),
    "step": TrialColumnDefinition(
        "text enum",
        "hold | down | up",
        "Adaptive staircase decision produced by this response.",
        "May be blank/not applicable for future non-adaptive experiments.",
    ),
    "reversal": TrialColumnDefinition(
        "integer",
        "0 = no; 1 = yes",
        "Whether this accepted response created a staircase direction reversal.",
        "May be blank/not applicable for future non-adaptive experiments.",
    ),
    "reversal_count": TrialColumnDefinition(
        "integer",
        "count after this response",
        "Cumulative reversal count for the active staircase after this response.",
        "May be blank/not applicable for future non-adaptive experiments.",
    ),
    "next_display_contrast": TrialColumnDefinition(
        "float",
        "dimensionless C_disp",
        "Post-response display contrast calculated for the next use of this staircase.",
        "This is not what was shown on the current trial. Use presented_display_contrast for the stimulus the participant actually saw.",
    ),
    "next_screen_intensity": TrialColumnDefinition(
        "float",
        "normalised digital display command",
        "Post-response digital intensity calculated for the next use of this staircase.",
        "This is not what was shown on the current trial. Use presented_screen_intensity for the stimulus the participant actually saw.",
    ),
    "staircase_complete": TrialColumnDefinition(
        "integer",
        "0 = not complete; 1 = complete",
        "Whether the active staircase had met its configured completion criterion after this response.",
        "May be blank/not applicable for future non-adaptive experiments.",
    ),
    "run_status": TrialColumnDefinition(
        "text enum",
        "adaptive-run status",
        "Adaptive/run status immediately after this accepted response.",
        "Examples include running, completed and max_trials_reached.",
    ),
}

TRIAL_COLUMNS = tuple(TRIAL_COLUMN_DEFINITIONS)


def _merged_definition(
    column: str,
    overrides: Mapping[str, Mapping[str, str]] | None,
) -> TrialColumnDefinition:
    base = asdict(TRIAL_COLUMN_DEFINITIONS[column])
    if overrides and column in overrides:
        unknown = set(overrides[column]) - set(base)
        if unknown:
            raise ValueError(
                f"Unknown trial data-dictionary fields for {column!r}: {sorted(unknown)}"
            )
        base.update({key: str(value) for key, value in overrides[column].items()})
    return TrialColumnDefinition(**base)


def write_trial_data_dictionary(
    path: str | Path,
    *,
    experiment_id: str,
    overrides: Mapping[str, Mapping[str, str]] | None = None,
) -> Path:
    """Write the exact human-readable dictionary for a run's ``trials.tsv``.

    The file is created in every run directory before the experiment launches so
    the acquired data remain interpretable even when copied away from the code
    repository.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if overrides:
        unknown_columns = set(overrides) - set(TRIAL_COLUMNS)
        if unknown_columns:
            raise ValueError(
                "Trial data-dictionary overrides reference unknown columns: "
                f"{sorted(unknown_columns)}"
            )

    fields = (
        "trial_schema_version",
        "experiment_id",
        "column_order",
        "column_name",
        "logical_type",
        "units_or_encoding",
        "meaning",
        "notes",
    )
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for order, column in enumerate(TRIAL_COLUMNS, start=1):
            definition = _merged_definition(column, overrides)
            writer.writerow(
                {
                    "trial_schema_version": TRIAL_SCHEMA_VERSION,
                    "experiment_id": experiment_id,
                    "column_order": order,
                    "column_name": column,
                    **asdict(definition),
                }
            )
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return path


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
        payload["recorded_utc"] = (
            payload["recorded_utc"] or datetime.now(timezone.utc).isoformat()
        )
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRIAL_COLUMNS, delimiter="\t")
            writer.writerow(payload)
            handle.flush()
            os.fsync(handle.fileno())
