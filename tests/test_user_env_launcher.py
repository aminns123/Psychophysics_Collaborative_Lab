"""USER_env launch regression: the old bat could stop at missing py -3.11.

These tests do not install Python, mutate the global PATH, or launch GUIs.
"""
from pathlib import Path
import pytest
from scripts import launcher_setup as setup

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_python_launcher_delegates_to_same_application_environment():
    batch = (ROOT / "run_user_env.bat").read_text()
    assert 'PsyCoLab_Python.bat" %*' in batch
    assert "launcher_setup.py" not in batch and "USER_env\\Scripts" not in batch
    supported = (ROOT / "PsyCoLab_Python.bat").read_text()
    assert '--python "%~dp0." %*' in supported


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


def test_shared_setup_has_one_interpreter_discovery_path():
    shared = (ROOT / "scripts/windows_development.cmd").read_text()
    assert 'PSYCOLAB_BOOTSTRAP_PYTHON' in shared and 'py -3.11' in shared
    assert 'scripts\\developer_setup.py' in shared
    assert 'windows_development.cmd' in (ROOT / "setup_psycolab_dev.bat").read_text()
    assert 'windows_development.cmd' in (ROOT / "scripts/windows_startup.cmd").read_text()


def test_extra_requirements_file_only_belongs_to_user_env(tmp_path, monkeypatch):
    from scripts import launcher_setup as setup
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(setup, "VENV", tmp_path / ".venv")
    assert setup._extra_requirements() is None
    setup.select_environment("USER_env")
    extra = setup._extra_requirements()
    assert extra == tmp_path / "user_requirements.txt"
    assert extra.is_file()
    first = setup._hash_file(extra)
    extra.write_text("scipy>=1.11\n", encoding="utf-8")
    assert setup._hash_file(extra) != first
