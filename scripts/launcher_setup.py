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
PROFILE_DIR = ROOT / "requirements/windows-cp311"


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
    if path.is_symlink():
        raise ValueError("USER_env requirements must be a regular file.")
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
        arguments = [str(python), "-m", "pip", "install", "--disable-pip-version-check",
                     "--constraint", str(PROFILE_DIR / "core.constraints"), "--requirement", str(extra)]
        # Resolve conflicts/unavailable inputs before mutating USER_env. Laboratory
        # requirements remain owned by the researcher and are never rewritten.
        report = VENV / ".psycolab-extra-plan.json"
        report.unlink(missing_ok=True)
        _run(arguments + ["--dry-run", "--report", str(report)] + _wheelhouse_options())
        profile, _ = _profile()
        for item in json.loads(report.read_text(encoding="utf-8"))["install"]:
            name = item["metadata"]["name"].lower().replace("_", "-").replace(".", "-")
            if name in profile["core"] or name == "psychophysics-lab":
                raise ValueError(f"Laboratory requirements would replace approved {name}; "
                                 "the core was preserved. Revise the optional requirements and retest.")
        _run(arguments + _wheelhouse_options())
        print("Laboratory requirements checked against the fixed core; retest affected studies. Ready was not granted.")


def _write_state(pyproject_hash: str, requirements_hash: str | None = None, *, qualification: dict | None = None) -> None:
    values = {
        "pyproject_sha256": pyproject_hash,
        "python": ".".join(map(str, EXPECTED_PYTHON)),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    if VENV.name == "USER_env":
        values["user_requirements_sha256"] = requirements_hash
    if qualification is not None:
        values.update(schema_version=2, qualification=qualification, source_root=str(ROOT.resolve()))
        try:
            revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
            values['source_commit_at_setup'] = revision.stdout.strip() if revision.returncode == 0 else None
        except OSError:
            values['source_commit_at_setup'] = None
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, indent=2), encoding="utf-8")
    temporary.replace(STATE)


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


def _profile() -> tuple[dict, str]:
    profile_path = PROFILE_DIR / "profile.json"
    raw = profile_path.read_bytes()
    profile = json.loads(raw)
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise ValueError("Unsupported Windows environment profile.")
    for name, expected in profile["files"].items():
        path = PROFILE_DIR / name
        if path.parent != PROFILE_DIR or _hash_file(path) != expected:
            raise ValueError(f"Reviewed dependency file changed: {name}. Use a reviewed checkout/profile; no upgrade was attempted.")
    constraints = dict(line.split("==", 1) for line in
                       (PROFILE_DIR / "core.constraints").read_text(encoding="utf-8").splitlines()
                       if line.strip() and not line.startswith("#"))
    if constraints != profile["core"]:
        raise ValueError("Core constraints differ from the reviewed environment profile.")
    return profile, hashlib.sha256(raw).hexdigest()


