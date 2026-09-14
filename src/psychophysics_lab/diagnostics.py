"""Crash and fatal-fault diagnostics for PsyCoLab.

Diagnostics are local runtime artefacts, ignored by Git, and are deliberately
separate from canonical experimental data. Normal Python exceptions receive a
plain-text traceback report. ``faulthandler`` additionally leaves a best-effort
trace if the Python process terminates because of a low-level/native fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import faulthandler
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import platform
import sys
import traceback
from typing import Any, TextIO


def _safe_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _safe_log_directory(repo_root: Path | None, data_root: Path | None) -> Path:
    candidates: list[Path] = []
    if data_root is not None:
        candidates.append(Path(data_root) / ".psycolab_logs")
    if repo_root is not None:
        candidates.append(Path(repo_root) / ".psycolab_logs")
    candidates.append(Path.cwd() / ".psycolab_logs")

    seen: set[Path] = set()
    for directory in candidates:
        try:
            directory = directory.resolve()
        except OSError:
            pass
        if directory in seen:
            continue
        seen.add(directory)
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
    """Write a local traceback report and return its path when successful.

    Absolute paths are permitted in this *local diagnostic* because they help
    identify a failing installation. They are not copied into canonical run
    metadata and the log directory is ignored by Git.
    """
    try:
        directory = _safe_log_directory(repo_root, data_root)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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
        # Diagnostics must never mask the original experiment/application error.
        return None


@dataclass
class FatalFaultCapture:
    """Best-effort low-level crash capture kept alive for the process lifetime."""

    path: Path
    handle: TextIO
    enabled: bool

    def close(self, *, clean_exit: bool) -> None:
        try:
            if self.enabled and faulthandler.is_enabled():
                faulthandler.disable()
        except Exception:
            pass
        try:
            self.handle.flush()
        except Exception:
            pass
        try:
            self.handle.close()
        except Exception:
            pass
        if clean_exit:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass


def start_fatal_fault_capture(
    *,
    repo_root: Path | None = None,
    data_root: Path | None = None,
) -> FatalFaultCapture | None:
    """Enable ``faulthandler`` so native/fatal failures can leave a traceback.

    On a normal exit the temporary fatal-fault file is removed. If the process
    terminates abnormally, cleanup does not run and the file remains in
    ``.psycolab_logs`` for inspection.
    """
    try:
        directory = _safe_log_directory(repo_root, data_root)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = directory / f"psycolab_fatal_{stamp}_{os.getpid()}.log"
        handle = path.open("w", encoding="utf-8", buffering=1)
        handle.write("PsyCoLab fatal-fault capture\n")
        handle.write("============================\n")
        handle.write(f"started_utc: {datetime.now(timezone.utc).isoformat()}\n")
        handle.write(f"python: {platform.python_version()}\n")
        handle.write(f"platform: {platform.platform()}\n\n")
        handle.flush()
        faulthandler.enable(file=handle, all_threads=True)
        return FatalFaultCapture(path=path, handle=handle, enabled=True)
    except Exception:
        return None
