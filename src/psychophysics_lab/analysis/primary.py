"""One protocol-declared primary estimate from canonical presented reversals.

Used at acquisition finalisation and again for post-hoc reproduction. Exploratory
generic summaries remain separate. No staircase or acquisition records are edited.
"""

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median, mean, geometric_mean


def expected_staircases(conditions):
    expected = {}
    for condition in conditions:
        key = str(condition.get("value", condition.get("frequency_cpd")))
        expected.setdefault(key, []).append(condition["id"])
    return expected


def estimate(rows, rule, expected, status):
    if (
        rule.get("version") != 1
        or rule.get("value_column") != "presented_display_contrast"
    ):
        raise ValueError(
            "Unsupported primary estimator/version or reversal value convention."
        )
    retained = rule["retained_reversals"]
    if type(retained) is not int or retained < 1:
        raise ValueError("Retained reversal count must be positive.")
    reducer = {"median": median, "geometric_mean": geometric_mean}.get(
        rule["within_staircase"]
    )
    if reducer is None:
        raise ValueError("Unsupported primary within-staircase estimator.")
    if rule.get("across_staircases") != "arithmetic_mean":
        raise ValueError("Unsupported primary across-staircase estimator.")
    ownership = {}
    for condition, ids in expected.items():
        for identity in ids:
            if str(identity) in ownership:
                raise ValueError("A staircase must belong to exactly one condition.")
            ownership[str(identity)] = str(condition)
    grouped = {}
    for row in rows:
        identity = str(row["staircase_id"])
        if (
            identity not in ownership
            or str(row["stimulus_condition"]) != ownership[identity]
        ):
            raise ValueError(
                "Canonical staircase/condition does not match the declared protocol."
            )
        grouped.setdefault(identity, []).append(row)
    staircases = {}
    conditions = {}
    excluded = {}
    reversal_counts = {}
    allowed = status in {"completed", "max_trials_reached", "aborted_by_user"}
    for condition, ids in expected.items():
        valid = []
        for identity in ids:
            history = grouped.get(str(identity), [])
            reversal_values = [
                float(r[rule["value_column"]])
                for r in history
                if str(r.get("reversal")) == "1"
            ]
            if any(not math.isfinite(v) or v <= 0 for v in reversal_values):
                raise ValueError(
                    "Primary reversal strengths must be finite and positive."
                )
            complete = (
                bool(history) and str(history[-1].get("staircase_complete")) == "1"
            )
            if not allowed or not complete or len(reversal_values) < retained:
                excluded[str(identity)] = (
                    "run error, incomplete staircase, or insufficient reversals"
                )
                continue
            value = reducer(reversal_values[-retained:])
            reversal_counts[str(identity)] = len(reversal_values)
            staircases[str(identity)] = value
            valid.append(value)
        if len(valid) == len(ids) and valid:
            threshold = mean(valid)
            conditions[str(condition)] = {
                "threshold": threshold,
                "sensitivity": 1 / threshold,
            }
    boundary_affected = []
    for identity, bounds in rule.get("strength_bounds", {}).items():
        lower, upper = bounds
        if any(
            row.get(column) not in (None, "") and
            (float(row[column]) <= lower or float(row[column]) >= upper)
            for row in grouped.get(str(identity), [])
            for column in ("presented_display_contrast", "next_display_contrast")
        ):
            boundary_affected.append(str(identity))
    return {
        "boundary_affected_staircases": boundary_affected,
        "boundary_warning": ("Adaptive strength reached a bound; estimates may be boundary-biased and require review." if boundary_affected else ""),
        "primary_estimator": dict(rule),
        "expected_staircases": expected,
        "run_status": status,
        "qualification": "digital metric; physical calibration not established",
        "staircase_thresholds": staircases,
        "staircase_reversal_counts": reversal_counts,
        "condition_thresholds": conditions,
        "excluded_staircases": excluded,
    }


def from_run(run_directory, rule, expected, status):
    with (Path(run_directory) / "trials.tsv").open(
        newline="", encoding="utf-8"
    ) as stream:
        return estimate(
            list(csv.DictReader(stream, delimiter="\t")), rule, expected, status
        )


