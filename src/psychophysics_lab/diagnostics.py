"""Local crash diagnostics for PsyCoLab.

Crash reports are deliberately local runtime artefacts. They are never required
for experiment execution and are ignored by Git. Canonical scientific run files
remain separate from these diagnostics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
import sys
import traceback
from typing import Any


def _safe_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _safe_log_directory(repo_root: Path | None, data_root: Path | None) -> Path:
    candidates: list[Path] = []
    if data_root is not None:
        candidates.append(data_root / ".psycolab_logs")
    if repo_root is not None:
        candidates.append(repo_root / ".psycolab_logs")
    candidates.append(Path.cwd() / ".psycolab_logs")

    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return directory
        except OSError:
            continue
    raise OSError("PsyCoLab could not find a writable location for its crash log.")


def write_crash_report(
    exc: BaseException,
    *,
    repo_root: Path | None = None,
    data_root: Path | None = None,
    phase: str = "unknown",
    extra: dict[str, Any] | None = None,
) -> Path | None:
    """Write a plain-text traceback without making it part of the scientific data.

    Absolute paths may appear in this local diagnostic because they are useful for
    debugging one machine. The report is ignored by Git and no runtime logic reads
    it back, so it never makes PsyCoLab dependent on a particular user's path.
    """
    try:
        directory = _safe_log_directory(repo_root, data_root)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = directory / f"psycolab_error_{stamp}.log"

        lines = [
            "PsyCoLab crash report",
            "=====================",
            f"utc: {datetime.now(timezone.utc).isoformat()}",
            f"phase: {phase}",
            f"python: {platform.python_version()}",
            f"python_implementation: {platform.python_implementation()}",
            f"platform: {platform.platform()}",
            f"executable_name: {Path(sys.executable).name}",
            f"numpy: {_safe_version('numpy')}",
            f"pyglet: {_safe_version('pyglet')}",
            f"textual: {_safe_version('textual')}",
        ]
        if repo_root is not None:
            lines.append(f"runtime_repository_path: {repo_root}")
        if data_root is not None:
            lines.append(f"runtime_data_path: {data_root}")
        if extra:
            for key, value in sorted(extra.items()):
                lines.append(f"{key}: {value}")

        lines.extend(
            [
                "",
                "Exception",
                "---------",
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
    except Exception:
        return None
