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
    if any((VENV / name).exists() for name in (".psycolab-setup.json", ".psycolab-setup.pending.json")):
        raise ValueError("A laboratory setup record exists inside .venv-dev; it cannot be converted or overwritten.")


def _verify_pinned_environment(python: Path) -> None:
    """Check versions and installed wheel RECORD hashes, without importing them."""
    pins = {}
    for name in ("build", "runtime", "development"):
        for line in (ROOT / "requirements/windows-cp311" / (name + ".lock")).read_text().splitlines():
            if "==" in line and not line.startswith("#"):
                package, version = line.split()[0].split("==")
                pins[package] = version
    code = """
import base64, hashlib, json, sys
from importlib.metadata import distribution
for name, version in json.loads(sys.argv[1]).items():
    dist = distribution(name)
    if dist.version != version:
        raise ValueError(f'{name}: expected {version}, found {dist.version}; run recovery')
    files = dist.files
    if not files:
        raise ValueError(f'{name}: installed file inventory missing; run recovery')
    for item in files:
        # pip may regenerate wheel-supplied bytecode for its installation path.
        if item.hash is None or str(item).endswith(('.pyc', '.pyo')):
            continue
        path = dist.locate_file(item)
        digest = base64.urlsafe_b64encode(hashlib.new(item.hash.mode, path.read_bytes()).digest()).rstrip(b'=').decode()
        if digest != item.hash.value:
            raise ValueError(f'{name}: installed file changed: {item}; run recovery')
print('Pinned source dependencies and installed wheel hashes verified.')
"""
    launcher._run([str(python), "-I", "-B", "-c", code, json.dumps(pins)])


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
        _verify_pinned_environment(launcher._venv_python(VENV))
        print("Maintainer development environment verified; laboratory software qualification is not granted.")
        return 0
    except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as error:
        print(f"Development launch refused: {error}. Open PsyCoLab.bat and choose 2 - Check / Repair; no repair was attempted.")
        return 1


def main(*, repair: bool = False) -> int:
    try:
        _paths()
        if repair and Path(sys.prefix).resolve() == VENV.resolve():
            raise ValueError("Use PsyCoLab.bat, option 2, to repair from a separate base interpreter.")
        if VENV.exists():
            record = _read(STATE if STATE.exists() else PENDING)
            if any(record.get(key) != value for key, value in _identity().items()):
                raise ValueError("Existing .venv-dev is not owned by this checkout. Preserve it and use a separate checkout.")
        else:
            VENV.mkdir()
            PENDING.write_text(json.dumps(_identity(), indent=2), encoding="utf-8")
        python = launcher._venv_python(VENV)
        if repair or not python.exists():
            venv.EnvBuilder(with_pip=True).create(VENV)
        # Reuse the repository's hash-pinned wheels, without asserting that an
        # ordinary CPython interpreter meets the qualified laboratory profile.
        options = launcher._wheelhouse_options()
        for section in ("build", "development"):
            installer = [str(python), "-I", "-X", "faulthandler", "-m", "pip"]
            if repair:
                # Recover even a missing/broken target pip, without installing
                # anything into the base interpreter. CPython bundles this wheel.
                bootstrap = """
import ensurepip, runpy, sys
from pathlib import Path
wheel = next((Path(ensurepip.__file__).parent / '_bundled').glob('pip-*.whl'))
sys.path.insert(0, str(wheel))
sys.argv = ['bootstrap-pip', *sys.argv[1:]]
runpy.run_module('pip', run_name='__main__', alter_sys=True)
"""
                installer = [str(python), "-I", "-B", "-X", "faulthandler", "-c", bootstrap]
            launcher._run([*installer, "--isolated", "install",
                           "--disable-pip-version-check", "--no-compile", "--require-hashes", "--only-binary=:all:",
                           *(["--force-reinstall"] if repair else []), "--requirement",
                           str(ROOT / "requirements/windows-cp311" / (section + ".lock")), *options])
        launcher._run([str(python), "-I", "-m", "pip", "--isolated", "install",
                       "--disable-pip-version-check", "--no-compile", "--no-deps", "--no-build-isolation",
                       "--editable", str(ROOT) + "[dev]"])
        launcher._validate_environment(python)
        _verify_pinned_environment(python)
        temporary = STATE.with_suffix(".tmp")
        temporary.write_text(json.dumps(_identity() | {
            "pyproject_sha256": launcher._hash_file(ROOT / "pyproject.toml")
        }, indent=2), encoding="utf-8")
        temporary.replace(STATE)
        print("Source setup complete. Open PsyCoLab.bat and choose 1 - Launch PsyCoLab.")
        print("This environment is for development; it has no locked laboratory qualification.")
        return 0
    except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as error:
        print(f"Maintainer setup failed: {error}. Existing laboratory software was preserved.")
        return 1


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--check"], ["--repair"]):
        raise SystemExit("Usage: developer_setup.py [--check | --repair]")
    raise SystemExit(check_only() if sys.argv[1:] == ["--check"] else main(repair=sys.argv[1:] == ["--repair"]))
