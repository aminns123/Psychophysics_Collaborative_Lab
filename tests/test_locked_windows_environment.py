"""Lock boundaries are enforced before any mutation; source identity tests stay real."""
import base64
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import venv

import pytest
from scripts import launcher_setup as setup
from test_launcher_environment_reliability import configured_launcher


def qualified(tmp_path, monkeypatch):
    root, project, python, calls = configured_launcher(tmp_path, monkeypatch, existing=True)
    setup._write_state(setup._hash_file(project), qualification=setup._fixture_qualification)
    return root, project, python, calls


@pytest.mark.parametrize('change', ['lock-id', 'project', 'artifact', 'inventory', 'files', 'interpreter'])
def test_existing_mismatch_preserves_state_and_never_installs(tmp_path, monkeypatch, change):
    root, project, python, calls = qualified(tmp_path, monkeypatch)
    if change == 'project':
        project.write_text(project.read_text() + '\n# changed dependency specification\n')
    else:
        state = json.loads(setup.STATE.read_text())
        q = state['qualification']
        if change == 'lock-id': q['profile_sha256'] = 'changed'
        if change == 'artifact': next(iter(q['artifacts'].values()))['sha256'] = '0' * 64
        if change == 'inventory': q['inventory'] = {'numpy': 'wrong'}
        if change == 'files': q['core_fingerprint'] = 'changed'
        if change == 'interpreter': q['interpreter'] = {'changed': True}
        setup.STATE.write_text(json.dumps(state))
    before = setup.STATE.read_bytes()
    assert setup.main() == 1
    assert setup.STATE.read_bytes() == before and setup.VENV.exists()
    assert not any('install' in command or 'venv' in command for command in calls)


def test_existing_unqualified_environment_is_not_adopted_or_moved(tmp_path, monkeypatch):
    root, project, python, calls = configured_launcher(tmp_path, monkeypatch, existing=True)
    marker = setup.VENV / 'old-working-file'
    marker.write_bytes(b'preserve')
    assert setup.main() == 1 and marker.read_bytes() == b'preserve'
    assert not setup.STATE.exists() and not calls


def test_interrupted_owned_setup_can_retry_only_the_same_profile(tmp_path, monkeypatch):
    root, project, python, calls = configured_launcher(tmp_path, monkeypatch, existing=False)
    install = setup._install_locked
    def unavailable(python):
        raise subprocess.CalledProcessError(1, ['pip', 'approved-artifact-unavailable'])
    monkeypatch.setattr(setup, '_install_locked', unavailable)
    assert setup.main() == 1 and not setup.STATE.exists()
    assert (setup.VENV / '.psycolab-setup.pending.json').is_file()
    monkeypatch.setattr(setup, '_install_locked', install)
    assert setup.main() == 0 and setup.STATE.is_file()
    calls.clear()
    assert setup.main() == 0 and not any('install' in c for c in calls)


def test_profile_rejects_a_changed_lock_before_setup(tmp_path, monkeypatch):
    import shutil
    target = tmp_path / 'profile'
    shutil.copytree(setup.PROFILE_DIR, target)
    monkeypatch.setattr(setup, 'PROFILE_DIR', target)
    (target / 'runtime.lock').write_bytes((target / 'runtime.lock').read_bytes() + b'\n')
    with pytest.raises(ValueError, match='dependency file changed'):
        setup._profile()


@pytest.mark.parametrize('field,value', [('version',[3,11,9]),('bits',32),('implementation','pypy'),
    ('exe_sha256','wrong'),('dll_sha256','wrong'),('native_fingerprint','wrong'),('distribution','other-provider')])
def test_interpreter_identity_does_not_accept_an_arbitrary_311(field, value):
    profile, _ = setup._profile()
    identity = dict(profile['python'], platform='win32', distribution='conda-forge', native=[
        {'name': r['name'], 'sha256': r['sha256']} for r in json.loads((setup.PROFILE_DIR/'interpreter-artifacts.json').read_text())])
    identity[field] = value
    with pytest.raises(ValueError): setup._validate_interpreter(identity)


@pytest.mark.parametrize('fault', ['file', 'missing', 'version'])
def test_real_installed_dependency_files_are_checked(tmp_path, monkeypatch, fault):
    target = tmp_path/'venv'
    venv.EnvBuilder(with_pip=False).create(target)
    python = setup._venv_python(target)
    site = Path(subprocess.check_output([str(python),'-I','-c',"import sysconfig;print(sysconfig.get_path('purelib'))"],text=True).strip())
    data = site/'exampledep.py'; data.write_bytes(b'value = 1\n')
    dist = site/'exampledep-1.dist-info'; dist.mkdir()
    (dist/'METADATA').write_text('Metadata-Version: 2.1\nName: exampledep\nVersion: 1\n')
    paths = [data, dist/'METADATA']
    with (dist/'RECORD').open('w',newline='') as stream:
        writer=csv.writer(stream)
        for path in paths:
            raw=path.read_bytes();h=base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
            writer.writerow([path.relative_to(site).as_posix(),'sha256='+h,len(raw)])
        writer.writerow(['exampledep-1.dist-info/RECORD','',''])
    profile, digest = setup._profile(); profile=profile|{'core':{'exampledep':'1'},'development':{}}
    identity=dict(implementation='cpython',version=[3,11,15],bits=64,platform='win32',distribution='fixture',
                  exe_sha256='fixture',dll_sha256='fixture',native_fingerprint='fixture')
    monkeypatch.setattr(setup,'_profile',lambda:(profile,digest))
    monkeypatch.setattr(setup,'_inspect_interpreter',lambda p:identity)
    monkeypatch.setattr(setup,'_validate_interpreter',lambda info:None)
    assert setup._environment_evidence(python)['inventory']=={'exampledep':'1'}
    if fault=='file': data.write_bytes(b'value = 2\n')
    if fault=='missing': data.unlink()
    if fault=='version': (dist/'METADATA').write_text('Metadata-Version: 2.1\nName: exampledep\nVersion: 2\n')
    with pytest.raises(ValueError): setup._environment_evidence(python)


def test_optional_requirements_resolve_against_core_before_install(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'VENV', tmp_path)
    path=tmp_path/'user_requirements.txt';path.write_text('iniconfig==2.3.1\n')
    calls=[]
    def record(command, **kwargs):
        calls.append(command)
        if '--dry-run' in command: raise subprocess.CalledProcessError(1,command)
    monkeypatch.setattr(setup,'_run',record)
    with pytest.raises(subprocess.CalledProcessError): setup._install_extra_requirements(Path(sys.executable),path)
    assert len(calls)==1 and '--constraint' in calls[0] and '--dry-run' in calls[0]
    assert path.read_text()=='iniconfig==2.3.1\n'


def test_optional_same_version_core_replacement_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, 'VENV', tmp_path)
    path = tmp_path / 'user_requirements.txt'
    path.write_text('numpy @ file:///different-build.whl\n')
    calls = []
    def plan(command, **kwargs):
        calls.append(command)
        Path(command[command.index('--report') + 1]).write_text(json.dumps(
            {'install': [{'metadata': {'name': 'numpy', 'version': '1.26.4'}}]}))
    monkeypatch.setattr(setup, '_run', plan)
    with pytest.raises(ValueError, match='would replace approved numpy'):
        setup._install_extra_requirements(Path(sys.executable), path)
    assert len(calls) == 1 and '--dry-run' in calls[0]
