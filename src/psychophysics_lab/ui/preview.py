"""Show appearance previews; no display calibration or acquisition is performed."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def open_preview(path):
    """Open only an existing PNG using the platform image viewer, without a shell."""
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".png":
        raise ValueError("Preview must be an existing PNG image.")
    if os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.Popen(
            ["open" if sys.platform == "darwin" else "xdg-open", str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def show_stimulus_preview(identity, parameters, directory):
    from ..core.presentation import preview_stimulus

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / (str(uuid4()) + ".png")
    preview_stimulus(identity, parameters, output)
    try:
        open_preview(output)
    except OSError as exc:
        raise OSError(
            f"Preview saved to {output}, but the image viewer could not open: {exc}"
        ) from exc
    return output
