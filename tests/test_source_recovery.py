"""Real Windows batch/native/install boundaries in disposable source checkouts.

No physical experiment is run. The disposable application's entry point drives
the real TUI headlessly and exits, so CI never needs to type into a terminal.
"""
import hashlib
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import venv
from unittest.mock import patch

import pytest

from test_windows_guided_setup import native
from _windows_launcher_process import run_launcher

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows source recovery")


@pytest.fixture(scope="module")
def wheels(tmp_path_factory):
    supplied = os.environ.get("PSYCOLAB_RECOVERY_TEST_WHEELS")
    if supplied:
        return Path(supplied)
    folder = tmp_path_factory.mktemp("recovery wheels")
    subprocess.run([sys.executable, "-I", "-m", "pip", "download", "--require-hashes",
                    "--only-binary=:all:", "-r", str(ROOT / "requirements/windows-cp311/build.lock"),
                    "-r", str(ROOT / "requirements/windows-cp311/development.lock"),
                    "--dest", str(folder)], check=True, capture_output=True)
    return folder


@pytest.fixture
def source(tmp_path):
    # Keep the native .NET Framework and venv paths below legacy MAX_PATH.
    with tempfile.TemporaryDirectory(prefix="psy-repair-") as short:
        folder = Path(short)
        root = folder / "source with spaces é"
        root.mkdir()
        for name in ("scripts", "packaging", "requirements", "src", "configs"):
            shutil.copytree(ROOT / name, root / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        for name in ("pyproject.toml", "README.md", ".gitignore", "PsyCoLab.bat"):
            shutil.copy2(ROOT / name, root / name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        old = root / ".venv"
        (old / "Scripts").mkdir(parents=True)
        (old / "Scripts/python.exe").write_bytes(b"legacy interpreter is never executed")
        (old / "personal-evidence").write_bytes(b"preserve original environment contents")
        record = {"pyproject_sha256": hashlib.sha256((root / "pyproject.toml").read_bytes()).hexdigest(),
                  "python": "3.11", "updated_utc": "2026-10-16T10:15:13+00:00"}
        (old / ".psycolab-setup.json").write_text(json.dumps(record))
        outside = folder / "research data"
        outside.mkdir()
        (outside / "calibration.json").write_bytes(b"unchanged calibration")
        (outside / "results.csv").write_bytes(b"unchanged results")
        runs = folder / "tui-starts.txt"
        # This is confined to the fixture. The production entry point is unchanged.
        (root / "src/psychophysics_lab/__main__.py").write_text(
            "import asyncio,sys\nfrom pathlib import Path\n"
            "from psychophysics_lab import app as launcher\n"
            "from psychophysics_lab.ui import setup\n"
            "def headless(**options):\n"
            " async def mount():\n"
            "  app=setup.PsyCoLabSetupApp(**options)\n"
            "  async with app.run_test(size=(130,45)) as pilot:\n"
            "   await pilot.pause()\n"
            "   assert app.query_one('#participant') is not None\n"
            f"   p=Path({str(runs)!r})\n"
            "   p.write_text((p.read_text() if p.exists() else '')+'mounted\\n')\n"
            "   app.exit(None)\n"
            " asyncio.run(mount())\n"
            " return None\n"
            "setup.run_setup_tui=headless\n"
            "raise SystemExit(launcher.main(sys.argv[1:]))\n", encoding="utf-8")
        env = os.environ | {
            "PSYCOLAB_BOOTSTRAP_PYTHON": str(Path(sys._base_executable)),
            "PSYCOLAB_CONFIG_DIR": str(folder / "research config"),
            "PSYCOLAB_DATA_DIR": str(outside),
        }
        yield root, outside, runs, env


def batch(source, *args, launcher="PsyCoLab.bat", input_text=None, timeout=180, **overrides):
    root, _, _, env = source
    with patch.dict(os.environ, env | overrides, clear=True):
        try:
            return run_launcher(["cmd.exe", "/d", "/c", "call", str(root / launcher), *args],
                                cwd=root, timeout=timeout, input_text=input_text)
        except subprocess.TimeoutExpired as error:
            pytest.fail(f"Launcher timed out. Output: {error.output}\n{error.stderr}")


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob("*") if p.is_file()}


def short_path(path):
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    api.GetShortPathNameW.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    length = api.GetShortPathNameW(str(path), buffer, len(buffer))
    assert 0 < length < len(buffer)
    if os.path.normcase(buffer.value) == os.path.normcase(str(path)):
        pytest.skip("This volume does not provide a distinct short-name alias")
    return buffer.value


def test_real_batch_legacy_repair_repeat_corruption_and_restore(source, wheels):
    root, data, runs, env = source
    env["PSYCOLAB_WHEELHOUSE"] = str(wheels)
    old = snapshot(root / ".venv")
    research = snapshot(data)
    result = batch(source, launcher="PsyCoLab.bat", input_text="2\nR\nYES\n1\n4\n")
    assert result.returncode == 0, result.stdout + result.stderr
    backups = list(root.glob(".venv-recovery-backup-*"))
    assert len(backups) == 1 and snapshot(backups[0]) == old
    assert snapshot(data) == research and runs.read_text() == "mounted\n"
    state = json.loads((root / ".venv-dev/.psycolab-development.json").read_text())
    assert state["mode"] == "development" and "qualification" not in state
    log = root / ".psycolab-recovery/repair.log"
    log_before = log.read_bytes()
    for args in (("--launch",), ("--repair",)):
        result = batch(source, *args)
        assert result.returncode == 0, result.stdout + result.stderr
    # Repair exits without acquisition; launch remains an explicit action.
    assert runs.read_text() == "mounted\n" * 2
    assert batch(source, "--launch").returncode == 0
    assert runs.read_text() == "mounted\n" * 3
    assert log.read_bytes() == log_before and list(root.glob(".venv-recovery-backup-*")) == backups
    # RECORD integrity detects tampering even if imports and pip check would pass.
    changed = root / ".venv-dev/Lib/site-packages/numpy/__init__.py"
    good = changed.read_bytes()
    changed.write_bytes(good + b"\n# corrupted fixture package\n")
    check = subprocess.run([str(root / ".venv-dev/Scripts/python.exe"), "-I", "-B",
                            str(root / "scripts/developer_setup.py"), "--check"],
                           capture_output=True, timeout=30)
    assert check.returncode != 0
    result = batch(source, "--repair")
    assert result.returncode == 0, result.stdout + result.stderr
    assert runs.read_text() == "mounted\n" * 3
    assert batch(source, "--launch").returncode == 0
    assert changed.read_bytes() == good and runs.read_text() == "mounted\n" * 4
    # Bootstrap from CPython's bundled pip even if the target pip cannot import.
    (root / ".venv-dev/Lib/site-packages/pip/__main__.py").unlink()
    result = batch(source, "--repair")
    assert result.returncode == 0, result.stdout + result.stderr
    assert runs.read_text() == "mounted\n" * 4
    assert batch(source, "--launch").returncode == 0
    assert runs.read_text() == "mounted\n" * 5
    assert snapshot(backups[0]) == old and snapshot(data) == research
    for args, text in (((), "2\nS\nYES\n4\n"), (("--restore",), None)):
        result = batch(source, *args, input_text=text)
        assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(root / ".venv") == old
    assert len(list(root.glob(".venv-dev-recovery-backup-*"))) == 1
    assert snapshot(data) == research
    # Every environment, backup, log and local preference is excluded by shared rules.
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True)
    assert not any(p.startswith((".venv", ".psycolab-recovery", ".psycolab_local")) for p in untracked.splitlines())


