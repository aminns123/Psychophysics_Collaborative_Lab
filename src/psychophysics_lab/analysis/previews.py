"""Non-destructive, exploratory quick-look plots from canonical PsyCoLab trial data.

Both human and synthetic acquisitions can be inspected. Figures are DERIVED
artifacts beneath the external data root, never acquisition evidence or edits
to the original canonical trial records.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from .thresholds import _owned_run, _read_manifest
from ..data.session import atomic_write_json


@dataclass(frozen=True)
class StaircasePreview:
    output_directory: Path
    plot_file: Path | None
    summary_file: Path


def latest_staircase_plot(*, data_root: Path, run_directory: Path) -> Path | None:
    run = _owned_run(data_root, run_directory)
    manifest = _read_manifest(run)
    uid = str(manifest.get("run_uuid", "")).strip()
    if not uid or "/" in uid or "\\" in uid or ".." in uid:
        return None
    folder = data_root.resolve() / "analysis" / "quicklook" / uid
    return next((p for p in sorted(folder.glob("*/staircases.png"), reverse=True)
                 if p.is_file() and not p.is_symlink()), None)


def create_staircase_preview(*, data_root: Path, run_directory: Path) -> StaircasePreview:
    data = Path(data_root).resolve()
    run = _owned_run(data, Path(run_directory))
    manifest = _read_manifest(run)
    if manifest.get("status") in {"configuring", "configured", "running"}:
        raise ValueError("Wait for canonical acquisition to finish before previewing it.")
    uuid = str(manifest.get("run_uuid", "")).strip()
    if not uuid or any(c in uuid for c in ("/", "\\", "..")):
        raise ValueError("Run UUID cannot form a safe analysis path.")
    source = run / "trials.tsv"
    with source.open("r", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError("No canonical trial header to preview.")
        required = {"staircase_id", "stimulus_condition", "presented_display_contrast", "reversal"}
        if required - set(reader.fieldnames):
            raise ValueError("Staircase preview requires canonical staircase and contrast columns.")
        rows = list(reader)
    groups: dict[tuple[str, str], list[tuple[int,float,bool]]] = {}
    for row in rows:
        raw = str(row.get("presented_display_contrast", "")).strip()
        if not raw:
            continue
        contrast = float(raw)
        if not math.isfinite(contrast) or contrast < 0:
            raise ValueError("Nonfinite or negative presented contrast in canonical trials.")
        key = (str(row["staircase_id"]), str(row["stimulus_condition"]))
        try:
            index = int(row.get("staircase_trial_index") or row.get("trial_index"))
        except (ValueError, TypeError):
            raise ValueError("Each plotted canonical trial requires its accepted trial index.")
        groups.setdefault(key, []).append(
            (index, contrast, str(row.get("reversal", "")).lower() in {"1", "true"})
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output = data / "analysis" / "quicklook" / uuid / stamp
    output.mkdir(parents=True, exist_ok=False)
    png = None
    if groups:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5.5))
        for (staircase_id, condition), values in sorted(groups.items()):
            values.sort(key=lambda item: item[0])
            xs = [item[0] for item in values]
            ys = [item[1] for item in values]
            (line,) = ax.plot(xs, ys, marker=".", linewidth=1.3,
                             label=f"Staircase {staircase_id} / condition {condition}")
            reversals = [(x, y) for x, y, rev in values if rev]
            if reversals:
                ax.scatter([x for x, _ in reversals], [y for _, y in reversals],
                           marker="x", s=35, color=line.get_color())
        ax.set_xlabel("Accepted response within staircase")
        ax.set_ylabel("Presented display contrast (normalised)")
        ax.set_title("Exploratory staircase traces — crosses denote reversals")
        ax.grid(True, alpha=.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        png = output / "staircases.png"
        fig.savefig(png, dpi=150)
        plt.close(fig)
    summary = output / "quicklook.json"
    atomic_write_json(summary, {
        "schema_version": 1,
        "analysis": "nonfinal_staircase_quicklook",
        "source_run_relative": run.relative_to(data).as_posix(),
        "source_run_uuid": uuid,
        "data_kind": manifest.get("data_kind", "human"),
        "canonical_trials_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "plotted_accepted_trials": sum(len(values) for values in groups.values()),
        "staircases_plotted": len(groups),
        "plot": png.name if png else None,
        "warning": "Exploratory figure. This is NOT a final threshold estimate or a measurement of physical display timing.",
    })
    return StaircasePreview(output, png, summary)
