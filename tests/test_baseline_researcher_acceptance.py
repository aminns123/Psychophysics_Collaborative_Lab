"""New author acceptance through public source, TUI controls and real recording."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/release_acceptance_lab"


def test_new_diamond_study_test_review_repeat_inspect_and_contribute(tmp_path):
    root = tmp_path / "project"
    shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "configs", root / "configs")
    shutil.copy2(ROOT / "pyproject.toml", root / "pyproject.toml")
    lab = tmp_path / "laboratory"
    shutil.copytree(FIXTURE, lab, ignore=shutil.ignore_patterns("exercise.py", "__pycache__"))
    env = os.environ | {"PYTHONPATH": os.pathsep.join([str(root / "src"), str(ROOT)]),
        "PSYCOLAB_REPO_ROOT": str(root), "PSYCOLAB_CONFIG_DIR": str(tmp_path / "private_config"),
        "PSYCOLAB_DATA_DIR": str(tmp_path / "data"), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-B", str(FIXTURE / "exercise.py"), str(root), str(lab), str(tmp_path / "data")],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    (tmp_path / "researcher_acceptance.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    assert result.returncode == 0, result.stdout[-3500:] + "\n" + result.stderr[-6500:]
    assert json.loads(result.stdout.strip().splitlines()[-1])["status"] == "PASS"
