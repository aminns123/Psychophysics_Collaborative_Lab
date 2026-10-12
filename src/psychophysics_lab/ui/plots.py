"""Explicit safe OS image viewer for derived analysis PNGs in the data root."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def open_analysis_png(data_root: Path, image_path: Path) -> None:
    analysis_root = (Path(data_root) / "analysis").resolve()
    path = Path(image_path).resolve()
    if not path.is_relative_to(analysis_root) or path.suffix.lower() != ".png" or not path.is_file():
        raise ValueError("Only an existing derived-analysis PNG under the active data root may be opened.")
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        opener = ["open"] if sys.platform == "darwin" else ["xdg-open"]
        subprocess.Popen(opener + [str(path)], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