def _inspect_interpreter(python: Path) -> dict:
    code = r"""
import hashlib,json,os,struct,sys
from pathlib import Path
base=Path(sys.base_prefix)
required=set(json.loads(sys.argv[1]));sealed=hashlib.sha256()
def digest(name):
    p=base/name
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
records=[]
for p in sorted((base/'conda-meta').glob('*.json')):
    r=json.loads(p.read_text(encoding='utf-8'))
    records.append({k:r.get(k) for k in ('name','version','build','sha256')})
    if r.get('name') in required:
        for name in sorted(r.get('files', [])):
            if not name.lower().endswith(('.exe','.dll','.pyd')):continue
            file=Path(os.path.abspath(base/name))
            if not file.is_relative_to(base.resolve()) or not file.is_file():raise ValueError('Missing/unsafe interpreter file: '+name)
            sealed.update(name.encode());sealed.update(hashlib.sha256(file.read_bytes()).digest())
print(json.dumps(dict(implementation=sys.implementation.name,version=list(sys.version_info[:3]),
    bits=struct.calcsize('P')*8,platform=sys.platform,distribution=sys.version,
    exe_sha256=digest('python.exe'),dll_sha256=digest('python311.dll'),native=records,native_fingerprint=sealed.hexdigest())))
"""
    names = [row['name'] for row in json.loads((PROFILE_DIR / 'interpreter-artifacts.json').read_text(encoding='utf-8'))]
    result = subprocess.run([str(python), "-I", "-B", "-c", code, json.dumps(names)], cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def _validate_interpreter(identity: dict) -> None:
    profile, _ = _profile()
    expected = profile["python"]
    for key in ("implementation", "version", "bits", "exe_sha256", "dll_sha256", "native_fingerprint"):
        if identity.get(key) != expected[key]:
            raise ValueError(f"Python {key} differs from qualified profile {profile['id']}. "
                             "Use the documented interpreter in a new checkout; existing environments were preserved.")
    if identity.get("platform") != "win32" or expected["distribution"] not in identity.get("distribution", ""):
        raise ValueError("The qualified Windows conda-forge interpreter is required; no global Python was changed.")
    installed = {row['name']: row for row in identity['native']}
    for row in json.loads((PROFILE_DIR / "interpreter-artifacts.json").read_text(encoding="utf-8")):
        actual = installed.get(row['name'], {})
        if actual.get('sha256') != row['sha256']:
            raise ValueError(f"Interpreter support artifact differs: {row['name']}. Preserve this environment and use the documented profile.")


def _environment_evidence(python: Path) -> dict:
    profile, digest = _profile()
    identity = _inspect_interpreter(python)
    _validate_interpreter(identity)
    code = r"""
import base64,hashlib,importlib.metadata as m,json,os,re,sys
from pathlib import Path
core=json.loads(sys.argv[1]);allowed=json.loads(sys.argv[2]);strict=sys.argv[3]=='True'
normal=lambda s:re.sub(r'[-_.]+','-',s).lower()
inventory={}
for d in m.distributions():
    name=normal(d.metadata['Name'])
    if name=='psychophysics-lab':continue
    if name in inventory and inventory[name]!=d.version:raise ValueError('Ambiguous distribution: '+name)
    inventory[name]=d.version
for name,version in core.items():
    if inventory.get(name)!=version:raise ValueError(f'Expected {name}=={version}; found {inventory.get(name)}. No dependency repair attempted.')
if strict and any(n not in allowed or allowed[n]!=v for n,v in inventory.items()):
    raise ValueError('Unexpected package/version in the qualified main environment; use USER_env for laboratory extras.')
digest=hashlib.sha256()
prefix=Path(sys.prefix).resolve()
for name in sorted(core):
    d=m.distribution(name)
    if not d.files:raise ValueError('Missing installed RECORD: '+name)
    for f in sorted(d.files,key=str):
        if str(f).endswith('.pyc'):continue
        p=Path(os.path.abspath(d.locate_file(f)))
        if not p.is_relative_to(prefix) or not p.is_file():raise ValueError('Missing/unsafe installed file: '+str(f))
        raw=p.read_bytes()
        if f.hash:
            h=hashlib.new(f.hash.mode,raw).digest()
            if base64.urlsafe_b64encode(h).decode().rstrip('=')!=f.hash.value:raise ValueError('Installed file hash mismatch: '+str(f))
        digest.update((name+'/'+str(f)).encode());digest.update(hashlib.sha256(raw).digest())
try:
    project=m.distribution('psychophysics-lab')
    project_identity=dict(version=project.version,editable_origin=json.loads(project.read_text('direct_url.json') or '{}'))
except m.PackageNotFoundError:
    project_identity=None
print(json.dumps(dict(inventory=inventory,core_fingerprint=digest.hexdigest(),project=project_identity)))
"""
    result = subprocess.run([str(python), "-I", "-B", "-c", code, json.dumps(profile['core']),
        json.dumps(profile['core'] | profile['development']), str(VENV.name != 'USER_env')],
        cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip().splitlines()[-1])
    evidence = json.loads(result.stdout)
    # Native identities use artifact hashes, not installation-location equality.
    evidence.update(profile_id=profile['id'], profile_sha256=digest,
        interpreter={k:identity[k] for k in ('implementation','version','bits','platform','distribution','exe_sha256','dll_sha256','native_fingerprint')})
    return evidence


def _wheelhouse_options() -> list[str]:
    value = os.environ.get("PSYCOLAB_WHEELHOUSE")
    if not value:
        return []
    path = Path(value).resolve()
    if not path.is_dir():
        raise ValueError("PSYCOLAB_WHEELHOUSE must name an existing directory of reviewed wheels.")
    return ["--no-index", "--find-links", str(path)]


def _install_locked(python: Path) -> dict:
    profile, _ = _profile()
    evidence = {}
    reports = VENV / ".psycolab-install-reports"
    reports.mkdir(exist_ok=True)
    from urllib.parse import unquote, urlsplit
    for section in ("build", "runtime"):
        report = reports / (section + ".json")
        _run([str(python), "-I", "-B", "-m", "pip", "--isolated", "install", "--disable-pip-version-check",
              "--no-cache-dir", "--no-compile", "--force-reinstall", "--only-binary=:all:", "--require-hashes",
              "--report", str(report), "--requirement", str(PROFILE_DIR / (section + ".lock")), *_wheelhouse_options()])
        for item in json.loads(report.read_text(encoding="utf-8"))['install']:
            name = item['metadata']['name'].lower().replace('_', '-')
            expected = profile['artifacts'][name]
            download = item['download_info']
            filename = unquote(urlsplit(download['url']).path.rsplit('/', 1)[-1])
            actual = download['archive_info'].get('hashes', {}).get('sha256')
            if (item['metadata']['version'] != expected['version'] or filename != expected['filename'] or actual != expected['sha256']):
                raise ValueError('Unexpected installed artifact: ' + name)
            evidence[name] = dict(version=expected['version'], filename=filename, sha256=actual)
    if set(evidence) != set(profile['core']):
        raise ValueError("Installation report is missing approved core artifacts.")
    return evidence


def _install_editable(python: Path) -> None:
    _run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-deps", "--no-build-isolation",
          "--editable", str(ROOT)])


