"""Create/reuse PsyCoLab's local virtual environment.

The launcher deliberately targets the known working Python 3.11 baseline.
It does not install Python itself and does not modify any global environment.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PYPROJECT = ROOT / "pyproject.toml"
STATE = VENV / ".psycolab-setup.json"
EXPECTED_PYTHON = (3, 11)


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(str(part) for part in command))
    return subprocess.run(command, cwd=ROOT, check=check)


def _python_version(python: Path) -> tuple[int, int] | None:
    if not python.exists():
        return None
    proc = subprocess.run(
        [
            str(python),
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        major, minor = proc.stdout.strip().split(".", 1)
        return int(major), int(minor)
    except Exception:
        return None


def _preserve_incompatible_venv() -> None:
    if not VENV.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = ROOT / f".venv.incompatible-{stamp}"
    print(f"Existing .venv is not a Python 3.11 environment; preserving it as {destination.name}")
    shutil.move(str(VENV), str(destination))


def _load_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(pyproject_hash: str) -> None:
    STATE.write_text(
        json.dumps(
            {
                "pyproject_sha256": pyproject_hash,
                "python": ".".join(map(str, EXPECTED_PYTHON)),
                "updated_utc": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _validate_environment(python: Path) -> None:
    _run([str(python), "-m", "pip", "check"])
    code = (
        "import psychophysics_lab, numpy, pyglet, textual; "
        "print('PsyCoLab imports OK'); "
        "print('numpy', numpy.__version__); "
        "print('pyglet', pyglet.version)"
    )
    _run([str(python), "-c", code])


def main() -> int:
    if sys.version_info[:2] != EXPECTED_PYTHON:
        print(
            "ERROR: launcher_setup.py must be run with Python 3.11. "
            f"Received {sys.version_info.major}.{sys.version_info.minor}."
        )
        return 2

    if not PYPROJECT.exists():
        print("ERROR: pyproject.toml is missing.")
        return 2

    venv_python = _venv_python(VENV)
    existing_version = _python_version(venv_python)
    if VENV.exists() and existing_version != EXPECTED_PYTHON:
        _preserve_incompatible_venv()

    if not VENV.exists():
        print("Creating .venv with Python 3.11...")
        _run([sys.executable, "-m", "venv", str(VENV)])

    venv_python = _venv_python(VENV)
    if _python_version(venv_python) != EXPECTED_PYTHON:
        print("ERROR: the newly created virtual environment is not Python 3.11.")
        return 2

    pyproject_hash = _hash_file(PYPROJECT)
    state = _load_state()
    needs_install = state.get("pyproject_sha256") != pyproject_hash

    if needs_install:
        print("Installing/updating PsyCoLab dependencies...")
        try:
            _run(
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--upgrade",
                    "pip",
                    "setuptools",
                    "wheel",
                ]
            )
            _run(
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--editable",
                    str(ROOT),
                ]
            )
        except subprocess.CalledProcessError:
            print(
                "\nDependency installation failed. If this machine is offline, "
                "PsyCoLab will later support an offline wheel cache; that deployment "
                "path is not included in this first public-v1 launcher."
            )
            return 1

        _validate_environment(venv_python)
        _write_state(pyproject_hash)
    else:
        print("Dependency configuration is unchanged; reusing the existing .venv.")
        try:
            _validate_environment(venv_python)
        except subprocess.CalledProcessError:
            print("Environment validation failed; reinstalling the editable project...")
            try:
                _run(
                    [
                        str(venv_python),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "--editable",
                        str(ROOT),
                    ]
                )
                _validate_environment(venv_python)
                _write_state(pyproject_hash)
            except subprocess.CalledProcessError:
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
