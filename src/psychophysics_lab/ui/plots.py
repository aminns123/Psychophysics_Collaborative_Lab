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