def main() -> int:
    if sys.version_info[:2] != EXPECTED_PYTHON:
        print(f"ERROR: launcher_setup.py must be run with Python 3.11; received {sys.version_info.major}.{sys.version_info.minor}.")
        return 2
    pending = VENV / ".psycolab-setup.pending.json"
    try:
        if (VENV.is_symlink() or VENV.resolve().parent != ROOT.resolve()
                or STATE.is_symlink() or pending.is_symlink()):
            raise ValueError("Setup paths must belong to this checkout, not links to another installation.")
        profile, digest = _profile()
        _validate_interpreter(_inspect_interpreter(Path(sys.executable)))
        pyproject_hash = _hash_file(PYPROJECT)
        state = _load_state()
        fresh = not VENV.exists()
        retry = False
        if not fresh and not STATE.exists() and pending.is_file():
            attempt = json.loads(pending.read_text(encoding='utf-8'))
            retry = attempt == dict(profile_sha256=digest, pyproject_sha256=pyproject_hash, source_root=str(ROOT.resolve()))
        if not fresh and not retry:
            if (state.get('schema_version') != 2 or state.get('source_root') != str(ROOT.resolve())
                    or state.get('pyproject_sha256') != pyproject_hash
                    or state.get('qualification', {}).get('profile_sha256') != digest):
                raise ValueError("Installation/profile/specification changed or is not qualified. Existing environment preserved. "
                                 "Retain the old checkout and prepare a new isolated checkout with the reviewed profile; no upgrade was attempted.")
            recorded = state['qualification'].get('artifacts', {})
            if set(recorded) != set(profile['core']) or any(
                recorded[name] != {key: profile['artifacts'][name][key] for key in ('version', 'filename', 'sha256')}
                for name in profile['core']):
                raise ValueError("Approved installed-artifact evidence is missing or changed; existing environment preserved.")
        if fresh or (retry and not _venv_python(VENV).exists()):
            _run([sys.executable, '-m', 'venv', str(VENV)])
            pending.write_text(json.dumps(dict(profile_sha256=digest, pyproject_sha256=pyproject_hash,
                                               source_root=str(ROOT.resolve()))), encoding='utf-8')
        python = _venv_python(VENV)
        _validate_interpreter(_inspect_interpreter(python))
        artifact_evidence = state.get('qualification', {}).get('artifacts', {})
        if fresh or retry:
            artifact_evidence = _install_locked(python)
            _install_editable(python)
        current = _environment_evidence(python)
        if not fresh and not retry:
            old = state['qualification']
            if (current['inventory'] != old['inventory'] or current['core_fingerprint'] != old['core_fingerprint']
                    or current['interpreter'] != old['interpreter']):
                raise ValueError("Installed packages/files differ from approved setup state. No automatic repair attempted; preserve this checkout and prepare a clean one.")
        extra = _extra_requirements()
        extra_hash = _hash_file(extra) if extra is not None else None
        extras_changed = extra is not None and state.get('user_requirements_sha256') != extra_hash
        repaired = False
        try:
            _validate_environment(python)
        except InstallationIdentityError:
            if fresh or retry:
                raise
            print("Refreshing only editable source metadata; verified dependencies are unchanged.")
            _install_editable(python)
            _validate_environment(python)
            repaired = True
        if fresh or retry or extras_changed:
            _install_extra_requirements(python, extra)
            _validate_environment(python)
        if fresh or retry or extras_changed or repaired:
            current = _environment_evidence(python)
            current['artifacts'] = artifact_evidence
            _write_state(pyproject_hash, extra_hash, qualification=current)
            pending.unlink(missing_ok=True)
        else:
            print(f"Reviewed profile and dependencies unchanged; reusing {VENV.name}.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: setup validation failed: {error}. No application was started. "
              "Existing laboratory source, configuration and data were not changed. "
              "For an incomplete new setup, obtain the reviewed artifacts and retry; for an existing mismatch use a separate checkout. "
              "See docs/WINDOWS_ENVIRONMENT.md.")
        return 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--user-env"]:
        select_environment("USER_env")
    elif sys.argv[1:]:
        print("Usage: launcher_setup.py [--user-env]")
        raise SystemExit(2)
    raise SystemExit(main())