def test_real_batch_offline_failure_retries_same_backup(source, wheels, tmp_path):
    root, _, runs, env = source
    empty = tmp_path / "empty wheel folder"
    empty.mkdir()
    env["PSYCOLAB_WHEELHOUSE"] = str(empty)
    old = snapshot(root / ".venv")
    for _ in range(2):
        result = batch(source, "--repair")
        assert result.returncode != 0
        assert len(list(root.glob(".venv-recovery-backup-*"))) == 1
        assert not runs.exists()
    backup = next(root.glob(".venv-recovery-backup-*"))
    assert snapshot(backup) == old
    assert (root / ".venv-dev/.psycolab-development.pending.json").exists()
    env["PSYCOLAB_WHEELHOUSE"] = str(wheels)
    result = batch(source, "--repair")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not runs.exists()
    assert batch(source, "--launch").returncode == 0
    assert snapshot(backup) == old and runs.read_text() == "mounted\n"


def test_failed_startup_check_is_rechecked_before_recovery_completes(source, wheels):
    root, _, runs, env = source
    env["PSYCOLAB_WHEELHOUSE"] = str(wheels)
    attempts = root.parent / "startup check attempts.txt"
    entry = root / "src/psychophysics_lab/__main__.py"
    original = entry.read_text(encoding="utf-8")
    entry.write_text("import sys\nfrom pathlib import Path\n"
                     "if '--help' in sys.argv:\n"
                     f" p=Path({str(attempts)!r})\n"
                     " count=int(p.read_text())+1 if p.exists() else 1\n"
                     " p.write_text(str(count))\n"
                     " if count==1: raise SystemExit(9)\n" + original, encoding="utf-8")
    result = batch(source, "--repair")
    assert result.returncode != 0 and "exit code 9" in result.stdout
    assert not runs.exists() and attempts.read_text() == "1"
    assert json.loads((root / ".psycolab-recovery/state.json").read_text())["phase"] == "setup"
    result = batch(source, "--repair")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not runs.exists()
    assert batch(source, "--launch").returncode == 0
    assert attempts.read_text() == "2" and runs.read_text() == "mounted\n"
    assert json.loads((root / ".psycolab-recovery/state.json").read_text())["phase"] == "verified"
    assert len(list(root.glob(".venv-recovery-backup-*"))) == 1


