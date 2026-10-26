"""Real isolated-interpreter identity checks; simulated pip, no network installs."""
import json
from pathlib import Path
import subprocess
import venv

import pytest

from scripts import launcher_setup as launcher


@pytest.fixture(params=[".venv", "USER_env"])
def installation(tmp_path, monkeypatch, request):
    root = tmp_path / "checkout with spaces & unicode é"
    root.mkdir()
    project = root / "pyproject.toml"
    project.write_text('[project]\nname="psychophysics-lab"\ndynamic=["version"]\n')
    source = root / "src/psychophysics_lab/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text('__version__ = "0.2.2"\n')
    monkeypatch.setattr(launcher, "ROOT", root)
    monkeypatch.setattr(launcher, "PYPROJECT", project)
    monkeypatch.setattr(launcher, "VENV", root / request.param)
    monkeypatch.setattr(launcher, "STATE", launcher.VENV / ".psycolab-setup.json")
    venv.EnvBuilder(with_pip=False).create(launcher.VENV)
    python = launcher._venv_python(launcher.VENV)
    site = Path(subprocess.check_output(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        text=True).strip())
    metadata = site / "psychophysics_lab-0.2.2.dist-info"
    metadata.mkdir()
    pth = site / "psycolab-fixture.pth"
    direct = metadata / "direct_url.json"

    def installed(version="0.2.2", origin=root):
        (metadata / "METADATA").write_text(
            f'Metadata-Version: 2.1\nName: psychophysics-lab\nVersion: {version}\n')
        direct.write_text(json.dumps({"url": origin.as_uri(), "dir_info": {"editable": True}}))
        pth.write_text("import sys; sys.path.append(" + ascii(str(origin / "src")) + ")\n",
                       encoding="ascii")

    installed()
    extra = root / "user_requirements.txt"
    extra.write_text("# Laboratory-owned requirements must stay untouched.\n", encoding="utf-8")
    extra_hash = launcher._hash_file(extra) if request.param == "USER_env" else None
    launcher._write_state(launcher._hash_file(project), extra_hash)
    calls = []
    behavior = {"refresh": lambda: installed("0.2.2")}
    real_run = launcher._run

    def command(args, **kwargs):
        calls.append(args)
        if "-c" in args and args[-1] == str(root):
            return real_run(args, **kwargs)  # actual importlib and editable path lookup
        if "install" in args:
            behavior["refresh"]()
        # Dependency import/pip commands are already covered by launcher tests;
        # this network-free fixture intentionally has no runtime dependencies.
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(launcher, "_run", command)
    return dict(root=root, source=source, project=project, python=python,
                metadata=metadata, direct=direct, pth=pth, installed=installed,
                calls=calls, behavior=behavior, extra=extra)


def installs(fixture):
    return [args for args in fixture["calls"] if "install" in args]


def assert_project_only_refresh(fixture):
    commands = installs(fixture)
    assert len(commands) == 1
    assert commands[0][-2:] == ["--editable", str(fixture["root"])]
    assert {"--no-deps", "--no-build-isolation"}.issubset(commands[0])
    assert not any("--upgrade" in c or "--requirement" in c for c in fixture["calls"])


def test_source_version_change_refreshes_metadata_without_dependency_changes(installation):
    f = installation
    project_before = f["project"].read_bytes()
    extra_before = f["extra"].read_bytes()
    f["source"].write_text('__version__ = "0.3.0"\n')
    f["behavior"]["refresh"] = lambda: f["installed"]("0.3.0")
    with pytest.raises(launcher.InstallationIdentityError):
        launcher._validate_installation_identity(f["python"])
    assert launcher.main() == 0
    assert_project_only_refresh(f)
    assert f["project"].read_bytes() == project_before
    assert f["extra"].read_bytes() == extra_before
    launcher._validate_installation_identity(f["python"])
    f["calls"].clear()
    assert launcher.main() == 0
    assert not installs(f)


def test_matching_identity_reuses_environment_and_state(installation):
    f = installation
    before = launcher.STATE.read_bytes()
    assert launcher.main() == 0
    assert not installs(f)
    assert launcher.STATE.read_bytes() == before
    assert not any(c[1:3] == ["-m", "venv"] for c in f["calls"])


