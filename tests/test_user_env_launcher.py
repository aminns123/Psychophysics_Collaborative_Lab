"""USER_env launch regression: the old bat could stop at missing py -3.11.

These tests do not install Python, mutate the global PATH, or launch GUIs.
"""
from pathlib import Path
import pytest
from scripts import launcher_setup as setup

ROOT = Path(__file__).resolve().parents[1]


def test_user_env_bootstrap_checks_main_venv_before_py_launcher():
    batch = (ROOT / "run_user_env.bat").read_text(encoding="utf-8")
    # "where py" succeeding must not prevent an existing working 3.11
    # interpreter in .venv or on PATH from launching USER_env.
    assert batch.index('if exist ".venv\\Scripts\\python.exe"') < batch.index('py -3.11 -c')
    assert 'if not errorlevel 1 set "USERENV_BOOTSTRAP=py -3.11"' in batch
    assert "where python >nul" in batch
    assert '"scripts\\launcher_setup.py" --user-env' in batch
    assert '"USER_env\\Scripts\\python.exe" -m psychophysics_lab --user-env' in batch


def test_setup_selects_isolated_environment_and_rejects_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(setup, "VENV", tmp_path / ".venv")
    monkeypatch.setattr(setup, "STATE", tmp_path / ".venv" / ".psycolab-setup.json")
    setup.select_environment("USER_env")
    assert setup.VENV == tmp_path / "USER_env"
    assert setup.STATE == tmp_path / "USER_env" / ".psycolab-setup.json"
    with pytest.raises(ValueError, match="Unsupported"):
        setup.select_environment("../unsafe")
    assert setup.VENV == tmp_path / "USER_env"


def test_incompatible_user_env_backup_keeps_name_and_contents(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(setup, "VENV", tmp_path / ".venv")
    monkeypatch.setattr(setup, "STATE", tmp_path / ".venv" / ".psycolab-setup.json")
    setup.select_environment("USER_env")
    setup.VENV.mkdir()
    original = setup.VENV / "do-not-delete.txt"
    original.write_text("preserved", encoding="utf-8")
    setup._preserve_incompatible_venv()
    backups = list(tmp_path.glob("USER_env.incompatible-*"))
    assert len(backups) == 1
    assert (backups[0] / "do-not-delete.txt").read_text(encoding="utf-8") == "preserved"
    assert not setup.VENV.exists()
