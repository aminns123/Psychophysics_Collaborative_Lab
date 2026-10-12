"""Explicit safe OS image viewer for derived analysis PNGs in the data root."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def open_analysis_png(data_root: Path, image_path: Path) -> None:
    root = Path(data_root).resolve()
    raw = Path(image_path).absolute()
    path = raw.resolve()
    if (raw != path or not path.is_relative_to(root)
            or path.suffix.lower() != ".png" or not path.is_file()
            or path.is_symlink()):
        raise ValueError("Only a real derived PNG inside the selected data root may be opened.")
    # Accept the current run-owned location, and historical data_root/analysis
    # paths read-only. Never open arbitrary PNGs under other participant files.
    legacy = path.is_relative_to(root / "analysis")
    owned = any(
        parent.name == "analysis" and (parent.parent / "manifest.json").is_file()
        for parent in path.parents if parent.is_relative_to(root)
    )
    if not (owned or legacy):
        raise ValueError("Image must be a derived analysis plot from a PsyCoLab run.")
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        opener = ["open"] if sys.platform == "darwin" else ["xdg-open"]
        subprocess.Popen(opener + [str(path)], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



def open_run_directory(data_root: Path, run_directory: Path) -> None:
    """Open the chosen run folder, never an arbitrary external filesystem path."""
    root = Path(data_root).resolve()
    raw = Path(run_directory).absolute()
    run = raw.resolve()
    if (raw != run or not run.is_relative_to(root) or run == root
            or not run.is_dir() or run.is_symlink()
            or not (run / "manifest.json").is_file()
            or (run / "manifest.json").is_symlink()):
        raise ValueError("Only a real PsyCoLab run directory inside the data repository can be opened.")
    if sys.platform == "win32":
        os.startfile(str(run))  # type: ignore[attr-defined]
    else:
        opener = ["open"] if sys.platform == "darwin" else ["xdg-open"]
        subprocess.Popen(opener + [str(run)], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
