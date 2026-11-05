"""USER_env launch regression: the old bat could stop at missing py -3.11.

These tests do not install Python, mutate the global PATH, or launch GUIs.
"""
from pathlib import Path
import pytest
from scripts import launcher_setup as setup

ROOT = Path(__file__).resolve().parents[1]


def test_retired_wrappers_are_pinned_nonexecutable_history_and_not_runtime_references():
    import hashlib
    import json
    archive = ROOT / "outdated_code/windows_launchers"
    inventory = json.loads((archive / "sha256-lf.json").read_text())
    assert len(inventory) == 5
    for name, expected in inventory.items():
        assert not (ROOT / name).exists()
        assert hashlib.sha256((archive / (name + ".txt")).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected
    for folder in (ROOT / "scripts", ROOT / "packaging", ROOT / "src", ROOT / ".github"):
        for path in folder.rglob("*"):
            if path.suffix.lower() in {".py", ".cmd", ".cs", ".yml", ".yaml"}:
                text = path.read_text(encoding="utf-8").lower()
                assert not any(name.lower() in text for name in inventory), path


def test_one_root_launcher_keeps_workspace_and_python_on_the_checked_environment():
    assert sorted(p.name for p in ROOT.iterdir() if p.suffix.lower() == ".bat") == ["PsyCoLab.bat"]
    batch = (ROOT / "PsyCoLab.bat").read_text()
    assert 'windows_startup.cmd" --entry "%~dp0." %*' in batch
    native = (ROOT / "packaging/windows/GuidedSetup.cs").read_text(encoding="utf-8")
    assert 'args[0]=="--workspace"' in native and 'args[0]=="--python"' in native
    assert 'StartupRecovery.LaunchPython(root,args.Skip(1).ToArray())' in native
    assert '3 - Python Workspace' in native


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
