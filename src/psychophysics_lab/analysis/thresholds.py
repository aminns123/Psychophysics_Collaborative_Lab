"""Post-hoc staircase threshold summaries.

The functions in this module read canonical acquisition records and write new
outputs below the external workspace ``analysis/`` directory.  They do not
change staircase updates, termination, trial files or run manifests.
"""

from __future__ import annotations

import csv
import hashlib
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


def _plot(condition_thresholds: tuple[ConditionThreshold, ...], output: Path, *, x_label="Condition", warning="") -> Path | None:
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
    ax.set_xlabel(x_label)
    ax.set_ylabel("Threshold C_disp (digital; not measured physical contrast)")
    ax.set_title("Derived threshold contrast vs condition" + ("\n" + warning if warning else ""))
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
    last_n_reversals: int | None = None,
    reversal_value_column: str = "next_display_contrast",
    create_plot: bool = True,
) -> ThresholdAnalysisResult:
    """Create a derived threshold summary for one finalized run.

    ``retain_fraction=0.80`` means retain the final 80% of reversal observations
    *within each staircase*.  ``ceil`` is used for non-integer counts so that at
    least the requested fraction is retained.  The default reversal value is the
    post-response ``next_display_contrast``, matching the current legacy CSF
    reversal basis.  Alternatively, ``last_n_reversals`` retains up to N
    final reversals for each staircase. This is a configurable derived analysis
    convention, not a modification to acquisition or the staircase rule.
    """
    fraction = float(retain_fraction)
    if not math.isfinite(fraction) or not 0 < fraction <= 1:
        raise ValueError("retain_fraction must be in (0, 1].")

    if last_n_reversals is not None and (
        type(last_n_reversals) is not int or last_n_reversals < 1
    ):
        raise ValueError("Last N reversals must be a positive integer.")
    data_root = data_root.resolve()
    run_directory = _owned_run(data_root, run_directory)
    manifest = _read_manifest(run_directory)
    if manifest.get("status") in {"configuring", "configured", "running"}:
        raise ValueError("Wait for the run to finalise before deriving thresholds.")
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
        keep = min(len(values), last_n_reversals) if last_n_reversals is not None else max(1, math.ceil(len(values) * fraction))
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
    # Keep all analyses WITH the acquisition they describe. Each change of
    # reversal convention creates a version, never overwriting canonical trials.
    output = run_directory / "analysis" / "thresholds" / stamp
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

    entered_unit = manifest.get("experiment_values", {}).get("condition_unit")
    if manifest.get("experiment_id") == "contrast_sensitivity":
        x_label = ("Spatial frequency (cycles/degree)" if entered_unit in {"cycles_per_degree", "degrees_per_cycle"}
                   else "Historical shader phase (uncalibrated legacy units)")
    else:
        x_label = "Condition"
    incomplete = manifest.get("status") != "completed"
    missing_ids = []
    states = manifest.get("adaptive_session", {}).get("staircases", {})
    estimated_ids = {item.staircase_id for item in staircase_results}
    if states:
        missing_ids = sorted(str(identity) for identity in states if str(identity) not in estimated_ids)
    warning = "EXPLORATORY — INCOMPLETE/CENSORED RUN" if incomplete else "EXPLORATORY REVERSAL ESTIMATE"
    if missing_ids:
        warning += "; some staircases have no reversal estimate"
    if manifest.get("data_kind") == "synthetic":
        warning = "SYNTHETIC — " + warning
    plot_file = _plot(condition_results, plot_path, x_label=x_label, warning=warning) if create_plot else None
    if plot_file:
        import shutil
        latest = run_directory / "analysis" / "threshold_vs_condition.png"
        shutil.copy2(plot_file, latest)
    source_relative = run_directory.relative_to(data_root).as_posix()
    summary = {
        "schema_version": 1,
        "analysis": "staircase_threshold_summary",
        "data_kind": manifest.get("data_kind", "human"),
        "simulation": manifest.get("simulation"),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_relative": source_relative,
        "source_run_uuid": manifest.get("run_uuid"),
        "input_sha256": {name: hashlib.sha256((run_directory / name).read_bytes()).hexdigest() for name in ("manifest.json", "trials.tsv")},
        "quality_flags": {
            "source_status": manifest.get("status", "unknown"),
            "incomplete_run": incomplete,
            "missing_staircase_estimates": missing_ids,
            "calibration_status": manifest.get("calibration", {}).get("status", "unverified"),
            "timing_status": manifest.get("runtime_display", {}).get("timing_status", "unverified"),
            "photon_timing_verified": False},
        "monitor_profile_sha256": manifest.get("monitor_profile_sha256"),
        "condition_axis_label": x_label,
        "scientific_warning": warning,
        "participant_id": manifest.get("participant_id"),
        "experiment_id": manifest.get("experiment_id"),
        "retain_fraction": fraction if last_n_reversals is None else None,
        "last_n_reversals": last_n_reversals,
        "retained_subset_rule": (
            f"last min(N, {last_n_reversals}) reversal observations per staircase"
            if last_n_reversals is not None
            else "final ceil(N * retain_fraction) reversals per staircase"
        ),
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
    from ..data.session import atomic_write_json
    atomic_write_json(run_directory / "analysis" / "latest_threshold_analysis.json", {
        "analysis_version": output.relative_to(run_directory).as_posix(),
        "last_n_reversals": last_n_reversals,
        "retain_fraction": summary["retain_fraction"],
        "reversal_value_column": reversal_value_column,
        "plot": "threshold_vs_condition.png" if plot_file else None,
        "scientific_warning": warning + "; not an authorised final THC.",
    })

    return ThresholdAnalysisResult(
        output_directory=output,
        staircase_table=staircase_table,
        condition_table=condition_table,
        summary_json=summary_json,
        plot_file=plot_file,
        staircase_thresholds=tuple(staircase_results),
        condition_thresholds=condition_results,
    )
