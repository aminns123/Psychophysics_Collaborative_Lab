"""Bound a Windows launcher test and own all of its descendant processes.

Test infrastructure only. File-backed output cannot wait forever for an inherited
pipe held by a console/GUI descendant. A private Windows job closes the entire
test process tree on success, failure or timeout. The worker waits for explicit
permission before spawning anything, avoiding a job-assignment race.
"""
import ctypes
from ctypes import wintypes
from contextlib import nullcontext
import json
import locale
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


class _BasicLimits(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', wintypes.DWORD), ('minimum_working_set', ctypes.c_size_t),
                ('maximum_working_set', ctypes.c_size_t), ('active_process_limit', wintypes.DWORD),
                ('affinity', ctypes.c_size_t), ('priority_class', wintypes.DWORD),
                ('scheduling_class', wintypes.DWORD)]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [('basic', _BasicLimits), ('io', _IoCounters),
                ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]


class _Accounting(ctypes.Structure):
    _fields_ = [(name, ctypes.c_longlong) for name in
                ('total_user', 'total_kernel', 'period_user', 'period_kernel')] + [
                (name, wintypes.DWORD) for name in
                ('page_faults', 'total_processes', 'active_processes', 'terminated_processes')]


class _ProcessIds(ctypes.Structure):
    _fields_ = [('assigned', wintypes.DWORD), ('listed', wintypes.DWORD),
                ('ids', ctypes.c_size_t * 128)]


def _kernel():
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    api.CreateJobObjectW.restype = wintypes.HANDLE
    api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    api.SetInformationJobObject.restype = wintypes.BOOL
    api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    api.AssignProcessToJobObject.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    api.TerminateJobObject.restype = wintypes.BOOL
    api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                              ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
    api.QueryInformationJobObject.restype = wintypes.BOOL
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    api.IsProcessInJob.restype = wintypes.BOOL
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    return api


def run_launcher(command, *, cwd, timeout, bootstrap_root=None):
    """Return CompletedProcess or raise TimeoutExpired; never approve a failure.

    Used only for isolated launcher fixtures, never real experiment acquisition.
    No arbitrary machine process enumeration or termination is performed.
    """
    api = _kernel()
    job = api.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    process = None
    # A caller can deliberately share its own private root to exercise repeated
    # and colliding bootstrap launches; never use the real machine temp inventory.
    native_context = (tempfile.TemporaryDirectory(prefix='psy-launch-test-')
                      if bootstrap_root is None else nullcontext(str(bootstrap_root)))
    with native_context as native_temp, \
            tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        try:
            limits = _ExtendedLimits()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not api.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            process = subprocess.Popen([sys.executable, '-I', '-u', str(Path(__file__).resolve()),
                '--worker', json.dumps(command), str(cwd)], stdin=subprocess.PIPE,
                stdout=output, stderr=error, creationflags=subprocess.CREATE_NO_WINDOW,
                env=os.environ | {'TEMP': native_temp, 'TMP': native_temp})
            if not api.AssignProcessToJobObject(job, int(process._handle)):
                raise ctypes.WinError(ctypes.get_last_error())
            process.stdin.write(b'START\n')
            process.stdin.close()
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                code = None
        finally:
            handles = []
            try:
                # Termination is asynchronous. Closing the job alone can return
                # while a dying descendant still holds its working directory.
                # Wait on observed kernel state before fixture files are removed.
                # Retain handles *before* requesting termination. A job's PID
                # list/accounting can change before each process is signaled.
                members = _ProcessIds()
                if not api.QueryInformationJobObject(job, 3, ctypes.byref(members),
                                                     ctypes.sizeof(members), None):
                    raise ctypes.WinError(ctypes.get_last_error())
                for pid in members.ids[:members.listed]:
                    handle = api.OpenProcess(0x101000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION
                    if handle:
                        if api.WaitForSingleObject(handle, 0) == 0:
                            api.CloseHandle(handle)
                            continue
                        belongs = wintypes.BOOL()
                        if not api.IsProcessInJob(handle, job, ctypes.byref(belongs)) or not belongs.value:
                            api.CloseHandle(handle)
                            raise RuntimeError('A test job member could not be verified before termination.')
                        handles.append(handle)
                    elif ctypes.get_last_error() != 87:  # ERROR_INVALID_PARAMETER: process already gone
                        raise ctypes.WinError(ctypes.get_last_error())
                if not api.TerminateJobObject(job, 1):
                    raise ctypes.WinError(ctypes.get_last_error())
                deadline = time.monotonic() + 5
                for handle in handles:
                    remaining = max(0, int((deadline-time.monotonic())*1000))
                    if api.WaitForSingleObject(handle, remaining) != 0:
                        raise TimeoutError('A private launcher test process did not finish termination.')
                while True:
                    accounting = _Accounting()
                    if not api.QueryInformationJobObject(job, 1, ctypes.byref(accounting),
                                                         ctypes.sizeof(accounting), None):
                        raise ctypes.WinError(ctypes.get_last_error())
                    if accounting.active_processes == 0:
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError('The private launcher test job did not finish termination.')
                    time.sleep(.01)
            finally:
                for handle in handles:
                    api.CloseHandle(handle)
                api.CloseHandle(job)
                # On assignment failure the gated worker has spawned no descendants.
                if process is not None:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                    process._handle.Close()
                    if not process.stdin.closed:
                        process.stdin.close()
        output.seek(0)
        error.seek(0)
        stdout = output.read().decode(locale.getencoding(), errors='replace')
        stderr = error.read().decode(locale.getencoding(), errors='replace')
        if code != 0:
            reports = [*Path(native_temp).glob('PsyCoLab-launch-*.exe.log'),
                       *Path(native_temp).glob('PsyCoLab-launch-*/bootstrap.log')]
            for path in reports:
                stderr += '\nNative bootstrap log:\n' + path.read_text(encoding='utf-8', errors='replace')
    if code is None:
        raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(command, code, stdout, stderr)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--worker' or sys.stdin.buffer.readline() != b'START\n':
        raise SystemExit('A parent-owned test job must authorise the worker.')
    raise SystemExit(subprocess.call(json.loads(sys.argv[2]), cwd=sys.argv[3],
        stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
