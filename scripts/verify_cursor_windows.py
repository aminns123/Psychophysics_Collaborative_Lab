"""Opt-in native cursor checks; briefly moves the pointer and opens blank windows.

Run on an interactive Windows desktop. Original pointer/focus are restored.
Uses no experiment, participant, installation or calibration records.
"""
import argparse
import ctypes as ct
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child-ready", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--control-ready", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--owner-pid", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("This opt-in check requires an interactive Windows desktop.")
    api = ct.WinDLL("user32", use_last_error=True)
    api.GetForegroundWindow.restype = wt.HWND
    api.SetForegroundWindow.argtypes = [wt.HWND]
    api.ClientToScreen.argtypes = [wt.HWND, ct.POINTER(wt.POINT)]
    class CursorInfo(ct.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD),
                    ("hCursor", wt.HANDLE), ("ptScreenPos", wt.POINT)]
    def visible():
        info = CursorInfo(cbSize=ct.sizeof(CursorInfo))
        if not api.GetCursorInfo(ct.byref(info)):
            raise ct.WinError(ct.get_last_error())
        return bool(info.flags & 1)
    def pump(window, seconds=.12):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if getattr(window, "_hwnd", None):
                window.dispatch_events()
            time.sleep(.005)
    def centre(window):
        point = wt.POINT(window.width//2, window.height//2)
        if not api.ClientToScreen(window._view_hwnd, ct.byref(point)):
            raise ct.WinError(ct.get_last_error())
        return point.x, point.y
    original_point = wt.POINT()
    api.GetCursorPos(ct.byref(original_point))
    original_focus = api.GetForegroundWindow()
    if not args.worker and not args.child_ready and not args.control_ready:
        worker = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--worker"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            try:
                stdout, stderr = worker.communicate(timeout=45)
            except subprocess.TimeoutExpired:
                worker.kill()
                stdout, stderr = worker.communicate(timeout=5)
                sys.stdout.buffer.write(stdout)
                sys.stderr.buffer.write(stderr)
                raise RuntimeError("Native probe exceeded 45 seconds and was stopped")
            sys.stdout.buffer.write(stdout)
            sys.stderr.buffer.write(stderr)
            if worker.returncode:
                raise SystemExit(worker.returncode)
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=5)
            api.SetForegroundWindow(original_focus)
            api.SetCursorPos(original_point.x, original_point.y)
        return
    import pyglet
    from psychophysics_lab.core.cursor import presentation_window_class
    screens = pyglet.canvas.get_display().get_screens()
    cls = presentation_window_class(pyglet.window.Window)
    results = []
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wt.HANDLE
    kernel.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    owner = kernel.OpenProcess(0x100000, False, args.owner_pid) if args.owner_pid else None
    def owner_alive():
        return not args.owner_pid or (owner and kernel.WaitForSingleObject(owner, 0) == 258)
    try:
        if args.control_ready:
            control = pyglet.window.Window(width=180, height=90, visible=True, vsync=False,
                                           caption="PsyCoLab cursor focus control")
            pump(control)
            args.control_ready.write_text(json.dumps({"window": control._hwnd}), encoding="utf-8")
            while getattr(control, "_hwnd", None) and owner_alive():
                pump(control)
            control.close()
            return
        if args.child_ready:
            window = cls(width=240, height=120, visible=False, vsync=False)
            api.SetCursorPos(*centre(window))
            window.set_visible(True)
            pump(window)
            assert not visible(), "Child cursor did not hide"
            args.child_ready.write_text(json.dumps({"hidden": True}), encoding="utf-8")
            while owner_alive():
                pump(window)
            window.close()
            return
        for index, screen in enumerate(screens):
            for fullscreen in (False, True):
                for ending in ("normal", "escape", "error"):
                    print(json.dumps({"stage": "create", "screen": index, "fullscreen": fullscreen, "ending": ending}), flush=True)
                    window = cls(screen=screen, width=None if fullscreen else 240,
                                 height=None if fullscreen else 120, fullscreen=fullscreen,
                                 visible=False, vsync=False, caption="PsyCoLab cursor verification")
                    try:
                        if not fullscreen:
                            window.set_location(screen.x+50, screen.y+50)
                        xy = centre(window)
                        api.SetCursorPos(*xy)  # stationary before showing/focus.
                        window.set_visible(True)
                        print(json.dumps({"stage": "initial_focus"}), flush=True)
                        pump(window)
                        assert not visible(), "Cursor visible at initial focus"
                        api.SetCursorPos(xy[0]+5, xy[1]+5)
                        pump(window)
                        assert not visible(), "Cursor visible after motion"
                        # A separate process models the TUI/terminal's native
                        # window, without relying on a taskbar/desktop target.
                        print(json.dumps({"stage": "focus_away"}), flush=True)
                        with tempfile.TemporaryDirectory(prefix="psycolab-cursor-focus-") as directory:
                            ready = Path(directory)/"control.json"
                            control = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--control-ready", str(ready), "--owner-pid", str(os.getpid())],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
                            try:
                                end = time.monotonic()+10
                                while not ready.exists() and control.poll() is None and time.monotonic()<end:
                                    pump(window, .02)
                                if not ready.exists():
                                    raise RuntimeError("Native control window did not become ready")
                                target = json.loads(ready.read_text())["window"]
                                api.SetForegroundWindow(target)
                                pump(window)
                                assert api.GetForegroundWindow() == target, "Control did not gain foreground"
                                assert visible(), "Cursor hidden outside presentation focus"
                            finally:
                                control.terminate()
                                control.wait(timeout=5)
                        window.set_visible(True)
                        window.activate()
                        print(json.dumps({"stage": "focus_return"}), flush=True)
                        pump(window)
                        assert not visible(), "Cursor reappeared after focus return"
                        window.set_mouse_visible(True)
                        pump(window)
                        assert visible(), "Explicit mouse-response cursor not visible"
                        window.set_mouse_visible(False)
                        pump(window)
                        assert not visible()
                        if ending == "escape":
                            window.dispatch_event("on_key_press", pyglet.window.key.ESCAPE, 0)
                            pump(window)
                            # In manual-dispatch presentation, Escape requests
                            # exit; RunContext then owns the actual close.
                            assert window.has_exit
                            window.close()
                        elif ending == "error":
                            try:
                                raise RuntimeError("Safely injected lifecycle error")
                            except RuntimeError:
                                window.close()
                        else:
                            window.close()
                        assert visible(), "Cursor not restored after close"
                        results.append({"screen": index, "origin": [screen.x, screen.y],
                                        "fullscreen": fullscreen, "ending": ending, "status": "PASS"})
                    finally:
                        window.close()
        with tempfile.TemporaryDirectory(prefix="psycolab-cursor-check-") as directory:
            ready = Path(directory)/"ready.json"
            child = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--child-ready", str(ready), "--owner-pid", str(os.getpid())],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                end = time.monotonic()+15
                while not ready.exists() and child.poll() is None and time.monotonic()<end:
                    time.sleep(.02)
                if not ready.exists():
                    raise RuntimeError("Cursor child did not become ready")
                assert not visible()
                child.terminate()  # intentionally no Python finally/close.
                child.wait(timeout=5)
                api.SetForegroundWindow(original_focus)
                api.SetCursorPos(original_point.x, original_point.y)
                time.sleep(.15)
                assert visible(), "OS cursor not restored after terminated process"
                results.append({"ending": "terminated_process", "status": "PASS"})
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        print(json.dumps({"status": "PASS", "windows": platform.win32_ver(),
                          "screens": len(screens), "checks": results}))
    finally:
        if owner:
            kernel.CloseHandle(owner)
        if not args.control_ready and not args.child_ready:
            api.SetForegroundWindow(original_focus)
            api.SetCursorPos(original_point.x, original_point.y)


if __name__ == "__main__":
    main()
