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
    destination = ROOT / f"{VENV.name}.incompatible-{stamp}"
    print(f"Existing {VENV.name} is not a Python 3.11 environment; preserving it as {destination.name}")
    shutil.move(str(VENV), str(destination))


def _load_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _extra_requirements() -> Path | None:
    """USER_env-only optional libraries for researcher-authored Python files."""
    if VENV.name != "USER_env":
        return None
    path = ROOT / "user_requirements.txt"
    if not path.exists():
        path.write_text(
            "# Optional packages for user-authored Python scripts.\n"
            "# One pip requirement per line; relaunch run_user_env.bat.\n",
            encoding="utf-8",
        )
    if path.is_symlink() or not path.is_file():
        raise ValueError("USER_env requirements must be a regular file.")
    return path


def _install_extra_requirements(python: Path, extra: Path | None) -> None:
    if extra is not None:
        _run([str(python), "-m", "pip", "install",
              "--disable-pip-version-check", "--requirement", str(extra)])


def _write_state(pyproject_hash: str, requirements_hash: str | None = None) -> None:
    values = {
        "pyproject_sha256": pyproject_hash,
        "python": ".".join(map(str, EXPECTED_PYTHON)),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    if VENV.name == "USER_env":
        values["user_requirements_sha256"] = requirements_hash
    STATE.write_text(json.dumps(values, indent=2), encoding="utf-8")


class InstallationIdentityError(subprocess.CalledProcessError):
    """The environment does not identify this editable source checkout."""


def _validate_installation_identity(python: Path) -> None:
    # -I excludes cwd/PYTHONPATH/user-site masking; the selected environment's
    # editable installation must supply both the import and its metadata.
    code = """
import ast
from importlib.metadata import distribution
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from urllib.request import url2pathname
import psychophysics_lab as package

root = Path(sys.argv[1]).resolve()
source = root / 'src' / 'psychophysics_lab' / '__init__.py'
if Path(package.__file__).resolve() != source.resolve():
    raise RuntimeError(f'PsyCoLab imported from unexpected checkout: {package.__file__}')
# The project's dynamic version is a literal in this file. Read it independently
# of cached imports, without executing any scientific modules.
tree = ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
version = next(ast.literal_eval(node.value) for node in tree.body
               if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == '__version__'
                       for target in node.targets))
dist = distribution('psychophysics-lab')
if package.__version__ != version or dist.version != version:
    raise RuntimeError(f'PsyCoLab version mismatch: source={version}, '
                       f'import={package.__version__}, metadata={dist.version}')
if sys.flags.isolated:
    origin = json.loads(dist.read_text('direct_url.json') or '{}')
    url = urlsplit(origin.get('url', ''))
    origin_path = url2pathname(('//' + url.netloc if url.netloc else '') + url.path)
    if (url.scheme != 'file' or origin.get('dir_info', {}).get('editable') is not True
            or Path(origin_path).resolve() != root):
        raise RuntimeError(f'PsyCoLab metadata is not editable from {root}: {origin}')
print(f'PsyCoLab editable identity OK: {version} from {root}')
"""
    try:
        _run([str(python), "-I", "-c", code, str(ROOT)])
        # Also check ordinary launch semantics: inherited PYTHONPATH/user-site
        # must not redirect an otherwise correct editable install at runtime.
        _run([str(python), "-c", code, str(ROOT)])
    except subprocess.CalledProcessError as error:
        raise InstallationIdentityError(error.returncode, error.cmd) from error


def _validate_environment(python: Path) -> None:
    _validate_installation_identity(python)
    _run([str(python), "-m", "pip", "check"])
    code = (
        "import psychophysics_lab, numpy, pyglet, textual; "
        "print('PsyCoLab imports OK'); "
        "print('numpy', numpy.__version__); "
        "print('pyglet', pyglet.version)"
    )
    _run([str(python), "-c", code])


def select_environment(name: str) -> None:
    """Target one of the two supported local environments, never arbitrary paths.

    The default .venv setup is unchanged. USER_env uses the same dependency
    version tracking and validation but has its own interpreter and setup state.
    """
    if name not in {".venv", "USER_env"}:
        raise ValueError("Unsupported PsyCoLab environment name.")
    global VENV, STATE
    VENV = ROOT / name
    STATE = VENV / ".psycolab-setup.json"


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
        print(f"Creating {VENV.name} with Python 3.11...")
        _run([sys.executable, "-m", "venv", str(VENV)])

    venv_python = _venv_python(VENV)
    if _python_version(venv_python) != EXPECTED_PYTHON:
        print(f"ERROR: newly created {VENV.name} is not a Python 3.11 environment.")
        return 2

    pyproject_hash = _hash_file(PYPROJECT)
    extra = _extra_requirements()
    extra_hash = _hash_file(extra) if extra is not None else None
    state = _load_state()
    needs_install = (state.get("pyproject_sha256") != pyproject_hash or
                     (extra is not None and state.get("user_requirements_sha256") != extra_hash))

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

        try:
            _install_extra_requirements(venv_python, extra)
            _validate_environment(venv_python)
        except subprocess.CalledProcessError:
            print("Dependency installation/validation failed. Review errors above; no script was started.")
            return 1
        _write_state(pyproject_hash, extra_hash)
    else:
        print(f"Dependency configuration is unchanged; reusing {VENV.name}.")
        try:
            _validate_environment(venv_python)
        except subprocess.CalledProcessError as error:
            identity_only = isinstance(error, InstallationIdentityError)
            print("Environment validation failed; reinstalling the editable project...")
            # Identity repair must not resolve lab/runtime dependencies or upgrade
            # build tools. If existing build tools cannot refresh it, fail safely.
            refresh_options = ["--no-deps", "--no-build-isolation"] if identity_only else []
            try:
                _run(
                    [
                        str(venv_python),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        *refresh_options,
                        "--editable",
                        str(ROOT),
                    ]
                )
                if not identity_only:
                    _install_extra_requirements(venv_python, extra)
                _validate_environment(venv_python)
                _write_state(pyproject_hash, extra_hash)
            except subprocess.CalledProcessError:
                print("Editable refresh/validation failed; no script was started. "
                      "Review the error above and retry setup after correcting it.")
                return 1

    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--user-env"]:
        select_environment("USER_env")
    elif sys.argv[1:]:
        print("Usage: launcher_setup.py [--user-env]")
        raise SystemExit(2)
    raise SystemExit(main())
