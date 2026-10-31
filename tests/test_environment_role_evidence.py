import json
from pathlib import Path
import subprocess
import sys

import pytest
from psychophysics_lab.core.environment import environment_evidence, environment_notice
from psychophysics_lab.core.runner import _software_provenance


@pytest.mark.parametrize('hint', ['', 'arbitrary', 'locked', 'development'])
def test_direct_or_unrelated_interpreter_is_unknown(tmp_path, monkeypatch, hint):
    monkeypatch.setenv('PSYCOLAB_LAUNCH_ROLE', hint)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: pytest.fail('Unrelated interpreter must not be checked'))
    d=environment_evidence(tmp_path)
    assert d['role']=='unknown' and not d['locked_profile_check_passed']
    assert 'unknown' in environment_notice(d)


@pytest.mark.parametrize('role,code', [('development',0),('locked',0),('development',1),('locked',1)])
def test_selected_route_is_independently_checked_and_portable(tmp_path,monkeypatch,role,code):
    folder='.venv-dev' if role=='development' else '.venv'
    env=tmp_path/folder
    python=env/'Scripts/python.exe'
    python.parent.mkdir(parents=True);python.write_bytes(b'interpreter')
    record=env/('.psycolab-development.json' if role=='development' else '.psycolab-setup.json')
    record.write_text('{}')
    script=tmp_path/'scripts'/('developer_setup.py' if role=='development' else 'launcher_setup.py')
    script.parent.mkdir();script.write_text('# check fixture')
    (tmp_path/'pyproject.toml').write_text('[project]')
    monkeypatch.setenv('PSYCOLAB_LAUNCH_ROLE',role)
    monkeypatch.setattr(sys,'executable',str(python));monkeypatch.setattr(sys,'prefix',str(env))
    calls=[]
    def check(args,**kw):
        calls.append(args)
        return subprocess.CompletedProcess(args,code,b'check output',b'')
    monkeypatch.setattr(subprocess,'run',check)
    d=environment_evidence(tmp_path)
    assert calls==[[str(python),'-I','-B',str(script),'--check']]
    assert d['check']==('passed' if code==0 else 'failed')
    assert d['locked_profile_check_passed']==(role=='locked' and code==0)
    assert str(tmp_path) not in json.dumps(d)
    if role=='development':assert 'No locked laboratory qualification' in environment_notice(d)


def test_saved_provenance_records_unknown_without_inventing_qualification(tmp_path,monkeypatch):
    monkeypatch.delenv('PSYCOLAB_LAUNCH_ROLE',raising=False)
    d=_software_provenance(Path(__file__).resolve().parents[1])
    assert d['environment']['role']=='unknown'
    assert d['environment']['locked_profile_check_passed'] is False
