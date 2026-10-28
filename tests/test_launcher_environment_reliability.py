"""Launcher command construction/failure tests; no installs or global env edits."""
from pathlib import Path
import subprocess
import sys
import pytest
from scripts import launcher_setup as launcher
from _locked_launcher_fixture import locked_fixture

def configured_launcher(tmp_path,monkeypatch,*,existing):
    qualification = locked_fixture(monkeypatch, launcher)
    root=tmp_path/'checkout with spaces & unicode é'
    root.mkdir()
    project=root/'pyproject.toml'
    project.write_text('[project]\nname="fixture"\nversion="0.0.0"\n')
    venv=root/'.venv'
    if existing: venv.mkdir()
    for key,value in {'ROOT':root,'VENV':venv,'PYPROJECT':project,'STATE':venv/'.psycolab-setup.json'}.items():
        monkeypatch.setattr(launcher,key,value)
    python=launcher._venv_python(venv)
    monkeypatch.setattr(launcher,'_python_version',lambda p:(3,11) if venv.exists() else None)
    calls=[]
    def command(args,**kwargs):
        calls.append(args)
        if args[1:3]==['-m','venv']: venv.mkdir(exist_ok=True)
        return subprocess.CompletedProcess(args,0)
    monkeypatch.setattr(launcher,'_run',command)
    monkeypatch.setattr(launcher, '_fixture_qualification', qualification, raising=False)
    return root,project,python,calls

def test_fresh_environment_commands_keep_paths_as_arguments(tmp_path,monkeypatch):
    root,project,python,calls=configured_launcher(tmp_path,monkeypatch,existing=False)
    assert launcher.main()==0
    assert calls[0]==[sys.executable,'-m','venv',str(root/'.venv')]
    assert any(args[-2:]==['--editable',str(root)] for args in calls)
    assert [str(python),'-m','pip','check'] in calls
    assert launcher.STATE.exists()

def test_existing_environment_reuse_does_not_install(tmp_path,monkeypatch):
    root,project,python,calls=configured_launcher(tmp_path,monkeypatch,existing=True)
    launcher._write_state(launcher._hash_file(project), qualification=launcher._fixture_qualification)
    assert launcher.main()==0
    assert not any('install' in args or 'venv' in args for args in calls)
    assert [str(python),'-m','pip','check'] in calls

def test_fresh_environment_validation_failure_is_actionable(tmp_path,monkeypatch,capsys):
    root,project,python,calls=configured_launcher(tmp_path,monkeypatch,existing=False)
    def broken(p): raise subprocess.CalledProcessError(1,[str(p),'-m','pip','check'])
    monkeypatch.setattr(launcher,'_validate_environment',broken)
    assert launcher.main()==1
    assert not launcher.STATE.exists()
    assert 'validation failed' in capsys.readouterr().out
