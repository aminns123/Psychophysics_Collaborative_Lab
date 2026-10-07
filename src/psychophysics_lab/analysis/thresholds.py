"""Post-hoc staircase threshold summaries.

The functions in this module read canonical acquisition records and write new
outputs below the external workspace ``analysis/`` directory.  They do not
change staircase updates, termination, trial files or run manifests.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any


@dataclass(frozen=True)
class StaircaseThreshold:
    condition: str
    staircase_id: str
    reversal_count: int
    retained_count: int
    threshold: float


@dataclass(frozen=True)
class ConditionThreshold:
    condition: str
    staircase_count: int
    threshold: float


@dataclass(frozen=True)
class ThresholdAnalysisResult:
    output_directory: Path
    staircase_table: Path
    condition_table: Path
    summary_json: Path
    plot_file: Path | None
    staircase_thresholds: tuple[StaircaseThreshold, ...]
    condition_thresholds: tuple[ConditionThreshold, ...]


def _owned_run(data_root: Path, run_directory: Path) -> Path:
    root = data_root.resolve()
    run = run_directory.resolve()
    if not run.is_relative_to(root):
        raise ValueError("Selected run is not inside the active external PsyCoLab data workspace.")
    return run


def _read_manifest(run_directory: Path) -> dict[str, Any]:
    path = run_directory / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest.json must contain an object.")
    return payload


def _read_trials(run_directory: Path) -> list[dict[str, str]]:
    path = run_directory / "trials.tsv"
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError("trials.tsv has no header.")
        required = {"stimulus_condition", "staircase_id", "reversal"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"trials.tsv is missing required columns: {sorted(missing)}")
        return [dict(row) for row in reader]


def _safe_component(value: Any) -> str:
    text = str(value).strip() or "unknown"
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)[:80]


def _write_tsv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _plot(condition_thresholds: tuple[ConditionThreshold, ...], output: Path) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None

    labels = [item.condition for item in condition_thresholds]
    values = [item.threshold for item in condition_thresholds]
    try:
        x = [float(item) for item in labels]
        xlabel = "Condition"
        tick_labels = None
    except ValueError:
        x = list(range(len(labels)))
        xlabel = "Condition"
        tick_labels = labels

    fig, ax = plt.subplots()
    ax.plot(x, values, marker="o")
    if tick_labels is not None:
        ax.set_xticks(x, tick_labels)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Threshold contrast")
    ax.set_title("Derived threshold contrast vs condition")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output


def analyse_thresholds(
    *,
    data_root: Path,
    run_directory: Path,
    retain_fraction: float = 0.80,
    reversal_value_column: str = "next_display_contrast",
    create_plot: bool = True,
) -> ThresholdAnalysisResult:
    """Create a derived threshold summary for one finalized run.

    ``retain_fraction=0.80`` means retain the final 80% of reversal observations
    *within each staircase*.  ``ceil`` is used for non-integer counts so that at
    least the requested fraction is retained.  The default reversal value is the
    post-response ``next_display_contrast``, matching the current legacy CSF
    reversal basis.  This is a configurable analysis convention, not an
    acquisition/staircase rule.
    """
    fraction = float(retain_fraction)
    if not math.isfinite(fraction) or not 0 < fraction <= 1:
        raise ValueError("retain_fraction must be in (0, 1].")

    data_root = data_root.resolve()
    run_directory = _owned_run(data_root, run_directory)
    manifest = _read_manifest(run_directory)
    rows = _read_trials(run_directory)
    if not rows:
        raise ValueError("This run contains no accepted responses; no threshold can be derived.")
    if reversal_value_column not in rows[0]:
        raise ValueError(f"Unknown reversal value column: {reversal_value_column}")

    grouped: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        if str(row.get("reversal", "")).strip() not in {"1", "true", "True"}:
            continue
        raw = str(row.get(reversal_value_column, "")).strip()
        if not raw:
            continue
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(
                f"Non-finite reversal value in {reversal_value_column}: {raw!r}"
            )
        key = (str(row.get("stimulus_condition", "")), str(row.get("staircase_id", "")))
        grouped.setdefault(key, []).append(value)

    if not grouped:
        raise ValueError("No reversal observations were found in the selected run.")

    staircase_results: list[StaircaseThreshold] = []
    for (condition, staircase_id), values in sorted(grouped.items()):
        keep = max(1, math.ceil(len(values) * fraction))
        retained = values[-keep:]
        staircase_results.append(
            StaircaseThreshold(
                condition=condition,
                staircase_id=staircase_id,
                reversal_count=len(values),
                retained_count=keep,
                threshold=fmean(retained),
            )
        )

    by_condition: dict[str, list[float]] = {}
    for item in staircase_results:
        by_condition.setdefault(item.condition, []).append(item.threshold)
    def condition_sort_key(item):
        condition = item[0]
        try:
            return (0, float(condition))
        except ValueError:
            return (1, condition)

    condition_results = tuple(
        ConditionThreshold(
            condition=condition,
            staircase_count=len(values),
            threshold=fmean(values),
        )
        for condition, values in sorted(by_condition.items(), key=condition_sort_key)
    )

    run_uuid = _safe_component(manifest.get("run_uuid", run_directory.name))
    participant = _safe_component(manifest.get("participant_id", "unknown_participant"))
    experiment = _safe_component(manifest.get("experiment_id", "unknown_experiment"))
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S_%f")
    output = data_root / "analysis" / "thresholds" / participant / experiment / run_uuid / stamp
    output.mkdir(parents=True, exist_ok=False)

    staircase_table = output / "staircase_thresholds.tsv"
    condition_table = output / "threshold_by_condition.tsv"
    summary_json = output / "threshold_analysis.json"
    plot_path = output / "threshold_vs_condition.png"

    _write_tsv(
        staircase_table,
        [asdict(item) for item in staircase_results],
        ("condition", "staircase_id", "reversal_count", "retained_count", "threshold"),
    )
    _write_tsv(
        condition_table,
        [asdict(item) for item in condition_results],
        ("condition", "staircase_count", "threshold"),
    )

    plot_file = _plot(condition_results, plot_path) if create_plot else None
    source_relative = run_directory.relative_to(data_root).as_posix()
    summary = {
        "schema_version": 1,
        "analysis": "staircase_threshold_summary",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_relative": source_relative,
        "source_run_uuid": manifest.get("run_uuid"),
        "participant_id": manifest.get("participant_id"),
        "experiment_id": manifest.get("experiment_id"),
        "retain_fraction": fraction,
        "retained_subset_rule": "final ceil(N * retain_fraction) reversals per staircase",
        "reversal_value_column": reversal_value_column,
        "scientific_note": (
            "Derived analysis only. This convention does not alter acquisition, staircase "
            "updates, termination, contrast definitions or canonical run files."
        ),
        "staircase_thresholds": [asdict(item) for item in staircase_results],
        "condition_thresholds": [asdict(item) for item in condition_results],
        "files": {
            "staircase_thresholds": staircase_table.name,
            "threshold_by_condition": condition_table.name,
            "plot": plot_file.name if plot_file else None,
        },
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return ThresholdAnalysisResult(
        output_directory=output,
        staircase_table=staircase_table,
        condition_table=condition_table,
        summary_json=summary_json,
        plot_file=plot_file,
        staircase_thresholds=tuple(staircase_results),
        condition_thresholds=condition_results,
    )
