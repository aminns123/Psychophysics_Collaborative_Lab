"""Real native classification and process boundary; no lab environment is adopted.

The tiny source fixture uses a stand-in read-only check to test routing. Existing
locked-environment regressions separately exercise the real qualification gate.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

import pytest
from test_windows_guided_setup import native

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows native startup')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source(tmp_path, *, real_python=False, name='checkout with spaces é'):
    root=tmp_path/name;root.mkdir(parents=True)
    (root/'pyproject.toml').write_text('fixture source')
    (root/'scripts').mkdir();(root/'scripts/launcher_setup.py').write_text('import sys\nassert sys.argv[1:] == ["--check"]\n')
    profile=root/'requirements/windows-cp311';profile.mkdir(parents=True)
    (profile/'runtime.lock').write_text('fixture lock')
    (profile/'profile.json').write_text(json.dumps(dict(files={'runtime.lock':sha(profile/'runtime.lock')})))
    if real_python:
        venv.EnvBuilder(with_pip=False).create(root/'.venv')
    else:
        (root/'.venv/Scripts').mkdir(parents=True);(root/'.venv/Scripts/python.exe').write_bytes(b'not executed by inspection')
    state=dict(schema_version=2,source_root=str(root),pyproject_sha256=sha(root/'pyproject.toml'),
               qualification=dict(profile_sha256=sha(profile/'profile.json')))
    (root/'.venv/.psycolab-setup.json').write_text(json.dumps(state))
    return root


@pytest.mark.parametrize('change,category', [
    ('none','check_required'),('legacy','qualification_legacy'),('missing_record','qualification_missing'),
    ('moved','installation_path_changed'),('profile','profile_changed'),('lock','profile_invalid'),
    ('requirements','requirements_changed'),('environment','environment_missing'),
    ('interrupted','setup_interrupted'),('malformed','evidence_unreadable'),('source','source_missing')])
def test_evidence_categories_preserve_every_fixture_file(native,tmp_path,change,category):
    root=source(tmp_path);state=root/'.venv/.psycolab-setup.json'
    if change=='legacy': state.write_text('{"schema_version":1}')
    if change=='missing_record': state.unlink()
    if change=='moved':
        d=json.loads(state.read_text());d['source_root']=str(tmp_path/'original');state.write_text(json.dumps(d))
    if change=='profile':
        p=root/'requirements/windows-cp311/profile.json';p.write_text(p.read_text()+'\n')
    if change=='lock': (root/'requirements/windows-cp311/runtime.lock').write_text('changed')
    if change=='requirements': (root/'pyproject.toml').write_text('incompatible requirements')
    if change=='environment': (root/'.venv/Scripts/python.exe').unlink()
    if change=='interrupted': state.unlink();(root/'.venv/.psycolab-setup.pending.json').write_text('{}')
    if change=='malformed': state.write_text('{')
    if change=='source': (root/'pyproject.toml').unlink()
    before={str(p):sha(p) for p in root.rglob('*') if p.is_file()}
    result=native('inspect',root)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['category']==category
    assert {str(p):sha(p) for p in root.rglob('*') if p.is_file()}==before


def test_repeated_read_only_check_allows_environment_compatible_source_changes(native,tmp_path):
    root=source(tmp_path,real_python=True)
    before={str(p):sha(p) for p in root.rglob('*') if p.is_file()}
    for _ in range(2): assert json.loads(native('diagnose',root).stdout)['healthy']
    assert {str(p):sha(p) for p in root.rglob('*') if p.is_file()}==before
    (root/'scientific_source.py').write_text('# deliberate branch/source edit; not scientific approval\n')
    assert json.loads(native('diagnose',root).stdout)['healthy']
    (root/'pyproject.toml').write_text('new requirements')
    assert json.loads(native('diagnose',root).stdout)['category']=='requirements_changed'


def test_failed_existing_check_is_never_repaired(native,tmp_path):
    root=source(tmp_path,real_python=True)
    hook=root/'scripts/launcher_setup.py';hook.write_text('raise SystemExit(7)')
    state=root/'.venv/.psycolab-setup.json';before=state.read_bytes()
    result=json.loads(native('diagnose',root).stdout)
    assert result['category']=='qualification_check_failed' and not result['healthy']
    assert state.read_bytes()==before and hook.read_text()=='raise SystemExit(7)'


def test_damaged_interpreter_is_not_replaced(native,tmp_path):
    root=source(tmp_path)
    python=root/'.venv/Scripts/python.exe';before=python.read_bytes()
    d=json.loads(native('diagnose',root).stdout)
    assert not d['healthy'] and d['category']=='environment_or_source_damaged'
    assert python.read_bytes()==before


@pytest.mark.parametrize('phase',['application_startup','post_tui_experiment_launch','unknown'])
def test_real_child_exit_is_observed_once_and_never_replayed(native,tmp_path,phase):
    root=source(tmp_path,real_python=True)
    site=subprocess.check_output([str(root/'.venv/Scripts/python.exe'),'-I','-c',
        "import sysconfig;print(sysconfig.get_path('purelib'))"],text=True).strip()
    # Python 3.11 reads plain .pth paths using the Windows locale. An ASCII
    # import expression preserves this Unicode fixture path independently.
    (Path(site)/'fixture.pth').write_text('import sys;sys.path.insert(0,'+ascii(str(root))+')\n',encoding='ascii')
    package=root/'psychophysics_lab';package.mkdir();(package/'__init__.py').write_text('')
    (package/'__main__.py').write_text(
        'import json,os,sys\nfrom pathlib import Path\n'
        'p=Path("attempts");p.write_text(p.read_text()+"run\\n" if p.exists() else "run\\n")\n'
        'if sys.argv[1]!="unknown":\n'
        ' with open("\\\\\\\\.\\\\pipe\\\\"+os.environ["PSYCOLAB_STARTUP_PIPE"],"wb",buffering=0) as pipe:\n'
        '  pipe.write((json.dumps({"phase":sys.argv[1]})+"\\n").encode())\n'
        'raise SystemExit(7)\n')
    result=native('observed-exit',root,phase,timeout=30)
    assert result.returncode==0,result.stderr
    assert 'application_exit=7' in result.stdout
    assert 'View diagnostics and administrator instructions [Recommended]' in result.stdout
    assert 'Open verified retained installation' not in result.stdout
    assert 'Create separate approved installation' not in result.stdout
    assert ('application startup crash' in result.stdout)==(phase=='application_startup')
    assert (root/'attempts').read_text()=='run\n'


def test_retained_choices_are_rechecked_and_invalid_choices_disappear(native,tmp_path):
    old=source(tmp_path/'old',real_python=True)
    current=source(tmp_path/'current')
    state=current/'.venv/.psycolab-setup.json'
    d=json.loads(state.read_text());d['source_root']=str(old);state.write_text(json.dumps(d))
    candidates=json.loads(native('retained',current,tmp_path/'empty-store').stdout)
    assert len(candidates)==1 and candidates[0]['root']==str(old)
    (old/'scripts/launcher_setup.py').write_text('raise SystemExit(1)')
    assert json.loads(native('retained',current,tmp_path/'empty-store').stdout)==[]


def test_managed_retained_source_seal_rejects_added_files(native):
    # Actual default managed stores are short; do not exceed .NET Framework's
    # legacy path limit by nesting the pytest workspace plus a managed prefix.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='psy-sr-') as folder:
        root=Path(folder)
        assert root.parent.resolve()==Path(tempfile.gettempdir()).resolve()
        managed_seal_case(native,root)


def managed_seal_case(native,tmp_path):
    identity='a'*32
    old=source(tmp_path,real_python=True,name='store/versions/'+identity+'/source')
    manifest={p.relative_to(old).as_posix():sha(p) for p in old.rglob('*') if p.is_file() and '.venv' not in p.parts}
    (old.parent/'installation.json').write_text(json.dumps(dict(schema_version=1,id=identity,label='fixture',source_files=manifest)))
    broken=source(tmp_path/'broken');(broken/'.venv/.psycolab-setup.json').unlink()
    assert len(json.loads(native('retained',broken,tmp_path/'store').stdout))==1
    (old/'unreviewed_science.py').write_text('# must not bypass the packaged source seal')
    assert json.loads(native('retained',broken,tmp_path/'store').stdout)==[]


def test_exit_phase_crosses_real_private_os_pipe(native,tmp_path):
    import uuid
    name='PsyCoLabStartup-'+uuid.uuid4().hex
    # The harness executes its real native named-pipe listener.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor() as pool:
        listening=pool.submit(native,'pipe',name,timeout=15)
        code='import sys;sys.path.insert(0,sys.argv[1]);from psychophysics_lab.diagnostics import notify_launcher_exit;notify_launcher_exit("post_tui_experiment_launch")'
        # Windows CreateFile can precede the listener; retry only this test IPC,
        # never an application or experimental operation.
        import time
        for _ in range(30):
            subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT/'src')],
                env=os.environ|{'PSYCOLAB_STARTUP_PIPE':name},check=True)
            if listening.done(): break
            time.sleep(.05)
        notice=json.loads(listening.result(timeout=15).stdout)
    assert notice=={'phase':'post_tui_experiment_launch','report':None}


@pytest.mark.parametrize('healthy,after,count,package,expected',[
    (True,False,0,False,'cancel'),(False,False,1,False,'retained'),
    (False,False,0,True,'separate'),(False,False,0,False,'diagnostics'),
    (False,True,2,True,'diagnostics')])
def test_recommendation_uses_only_verified_available_options(native,healthy,after,count,package,expected):
    d=json.dumps(dict(healthy=healthy,after_application=after))
    assert native('recommend',d,count,str(package).lower()).stdout.strip()==expected


@pytest.mark.parametrize('phase,category',[('application_startup','application_startup_crash'),
    ('post_tui_experiment_launch','experiment_or_operation_failure'),
    ('synthetic_simulation','experiment_or_operation_failure'),('unknown','unknown_application_exit')])
def test_incidents_never_offer_relaunch_or_install(native,tmp_path,phase,category):
    d=json.loads(native('incident',tmp_path,phase).stdout)
    assert d['category']==category and d['after_application']
    form=native('recovery-form',json.dumps(d),tmp_path).stdout
    assert form.count('[Recommended]')==1 and 'View diagnostics' in form
    assert 'Open verified retained' not in form and 'Create separate' not in form
    assert 'No automatic correction' in form


def test_unavailable_artifacts_and_unqualified_retained_instances_offer_diagnostics(native,tmp_path):
    root=source(tmp_path);(root/'.venv/.psycolab-setup.json').unlink()
    store=tmp_path/'store';(store/'versions'/('a'*32)).mkdir(parents=True)
    (store/'versions'/('a'*32)/'installation.json').write_text('{}')
    assert json.loads(native('retained',root,store).stdout)==[]
    d=json.loads(native('inspect',root).stdout)
    form=native('recovery-form',json.dumps(d),tmp_path).stdout
    assert form.count('[Recommended]')==1 and 'View diagnostics' in form
    assert 'Create separate approved' not in form


def test_named_pipe_notification_cannot_be_redirected_to_a_lab_file(monkeypatch,tmp_path):
    from psychophysics_lab.diagnostics import notify_launcher_exit
    marker=tmp_path/'calibration.json';marker.write_bytes(b'preserve')
    monkeypatch.setenv('PSYCOLAB_STARTUP_PIPE',str(marker))
    notify_launcher_exit('application_startup')
    assert marker.read_bytes()==b'preserve'


@pytest.mark.parametrize('phase',['application_startup','post_tui_experiment_launch'])
def test_app_error_reports_phase_without_retry(monkeypatch,phase):
    from psychophysics_lab import app,diagnostics
    called=[]
    def fail(argv,diagnostic_context):
        diagnostic_context['phase']=phase
        raise RuntimeError('controlled startup/operation failure')
    monkeypatch.setattr(app,'_main',fail)
    monkeypatch.setattr(app,'start_fatal_fault_capture',lambda:None)
    monkeypatch.setattr(app,'write_crash_report',lambda *a,**k:None)
    monkeypatch.setattr(diagnostics,'notify_launcher_exit',lambda p,r:called.append((p,r)))
    assert app.main([])==1 and called==[(phase,None)]