def analyse_primary(*, data_root, run_directory, create_plot=True):
    from datetime import datetime, timezone
    from .thresholds import (
        ThresholdAnalysisResult,
        StaircaseThreshold,
        ConditionThreshold,
        _write_tsv,
        _plot,
    )

    root = Path(run_directory).resolve()
    if not root.is_relative_to(Path(data_root).resolve()):
        raise ValueError("Run outside data workspace.")
    resolved = json.loads((root / "resolved_experiment.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    rule = resolved["primary_estimator"]
    result = from_run(root, rule, resolved["expected_staircases"], manifest["status"])
    if not result["condition_thresholds"]:
        raise ValueError("Primary thresholds unavailable: no complete condition.")
    # Carry source context into every independently shared derived report.
    # Acquisition records and the protocol's numerical estimator stay unchanged.
    data_kind = manifest.get("data_kind", "unknown")
    incomplete = manifest["status"] != "completed"
    warning_lines = []
    if data_kind == "synthetic":
        warning_lines.append("SYNTHETIC")
    elif data_kind == "uncalibrated_presentation_test":
        warning_lines.append("UNCALIBRATED PRESENTATION TEST")
    elif data_kind != "human":
        warning_lines.append("UNKNOWN DATA ORIGIN")
    warning_lines.append("Protocol primary estimator" + (" — INCOMPLETE/CENSORED RUN" if incomplete else ""))
    if result["excluded_staircases"]:
        warning_lines.append("Some staircases have no primary estimate")
    if result["boundary_affected_staircases"]:
        warning_lines.append("BOUNDARY-AFFECTED estimates; review required")
    warning_lines.append("Digital metric; physical calibration not established")
    warning = "\n".join(warning_lines)
    result.update({
        "schema_version": 1,
        "analysis": "protocol_primary_threshold_summary",
        "analysis_role": "protocol_primary",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "data_kind": data_kind,
        "simulation": manifest.get("simulation"),
        "source_run_relative": root.relative_to(Path(data_root).resolve()).as_posix(),
        "source_run_uuid": manifest.get("run_uuid"),
        "source_software": manifest.get("software"),
        "participant_id": manifest.get("participant_id"),
        "experiment_id": manifest.get("experiment_id"),
        "monitor_profile_sha256": manifest.get("monitor_profile_sha256"),
        "input_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                         for name in ("manifest.json", "trials.tsv", "resolved_experiment.json")},
        "quality_flags": {
            "source_status": manifest["status"],
            "incomplete_run": incomplete,
            "missing_staircase_estimates": sorted(result["excluded_staircases"]),
            "boundary_affected_staircases": result["boundary_affected_staircases"],
            "calibration_status": manifest.get("calibration", {}).get("status", "unverified"),
            "timing_status": manifest.get("runtime_display", {}).get("timing_status", "unverified"),
            # A derived software analysis cannot establish photon timing.
            "photon_timing_verified": False,
        },
        "scientific_warning": warning,
    })
    output = (
        root
        / "analysis"
        / "primary"
        / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    output.mkdir(parents=True)
    stairs = tuple(
        StaircaseThreshold(
            condition,
            str(i),
            result["staircase_reversal_counts"][str(i)],
            rule["retained_reversals"],
            result["staircase_thresholds"][str(i)],
        )
        for condition, ids in result["expected_staircases"].items()
        for i in ids
        if str(i) in result["staircase_thresholds"]
    )
    conditions = tuple(
        ConditionThreshold(c, len(result["expected_staircases"][c]), v["threshold"])
        for c, v in result["condition_thresholds"].items()
    )
    sf, cf, jf = (
        output / "staircase_thresholds.tsv",
        output / "threshold_by_condition.tsv",
        output / "threshold_analysis.json",
    )
    from dataclasses import asdict

    _write_tsv(
        sf,
        [asdict(v) for v in stairs],
        ("condition", "staircase_id", "reversal_count", "retained_count", "threshold"),
    )
    _write_tsv(
        cf,
        [asdict(v) for v in conditions],
        ("condition", "staircase_count", "threshold"),
    )
    jf.write_text(json.dumps(result, indent=2), encoding="utf-8")
    plot = (
        _plot(
            conditions,
            output / "threshold_vs_condition.png",
            warning=warning,
        )
        if create_plot
        else None
    )
    return ThresholdAnalysisResult(output, sf, cf, jf, plot, stairs, conditions)
