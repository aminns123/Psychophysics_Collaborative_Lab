"""Repository and data paths used by PsyCoLab."""

from __future__ import annotations

import os
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """Find the checkout containing the legacy experiment implementation."""
    override = os.environ.get("PSYCOLAB_REPO_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
        if (root / "Experiments").is_dir() and (root / "Interface").is_dir():
            return root
        raise RuntimeError(f"PSYCOLAB_REPO_ROOT is not a PsyCoLab checkout: {root}")

    candidates: list[Path] = []
    if start is not None:
        candidates.extend([start.resolve(), *start.resolve().parents])

    here = Path(__file__).resolve()
    candidates.extend(here.parents)

    cwd = Path.cwd().resolve()
    candidates.extend([cwd, *cwd.parents])

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (
            (candidate / "Experiments").is_dir()
            and (candidate / "Interface").is_dir()
            and (candidate / "libC.py").exists()
        ):
            return candidate

    raise RuntimeError(
        "Could not locate the PsyCoLab repository root. "
        "Run PsyCoLab from the repository checkout or set PSYCOLAB_REPO_ROOT."
    )


def default_data_root(repo_root: Path | None = None) -> Path:
    """Default to a sibling folder so experimental data stays out of Git."""
    override = os.environ.get("PSYCOLAB_DATA_DIR")
    if override:
        return Path(os.path.expandvars(override)).expanduser().resolve()

    root = repo_root or find_repo_root()
    return root.parent / "local_psychophysics_data"


def resolve_data_root(value: str | Path, repo_root: Path) -> Path:
    """Resolve a TUI-entered data directory without placing it inside the repo."""
    raw = os.path.expandvars(str(value).strip())
    if not raw:
        raise ValueError("A data folder is required.")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = repo_root.parent / path
    path = path.resolve()

    repo = repo_root.resolve()
    if path == repo or path.is_relative_to(repo) or repo.is_relative_to(path):
        raise ValueError(
            "Experimental data must be stored in a separate folder outside the "
            "PsyCoLab repository (an adjacent/sibling folder is recommended)."
        )
    return path