def test_unexpected_editable_checkout_is_detected_and_repaired(installation, monkeypatch):
    f = installation
    other = f["root"].parent / "other checkout"
    other_source = other / "src/psychophysics_lab/__init__.py"
    other_source.parent.mkdir(parents=True)
    other_source.write_text('__version__ = "0.2.2"\n')
    f["installed"](origin=other)
    # PYTHONPATH must not mask the wrong editable installation.
    monkeypatch.setenv("PYTHONPATH", str(f["root"] / "src"))
    with pytest.raises(launcher.InstallationIdentityError):
        launcher._validate_installation_identity(f["python"])
    assert launcher.main() == 0
    assert_project_only_refresh(f)
    launcher._validate_installation_identity(f["python"])
    assert other_source.read_text() == '__version__ = "0.2.2"\n'


def test_runtime_path_override_cannot_hide_behind_correct_installation(installation, monkeypatch):
    f = installation
    other = f["root"].parent / "runtime shadow"
    source = other / "psychophysics_lab/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text('__version__ = "0.2.2"\n')
    monkeypatch.setenv("PYTHONPATH", str(other))
    state_before = launcher.STATE.read_bytes()
    assert launcher.main() == 1
    assert launcher.STATE.read_bytes() == state_before
    monkeypatch.delenv("PYTHONPATH")
    f["calls"].clear()
    assert launcher.main() == 0
    assert not installs(f)


@pytest.mark.parametrize("failure", ["command", "ineffective", "post_refresh_validation"])
def test_failed_refresh_retains_state_and_retries_safely(installation, failure):
    f = installation
    f["source"].write_text('__version__ = "0.3.0"\n')
    before = launcher.STATE.read_bytes()

    def fail():
        raise subprocess.CalledProcessError(1, [str(f["python"]), "-m", "pip", "install"])

    if failure == "command":
        f["behavior"]["refresh"] = fail
    elif failure == "post_refresh_validation":
        # A successful pip exit does not justify accepting incompatible source.
        f["behavior"]["refresh"] = lambda: f["installed"]("0.3.0", f["root"].parent)
    assert launcher.main() == 1
    assert launcher.STATE.read_bytes() == before
    assert_project_only_refresh(f)
    f["calls"].clear()
    f["behavior"]["refresh"] = lambda: f["installed"]("0.3.0")
    assert launcher.main() == 0
    assert_project_only_refresh(f)


@pytest.mark.parametrize("origin", ["missing", "noneditable", "wrong_root"])
def test_matching_version_and_import_do_not_hide_wrong_metadata_origin(installation, origin):
    f = installation
    if origin == "missing":
        f["direct"].unlink()
    else:
        f["direct"].write_text(json.dumps({
            "url": (f["root"].parent if origin == "wrong_root" else f["root"]).as_uri(),
            "dir_info": {"editable": origin != "noneditable"},
        }))
    with pytest.raises(launcher.InstallationIdentityError):
        launcher._validate_installation_identity(f["python"])


def test_missing_distribution_is_not_accepted_as_successful_import(installation):
    f = installation
    (f["metadata"] / "METADATA").unlink()
    with pytest.raises(launcher.InstallationIdentityError):
        launcher._validate_installation_identity(f["python"])


def test_identity_repair_leaves_external_laboratory_files_untouched(installation, monkeypatch):
    f = installation
    lab = f["root"].parent / "independent laboratory"
    protected = {}
    for name in ("configuration/calibration.json", "data/trials.csv",
                 "extensions/experiment.py", "extensions/readiness.json"):
        path = lab / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"laboratory-owned fixture\n")
        protected[path] = path.read_bytes()
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(lab / "configuration"))
    monkeypatch.setenv("PSYCOLAB_DATA_DIR", str(lab / "data"))
    f["source"].write_text('__version__ = "0.3.0"\n')
    f["behavior"]["refresh"] = lambda: f["installed"]("0.3.0")
    assert launcher.main() == 0
    assert {p: p.read_bytes() for p in lab.rglob("*") if p.is_file()} == protected
