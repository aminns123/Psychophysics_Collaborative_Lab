"""Maintainer setup is explicit, separate, and never grants qualification."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import developer_setup as setup


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    root = tmp_path / "maintainer with spaces & unicode é"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="fixture"\n')
    env = root / ".venv-dev"
    for key, value in dict(ROOT=root, VENV=env, STATE=env / ".psycolab-development.json",
                           PENDING=env / ".psycolab-development.pending.json").items():
        monkeypatch.setattr(setup, key, value)
    calls = []
    monkeypatch.setattr(setup.launcher, "_run", lambda args: calls.append(args))
    monkeypatch.setattr(setup.launcher, "_validate_environment", lambda python: calls.append([str(python), "validate"]))

    def create(folder):
        python = setup.launcher._venv_python(folder)
        python.parent.mkdir(parents=True)
        python.write_bytes(b"fixture interpreter")

    monkeypatch.setattr(setup.venv.EnvBuilder, "create", lambda self, folder: create(folder))
    return root, calls


def test_explicit_setup_then_repeated_read_only_checks(checkout, monkeypatch):
    root, calls = checkout
    assert setup.main() == 0
    assert not (root / ".venv").exists()
    assert not list(root.rglob(".psycolab-setup.json"))
    state = json.loads(setup.STATE.read_text())
    assert state["mode"] == "development" and "qualification" not in state
    assert any(args[-2:] == ["--editable", str(root) + "[dev]"] for args in calls)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.setattr(sys, "prefix", str(setup.VENV))
    calls.clear()
    for _ in range(2):
        assert setup.check_only() == 0
    assert not any("install" in args for args in calls)
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("change", ["path", "requirements", "mode", "missing", "malformed", "interpreter"])
def test_invalid_dev_environment_is_never_repaired(checkout, monkeypatch, change):
    root, calls = checkout
    assert setup.main() == 0
    monkeypatch.setattr(sys, "prefix", str(setup.VENV))
    if change == "requirements":
        (root / "pyproject.toml").write_text("changed dependency specification")
    elif change == "missing":
        setup.STATE.unlink()
    elif change == "malformed":
        setup.STATE.write_text("{")
    elif change == "interpreter":
        monkeypatch.setattr(sys, "prefix", str(root / "unrelated"))
    else:
        state = json.loads(setup.STATE.read_text())
        state["source_root" if change == "path" else "mode"] = "unrelated"
        setup.STATE.write_text(json.dumps(state))
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    calls.clear()
    assert setup.check_only() == 1 and not calls
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("occupied", [".venv", ".venv-dev"])
def test_setup_does_not_adopt_existing_environments(checkout, occupied):
    root, calls = checkout
    folder = root / occupied
    folder.mkdir()
    marker = folder / "preserve"
    marker.write_bytes(b"existing installation")
    assert setup.main() == 1 and not calls
    assert list(folder.iterdir()) == [marker]
    assert marker.read_bytes() == b"existing installation"


def test_failed_setup_can_retry_but_cannot_launch(checkout, monkeypatch):
    _, calls = checkout
    def fail(_):
        raise subprocess.CalledProcessError(7, ["fixture install"])
    monkeypatch.setattr(setup.launcher, "_run", fail)
    assert setup.main() == 1 and setup.PENDING.exists() and not setup.STATE.exists()
    monkeypatch.setattr(sys, "prefix", str(setup.VENV))
    assert setup.check_only() == 1
    monkeypatch.setattr(setup.launcher, "_run", lambda args: calls.append(args))
    assert setup.main() == 0


def test_repeat_setup_does_not_overwrite_running_interpreter(checkout, monkeypatch):
    assert setup.main() == 0
    monkeypatch.setattr(setup.venv.EnvBuilder, "create", lambda *args: pytest.fail("existing interpreter recreated"))
    assert setup.main() == 0


@pytest.mark.parametrize("unsupported", ["python", "architecture", "managed"])
def test_unsupported_setup_is_refused_before_creation(checkout, monkeypatch, unsupported):
    root, calls = checkout
    if unsupported == "python":
        monkeypatch.setattr(sys, "version_info", (3, 12, 0))
    elif unsupported == "architecture":
        monkeypatch.setattr(setup.struct, "calcsize", lambda _: 4)
    else:
        (root.parent / "installation.json").write_text('{}')
    assert setup.main() == 1 and not calls and not setup.VENV.exists()
