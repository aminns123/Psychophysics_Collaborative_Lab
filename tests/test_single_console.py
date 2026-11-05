"""Native Windows console inheritance and external researcher scripts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from test_startup_recovery import source

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows console ownership")


@pytest.mark.parametrize("entry", [("PsyCoLab.bat", "--python")])
def test_actual_batch_reuses_parent_console_and_same_python_for_external_scripts(tmp_path, entry):
    root = source(tmp_path, real_python=True)
    (root / "packaging/windows").mkdir(parents=True)
    for name in ("PsyCoLab.bat", "scripts/windows_startup.cmd", "packaging/windows/GuidedSetup.cs"):
        shutil.copy2(ROOT / name, root / name)
    script = tmp_path / "independent researcher script.py"
    result_file = tmp_path / "script evidence.json"
    script.write_text(
        'import ctypes,json,os,sys\nfrom pathlib import Path\n'
        'ids=(ctypes.c_uint32*64)()\ncount=ctypes.windll.kernel32.GetConsoleProcessList(ids,64)\n'
        'Path(sys.argv[1]).write_text(json.dumps(dict(python=sys.executable,role=os.environ.get("PSYCOLAB_LAUNCH_ROLE"),args=sys.argv[2:],'
        'console=list(ids[:count]),own=os.getpid(),parent=int(os.environ["PROBE_PARENT"]))))\n'
        'raise SystemExit(int(sys.argv[3]))\n', encoding="utf-8")
    parent = tmp_path / "console parent.py"
    parent.write_text(
        'import os,subprocess,sys\nos.environ["PROBE_PARENT"]=str(os.getpid())\n'
        f'raise SystemExit(subprocess.call(["cmd.exe","/d","/c","call",*{entry!r},*sys.argv[1:]]))\n')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    for code in (0, 7, 0):
        result = subprocess.run([sys.executable, str(parent), str(script), str(result_file), "space & é", str(code)],
            cwd=root, creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startup, timeout=30)
        assert result.returncode == code
        evidence = json.loads(result_file.read_text())
        assert Path(evidence["python"]).resolve() == (root / ".venv/Scripts/python.exe").resolve()
        assert evidence["args"] == ["space & é", str(code)]
        assert evidence["role"] == "locked"
        assert evidence["own"] in evidence["console"]
        assert evidence["parent"] in evidence["console"], "Python allocated a redundant console"


def test_missing_source_environment_runs_shared_setup_once_and_preserves_failure(tmp_path):
    # Execute the actual shared batch flow; stand-ins avoid network and package
    # installs. Developer setup itself has independent real ownership tests.
    root = tmp_path / "fresh checkout with spaces"
    (root / "scripts").mkdir(parents=True)
    (root / ".git").mkdir()
    shutil.copy2(ROOT / "scripts/windows_startup.cmd", root / "scripts/windows_startup.cmd")
    shutil.copy2(ROOT / "scripts/windows_development.cmd", root / "scripts/windows_development.cmd")
    shutil.copy2(ROOT / "PsyCoLab.bat", root / "PsyCoLab.bat")
    (root / "packaging/windows").mkdir(parents=True)
    shutil.copy2(ROOT / "packaging/windows/GuidedSetup.cs", root / "packaging/windows/GuidedSetup.cs")
    (root / "pyproject.toml").write_text("# disposable source setup\n")
    (root / "scripts/launcher_setup.py").write_text("# fixture presence\n")
    profile = root / "requirements/windows-cp311"
    profile.mkdir(parents=True)
    for name in ("build", "runtime", "development"):
        (profile / (name + ".lock")).write_text("# fixture; setup deliberately fails\n")
    (root / "scripts/developer_setup.py").write_text(
        'from pathlib import Path\np=Path("setup attempts");p.write_text("one")\n'
        'raise SystemExit(9)\n')
    from _windows_launcher_process import run_launcher
    from unittest.mock import patch
    with patch.dict(os.environ, {"PSYCOLAB_BOOTSTRAP_PYTHON": sys._base_executable}):
        result = run_launcher(["cmd.exe", "/d", "/c", "call", "PsyCoLab.bat", "--repair"], cwd=root, timeout=45)
    assert result.returncode == 1 and "exit code 9" in result.stdout, result.stdout + result.stderr
    assert (root / "setup attempts").read_text() == "one"
    assert not (root / ".venv").exists()
