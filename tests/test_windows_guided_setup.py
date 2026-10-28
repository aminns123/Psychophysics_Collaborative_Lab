"""Exercise the real native engine without downloads or modifying a user install."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSC = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
pytestmark = pytest.mark.skipif(os.name != 'nt' or not CSC.is_file(), reason='Windows .NET Framework compiler required')

HARNESS = r'''
using System;
using System.IO;
class Checks {
 static int Main(string[] a) { try {
  if(a[0]=="path")Console.WriteLine(SetupEngine.At(a[1],a[2]));
  if(a[0]=="quote")Console.WriteLine(SetupEngine.Quote(a[1]));
  if(a[0]=="load")Console.WriteLine(SetupEngine.Load(a[1]).id);
  if(a[0]=="verify")SetupEngine.Verify(a[1],SetupEngine.Read<System.Collections.Generic.Dictionary<string,string>>(a[2]),()=>false);
  if(a[0]=="install")SetupEngine.Install(a[1],a[2],a[3],a[4],Console.WriteLine,()=>a[5]=="cancel");
  if(a[0]=="validate")SetupEngine.Validate(a[1],SetupEngine.Load(a[1]),a[2],()=>false);
  if(a[0]=="launch-cancel")SetupEngine.Launch(a[1],()=>true);
  if(a[0]=="environment") { var p=SetupEngine.Start("not-run.exe",new[]{a[1]},a[2]);
   foreach(string key in new[]{"PYTHONHOME","PYTHONPATH","CONDA_PREFIX","PSYCOLAB_CONFIG_DIR"})if(p.EnvironmentVariables.ContainsKey(key))throw new Exception("Inherited override: "+key);
   Console.WriteLine(p.Arguments); }
  if(a[0]=="roundtrip") { var p=SetupEngine.Start(a[1],new[]{"-I","-c","import sys;print(ascii(sys.argv[1]))",a[2]},a[3]);p.RedirectStandardOutput=true;using(var child=System.Diagnostics.Process.Start(p)){Console.Write(child.StandardOutput.ReadToEnd());child.WaitForExit();if(child.ExitCode!=0)throw new Exception("child failed");} }
  if(a[0]=="fail-process")SetupEngine.Run(SetupEngine.Start(a[1],new[]{"-I","-c","raise SystemExit(9)"},a[2]),a[3],()=>false);
  return 0;
 }catch(Exception e){Console.Error.WriteLine(e.Message);return 1;} }
}
'''


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    folder = tmp_path_factory.mktemp('native setup with spaces é')
    exe = folder / 'PsyCoLabSetup.exe'
    sealed = folder / 'bundle.json'; sealed.write_text(json.dumps(bundle_manifest()))
    subprocess.run([str(CSC), '/nologo', '/codepage:65001', '/target:winexe', '/platform:x64',
                    '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll', '/r:System.Web.Extensions.dll',
                    '/r:Microsoft.CSharp.dll', '/out:' + str(exe), '/resource:'+str(sealed)+',PsyCoLab.Bundle', str(ROOT / 'packaging/windows/GuidedSetup.cs')], check=True)
    source = folder / 'Checks.cs'
    source.write_text(HARNESS, encoding='utf-8')
    harness = folder / 'Checks.exe'
    subprocess.run([str(CSC), '/nologo', '/r:' + str(exe), '/out:' + str(harness), str(source)], check=True)
    def run(*args, **kwargs):
        return subprocess.run([str(harness), *map(str, args)], capture_output=True, text=True, **kwargs)
    return run


@pytest.mark.parametrize('relative', ['../outside', '/absolute', 'C:/outside', 'a/../../outside', 'a\\b', 'a:stream', 'a//b'])
def test_package_paths_cannot_leave_root(native, tmp_path, relative):
    assert native('path', tmp_path, relative).returncode == 1


def test_linked_store_is_refused(native, tmp_path):
    target = tmp_path/'target';target.mkdir()
    link = tmp_path/'linked'
    try: link.symlink_to(target, target_is_directory=True)
    except OSError: pytest.skip('This Windows account cannot create test symlinks')
    assert native('path',link,'file').returncode == 1
    assert not list(target.iterdir())


@pytest.mark.parametrize('value', ['space & é', 'trailing\\', 'quote"here', ''])
def test_windows_argument_quoting_and_inherited_overrides(native, tmp_path, value):
    env = os.environ | dict(PYTHONHOME='bad', PYTHONPATH='bad', CONDA_PREFIX='bad', PSYCOLAB_CONFIG_DIR='protected')
    result = native('environment', value, tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith('"')
    import ast
    import sys
    result = native('roundtrip', sys.executable, value, tmp_path)
    assert result.returncode == 0 and ast.literal_eval(result.stdout.strip()) == value


def bundle_manifest():
    digest = hashlib.sha256(b'reviewed').hexdigest()
    return dict(schema_version=1, files={'source.txt':digest}, source_files={'source.txt':digest},
                interpreter_files=['source.txt'],wheel_probe='test.whl')


def package(tmp_path):
    bundle, store = tmp_path / 'bundle', tmp_path / 'versions'
    bundle.mkdir()
    (bundle / 'source.txt').write_text('reviewed')
    (bundle / 'bundle.json').write_text(json.dumps(bundle_manifest()))
    return bundle, store


@pytest.mark.parametrize('failure', ['corrupt', 'cancel', 'occupied', 'overlap', 'inconsistent', 'changed-manifest'])
def test_failed_or_cancelled_install_preserves_existing_bytes(native, tmp_path, failure):
    bundle, store = package(tmp_path)
    old = tmp_path / 'old-working-installation'
    old.mkdir(); (old / 'identity').write_bytes(b'old identity and source')
    config, data = '', ''
    if failure == 'corrupt': (bundle / 'source.txt').write_text('changed')
    if failure == 'changed-manifest': (bundle / 'bundle.json').write_text(json.dumps(bundle_manifest() | {'label':'unapproved change'}))
    if failure == 'occupied': store.mkdir(); (store / 'participant.tsv').write_bytes(b'preserve')
    if failure == 'overlap': config = str(store / 'calibration')
    result = native('install', bundle, store, config, data, 'cancel' if failure == 'cancel' else 'go')
    assert result.returncode == 1
    assert (old / 'identity').read_bytes() == b'old identity and source'
    if failure == 'occupied': assert (store / 'participant.tsv').read_bytes() == b'preserve'
    else: assert not store.exists()


def test_unexpected_source_is_rejected_before_executing_python(native, tmp_path):
    instance = tmp_path / ('a' * 32); source = instance / 'source'; source.mkdir(parents=True)
    (source / 'known.py').write_bytes(b'reviewed')
    (instance / 'installation.json').write_text(json.dumps(dict(schema_version=1,id=instance.name,
        source_files={'known.py': hashlib.sha256(b'reviewed').hexdigest()})))
    (source / 'unexpected.py').write_bytes(b'new science')
    result = native('validate', instance, tmp_path / 'check.log')
    assert result.returncode == 1 and 'added or changed source' in result.stderr
    assert not (tmp_path / 'check.log').exists()
    result = native('launch-cancel', instance)
    assert result.returncode == 1 and 'canceled' in result.stderr.lower()


def test_process_failure_retains_diagnostic_log(native, tmp_path):
    import sys
    log = tmp_path / 'failure.log'
    result = native('fail-process', sys.executable, tmp_path, log)
    assert result.returncode == 1 and 'previous installations are unchanged' in result.stderr
    assert log.is_file()
