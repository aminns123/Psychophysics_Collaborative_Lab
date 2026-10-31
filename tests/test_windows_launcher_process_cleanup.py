"""Fault-injected test-console descendants cannot hold pytest open on Windows."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys
import time
import pytest
from _windows_launcher_process import run_launcher

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='Windows job/console ownership')


def assert_stopped(pid):
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE; read-only wait
    if handle:
        try:
            assert api.WaitForSingleObject(handle, 2000) == 0
        finally:
            api.CloseHandle(handle)


@pytest.mark.parametrize('parent_waits', [False, True])
def test_inherited_output_and_live_descendants_are_bounded_and_cleaned(tmp_path, parent_waits):
    source = tmp_path/'launcher with spaces.py'
    source.write_text(
        'import subprocess,sys,time\nfrom pathlib import Path\n'
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],stdout=sys.stdout,stderr=sys.stderr,close_fds=False)\n"
        "Path('descendant.pid').write_text(str(child.pid))\n"
        "print('partial launcher evidence',flush=True)\n"
        + ('time.sleep(60)\n' if parent_waits else ''), encoding='utf-8')
    command=[sys.executable,'-u',str(source)]
    start=time.monotonic()
    if parent_waits:
        with pytest.raises(subprocess.TimeoutExpired) as caught:
            run_launcher(command,cwd=tmp_path,timeout=2)
        assert 'partial launcher evidence' in caught.value.output
    else:
        result=run_launcher(command,cwd=tmp_path,timeout=5)
        assert result.returncode==0 and 'partial launcher evidence' in result.stdout
    assert time.monotonic()-start < 10
    assert_stopped(int((tmp_path/'descendant.pid').read_text()))
    # All fixture handles are closed; no file lock prevents source cleanup.
    source.rename(tmp_path/'preserved launcher.py')


def test_nonzero_exit_and_diagnostics_are_not_suppressed(tmp_path):
    result=run_launcher([sys.executable,'-c',"import sys;print('out');print('err',file=sys.stderr);sys.exit(7)"],
                        cwd=tmp_path,timeout=5)
    assert result.returncode==7 and result.stdout.strip()=='out' and result.stderr.strip()=='err'


def test_actual_batch_bootstrap_claims_unique_directories_during_concurrent_collisions(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import shutil
    import tempfile
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setenv('RANDOM','17')
    # Short disposable paths also respect .NET Framework's legacy path limits.
    with tempfile.TemporaryDirectory(prefix='psy-atomic-') as folder:
        workspace=Path(folder)
        bootstrap=workspace/'native';bootstrap.mkdir()
        occupied=bootstrap/'PsyCoLab-launch-17-17-1';occupied.mkdir()
        (occupied/'preserve').write_bytes(b'unrelated existing candidate')
        sources=[]
        for name in ('first source','second source'):
            source=workspace/name;source.mkdir();sources.append(source)
            (source/'scripts').mkdir();(source/'packaging/windows').mkdir(parents=True)
            shutil.copy2(root/'run_psycolab.bat',source/'run_psycolab.bat')
            shutil.copy2(root/'scripts/windows_startup.cmd',source/'scripts/windows_startup.cmd')
            (source/'packaging/windows/GuidedSetup.cs').write_text(
                'class BootstrapProbe { static int Main(string[] args) {'
                ' System.Threading.Thread.Sleep(300);'
                ' System.IO.File.WriteAllText("claimed.txt",System.AppDomain.CurrentDomain.BaseDirectory);'
                ' return 0; } }',encoding='utf-8')
        def launch(source):
            return run_launcher(['cmd.exe','/d','/c','call run_psycolab.bat'],
                cwd=source,timeout=20,bootstrap_root=bootstrap)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(launch,sources))
        assert all(r.returncode==0 for r in results),[(r.stdout,r.stderr) for r in results]
        assert len({(source/'claimed.txt').read_text() for source in sources})==2
        assert set(bootstrap.iterdir())=={occupied}
        assert (occupied/'preserve').read_bytes()==b'unrelated existing candidate'


def test_genuine_bootstrap_compile_failure_retains_report_and_is_not_approved():
    import shutil
    import tempfile
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='psy-compile-fail-') as folder:
        workspace=Path(folder)
        source=workspace/'source';source.mkdir()
        bootstrap=workspace/'native';bootstrap.mkdir()
        (source/'scripts').mkdir();(source/'packaging/windows').mkdir(parents=True)
        shutil.copy2(root/'run_psycolab.bat',source/'run_psycolab.bat')
        shutil.copy2(root/'scripts/windows_startup.cmd',source/'scripts/windows_startup.cmd')
        (source/'packaging/windows/GuidedSetup.cs').write_text('this is deliberately invalid CSharp',encoding='utf-8')
        try:
            result=run_launcher(['cmd.exe','/d','/c','call run_psycolab.bat'],
                cwd=source,timeout=3,bootstrap_root=bootstrap)
        except subprocess.TimeoutExpired as error:
            diagnostic=error.stderr
        else:
            # A desktop may reject the modal immediately; it must still fail.
            assert result.returncode!=0
            diagnostic=result.stderr
        assert 'error CS' in diagnostic and 'Native bootstrap log' in diagnostic
        reports=list(bootstrap.glob('PsyCoLab-launch-*/bootstrap.log'))
        assert len(reports)==1 and 'error CS' in reports[0].read_text()