@pytest.mark.parametrize("refusal", ["missing_python", "qualified", "incomplete_qualified", "managed", "unowned_development"])
def test_real_batch_refuses_before_moving_original(source, refusal):
    root, _, _, env = source
    if refusal == "missing_python":
        env["PSYCOLAB_BOOTSTRAP_PYTHON"] = str(root.parent / "missing-python.exe")
    elif refusal == "managed":
        (root.parent / "installation.json").write_text("{}")
    elif refusal == "unowned_development":
        (root / ".venv-dev").mkdir()
        (root / ".venv-dev/personal-file").write_text("do not replace")
    else:
        record = root / ".venv/.psycolab-setup.json"
        value = json.loads(record.read_text()) | {"schema_version": 2}
        if refusal == "qualified":
            value["qualification"] = {"evidence": "never reinterpret as development"}
        record.write_text(json.dumps(value))
    old = snapshot(root / ".venv")
    result = batch(source, "--repair")
    assert result.returncode != 0
    assert snapshot(root / ".venv") == old and not list(root.glob(".venv-recovery-backup-*"))
    assert not (root / ".psycolab-recovery/state.json").exists()


def test_real_batch_resumes_rename_checkpoint_and_restores_without_install(source):
    root, _, _, env = source
    original = snapshot(root / ".venv")
    backup = ".venv-recovery-backup-" + uuid.uuid4().hex
    journal = root / ".psycolab-recovery"
    journal.mkdir()
    state = {"schema_version": 1, "root": str(root), "backup": backup, "phase": "prepared",
             "record_sha256": hashlib.sha256((root / ".venv/.psycolab-setup.json").read_bytes()).hexdigest()}
    (journal / "state.json").write_text(json.dumps(state))
    # Simulate termination immediately after the atomic rename, before journal update.
    (root / ".venv").rename(root / backup)
    empty = root.parent / "empty wheels"
    empty.mkdir()
    env["PSYCOLAB_WHEELHOUSE"] = str(empty)
    result = batch(source, "--repair")
    assert result.returncode != 0 and len(list(root.glob(".venv-recovery-backup-*"))) == 1
    assert snapshot(root / backup) == original
    result = batch(source, "--restore")
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(root / ".venv") == original


@pytest.mark.parametrize("checkpoint", ["before_rename", "empty_development", "after_development_preserved", "after_original_restored"])
def test_restore_handles_interruption_checkpoints(source, checkpoint):
    root, _, _, _ = source
    old = snapshot(root / ".venv")
    backup = ".venv-recovery-backup-" + uuid.uuid4().hex
    retained = ".venv-dev-recovery-backup-" + uuid.uuid4().hex
    folder = root / ".psycolab-recovery"
    folder.mkdir()
    state = {"schema_version": 1, "root": str(root), "backup": backup, "phase": "prepared",
             "record_sha256": hashlib.sha256((root / ".venv/.psycolab-setup.json").read_bytes()).hexdigest()}
    if checkpoint != "before_rename":
        (root / ".venv").rename(root / backup)
        if checkpoint == "empty_development":
            state["phase"] = "setup"
            (root / ".venv-dev").mkdir()
        else:
            state |= {"phase": "restoring", "development_backup": retained}
            (root / retained).mkdir()
            (root / retained / "preserve").write_bytes(b"replacement environment")
        if checkpoint == "after_original_restored":
            (root / backup).rename(root / ".venv")
    (folder / "state.json").write_text(json.dumps(state))
    result = batch(source, "--restore")
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(root / ".venv") == old


def test_real_batch_restore_accepts_same_folder_short_name(source):
    root, _, _, _ = source
    before = snapshot(root / ".venv")
    alias = short_path(root)
    folder = root / ".psycolab-recovery"
    folder.mkdir()
    state = {"schema_version": 1, "root": alias, "phase": "prepared",
             "backup": ".venv-recovery-backup-" + uuid.uuid4().hex,
             "record_sha256": hashlib.sha256((root / ".venv/.psycolab-setup.json").read_bytes()).hexdigest()}
    (folder / "state.json").write_text(json.dumps(state))
    result = batch(source, "--restore")
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(root / ".venv") == before


