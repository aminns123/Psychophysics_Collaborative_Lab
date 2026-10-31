"""Explicit source-maintainer setup; never creates laboratory qualification.

Ordinary startup calls --check only. Provisioning uses a separate .venv-dev
and accepts an installed 64-bit CPython 3.11, including the python.org build.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import venv

# Also works when Windows starts this file with Python's isolated (-I) flag.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launcher_setup as launcher

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv-dev"
STATE = VENV / ".psycolab-development.json"
PENDING = VENV / ".psycolab-development.pending.json"


def _identity() -> dict:
    return {"schema_version": 1, "mode": "development", "source_root": str(ROOT.resolve())}


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Development setup record is not an object.")
    return value


def _paths() -> None:
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 11) or struct.calcsize("P") != 8:
        raise ValueError("Maintainer setup requires 64-bit CPython 3.11.")
    if not (ROOT / ".git").exists() or (ROOT.parent / "installation.json").exists():
        raise ValueError("Use a Git source checkout for development, separate from installed laboratory software.")
    if (ROOT / ".venv").exists() or (ROOT / ".venv").is_symlink():
        raise ValueError("This checkout already has a laboratory .venv. Preserve it and use a separate Git checkout for development.")
    for path in (VENV, STATE, PENDING):
        # Reject Windows junctions as well as symlinks, before any write.
        if path.is_symlink() or path.resolve() != ROOT.resolve() / path.relative_to(ROOT):
            raise ValueError("Development environment paths must stay in this checkout without links.")


def check_only() -> int:
    """Validate the selected development environment without installation/writes."""
    try:
        _paths()
        if Path(sys.prefix).resolve() != VENV.resolve():
            raise ValueError("Use this checkout's own .venv-dev interpreter.")
        state = _read(STATE)
        if state != _identity() | {"pyproject_sha256": launcher._hash_file(ROOT / "pyproject.toml")}:
            raise ValueError("Development setup belongs to another path or dependency specification.")
        launcher._validate_environment(launcher._venv_python(VENV))
        print("Maintainer development environment verified; laboratory software qualification is not granted.")
        return 0
    except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as error:
        print(f"Development launch refused: {error}. Run setup_psycolab_dev.bat explicitly; no repair was attempted.")
        return 1


def main() -> int:
    try:
        _paths()
        if VENV.exists():
            record = _read(STATE if STATE.exists() else PENDING)
            if any(record.get(key) != value for key, value in _identity().items()):
                raise ValueError("Existing .venv-dev is not owned by this checkout. Preserve it and use a separate checkout.")
        else:
            VENV.mkdir()
            PENDING.write_text(json.dumps(_identity(), indent=2), encoding="utf-8")
        python = launcher._venv_python(VENV)
        if not python.exists():
            venv.EnvBuilder(with_pip=True).create(VENV)
        # This is a developer install of the declared project requirements, not
        # an assertion that this interpreter matches the locked laboratory profile.
        launcher._run([str(python), "-I", "-m", "pip", "--isolated", "install",
                       "--disable-pip-version-check", "--editable", str(ROOT) + "[dev]"])
        launcher._validate_environment(python)
        temporary = STATE.with_suffix(".tmp")
        temporary.write_text(json.dumps(_identity() | {
            "pyproject_sha256": launcher._hash_file(ROOT / "pyproject.toml")
        }, indent=2), encoding="utf-8")
        temporary.replace(STATE)
        print("Maintainer setup complete. Open run_psycolab.bat to start the normal TUI.")
        print("This environment is for development; it has no locked laboratory qualification.")
        return 0
    except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as error:
        print(f"Maintainer setup failed: {error}. Existing laboratory software was preserved.")
        return 1


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--check"]):
        raise SystemExit("Usage: developer_setup.py [--check]")
    raise SystemExit(check_only() if sys.argv[1:] else main())