def test_real_batch_write_permission_refusal_preserves_original(source):
    root, _, _, _ = source
    original = snapshot(root / ".venv")
    sid = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True).strip().split(',')[-1].strip('"')
    subprocess.run(["icacls", str(root), "/deny", "*" + sid + ":(WD,AD)"], check=True, capture_output=True)
    try:
        result = batch(source, "--repair")
        assert result.returncode != 0
        assert snapshot(root / ".venv") == original and not list(root.glob(".venv-recovery-backup-*"))
    finally:
        subprocess.run(["icacls", str(root), "/remove:d", "*" + sid], check=True, capture_output=True)


def test_native_window_offers_same_repair_and_suppresses_after_acquisition(native, source):
    root, _, _, _ = source
    diagnosis = {"root": str(root), "category": "qualification_legacy", "message": "older source setup"}
    form = native("recovery-form", json.dumps(diagnosis), root.parent).stdout
    assert "Repair older source installation [Recommended]" in form
    form = native("recovery-form", json.dumps(diagnosis | {"after_application": True}), root.parent).stdout
    assert "Repair older source installation" not in form


@pytest.mark.parametrize("alias", [False, True])
def test_real_batch_and_native_launch_refuse_concurrent_owner(native, source, alias):
    root, _, _, _ = source
    before = snapshot(root / ".venv")
    lock_root = short_path(root) if alias else str(root)
    held = subprocess.Popen([str(native.executable), "source-hold", lock_root, "30000"],
                            stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        assert held.stdout.readline().strip() == "held"
        result = batch(source, "--repair")
        assert result.returncode != 0
        result = native("source-launch", root, "no application should start", timeout=20)
        assert result.returncode != 0 and "already running" in result.stderr
        assert snapshot(root / ".venv") == before
        assert not (root / ".psycolab-recovery/state.json").exists()
    finally:
        held.terminate()
        held.wait(timeout=10)


def test_real_batch_detects_python_started_outside_launcher(source):
    root, _, _, _ = source
    venv.EnvBuilder(with_pip=False).create(root / ".venv")
    before = snapshot(root / ".venv")
    child = subprocess.Popen([str(root / ".venv/Scripts/python.exe"), "-I", "-c",
                              "import sys;print('running',flush=True);sys.stdin.readline()"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        assert child.stdout.readline().strip() == "running"
        result = batch(source, "--repair")
        assert result.returncode != 0
        assert snapshot(root / ".venv") == before and not list(root.glob(".venv-recovery-backup-*"))
    finally:
        child.communicate("\n", timeout=10)


def test_native_menu_survives_missing_python_and_returns_after_failed_launch(source):
    root, _, _, env = source
    before = snapshot(root / ".venv")
    env["PSYCOLAB_BOOTSTRAP_PYTHON"] = str(root.parent / "no Python.exe")
    result = batch(source, launcher="PsyCoLab.bat", input_text="1\n2\nB\n4\n", timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("\nPsyCoLab\n1 - Launch PsyCoLab") == 3
    assert "3 - Python Workspace" in result.stdout and "Python 3.11" in result.stdout
    assert snapshot(root / ".venv") == before and not list(root.glob(".venv-recovery-backup-*"))


def test_menu_initial_install_tui_return_and_python_workspace(source, wheels):
    root, _, runs, env = source
    (root / ".venv").rename(root.parent / "unrelated legacy fixture")
    env["PSYCOLAB_WHEELHOUSE"] = str(wheels)
    result = batch(source, launcher="PsyCoLab.bat", input_text="2\nI\nYES\n1\n1\n4\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "\x1b[?1049h" not in result.stdout and "██████" not in result.stdout
    assert result.stdout.count("\nPsyCoLab\n1 - Launch PsyCoLab") == 4
    assert runs.read_text() == "mounted\n" * 2
    log_before = (root / ".psycolab-recovery/repair.log").read_bytes()
    script = root.parent / "external researcher script.py"
    evidence = root.parent / "workspace evidence.json"
    script.write_text("import json,sys\nfrom pathlib import Path\n"
                      "Path(sys.argv[1]).write_text(json.dumps({'python':sys.executable,'args':sys.argv[2:]}))\n")
    commands = f'python "{script}" "{evidence}" "argument with spaces"\npython -m pip --version\nexit\n'
    for _ in range(2):
        result = batch(source, "--workspace", launcher="PsyCoLab.bat", input_text=commands)
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(evidence.read_text())
        assert Path(payload["python"]).resolve() == (root / ".venv-dev/Scripts/python.exe").resolve()
        assert payload["args"] == ["argument with spaces"]
    # The same terminal can enter the workspace and return to the launcher menu.
    result = batch(source, launcher="PsyCoLab.bat", input_text="3\nexit\n4\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("\nPsyCoLab\n1 - Launch PsyCoLab") >= 2
    assert (root / ".psycolab-recovery/repair.log").read_bytes() == log_before
