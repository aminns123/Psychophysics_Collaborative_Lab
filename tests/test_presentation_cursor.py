"""Cursor policy at window ownership boundaries, outside scientific timing."""
import ctypes
import sys
from types import SimpleNamespace

import pytest

from psychophysics_lab.core import cursor
from psychophysics_lab.core.presentation import Presentation


class Window:
    instances = []
    def __init__(self, **kwargs):
        self._mouse_visible = True
        self._mouse_in_window = False
        self._has_focus = False
        self.platform_visible = True
        self.visible = kwargs.get("visible", True)
        self.width, self.height = 800, 600
        self.closed = False
        self.calls = []
        self.instances.append(self)
    def set_mouse_visible(self, visible):
        self._mouse_visible = visible
        self.calls.append(("mouse", visible))
        self.set_mouse_platform_visible()
    def set_mouse_platform_visible(self, visible=None):
        self.platform_visible = (self._mouse_visible or not self._mouse_in_window
                                 or not self._has_focus) if visible is None else visible
    def set_visible(self, visible):
        self.visible = visible
        self._has_focus = visible
        self.calls.append(("window", visible))
        # Pyglet 1.5's Win32 focus handler makes this explicit request.
        self.set_mouse_platform_visible(True)
    def push_handlers(self, **handlers):
        self.handlers = handlers
    def close(self):
        self.closed = True
        self.visible = False
        self.set_mouse_platform_visible(True)


def test_stationary_pointer_focus_moves_and_explicit_mouse_opt_in(monkeypatch):
    inside = [True]
    monkeypatch.setattr(cursor, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(cursor, "_pointer_in_client", lambda w: inside[0])
    window = cursor.presentation_window_class(Window)(visible=False)
    assert window.platform_visible  # TUI remains visible before presentation.
    window.set_visible(True)
    assert not window._mouse_in_window and not window.platform_visible
    for _ in range(3):
        window.set_mouse_platform_visible(True)
        assert not window.platform_visible
    window._has_focus = False
    inside[0] = False  # foreground is another application, not this client.
    window.set_mouse_platform_visible(True)
    assert window.platform_visible
    window._has_focus = True
    inside[0] = True
    window.set_mouse_platform_visible(True)
    assert not window.platform_visible
    inside[0] = False
    window.set_mouse_platform_visible()
    assert window.platform_visible
    inside[0] = True
    window.set_mouse_platform_visible(True)
    assert not window.platform_visible
    window.set_mouse_visible(True)
    window.set_mouse_platform_visible(True)
    assert window.platform_visible
    window.close()
    assert window.closed and window.platform_visible
    calls = list(window.calls)
    window.close()
    assert window.calls == calls and window.platform_visible


def test_mouse_response_window_starts_with_visible_cursor(monkeypatch):
    monkeypatch.setattr(cursor, "_pointer_in_client", lambda w: True)
    window = cursor.presentation_window_class(Window, show_mouse_cursor=True)(visible=False)
    window.set_visible(True)
    assert window._mouse_visible and window.platform_visible
    window.close()
    assert window.platform_visible


def test_native_app_activation_restores_cursor_even_with_stale_keyboard_focus(monkeypatch):
    class NativeWindow(Window):
        _platform_event_names = set()
        def _event_setcursor(self, *args):
            return None
    monkeypatch.setattr(cursor, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(cursor, "_pointer_in_client", lambda w: True)
    monkeypatch.setitem(sys.modules, "pyglet.window", SimpleNamespace(_PlatformEventHandler=lambda code: lambda f: f))
    monkeypatch.setitem(sys.modules, "pyglet.libs.win32.constants", SimpleNamespace(WM_ACTIVATEAPP=28, WM_SETCURSOR=32))
    window = cursor.presentation_window_class(NativeWindow)(visible=False)
    window.set_visible(True)
    assert not window.platform_visible
    window._cursor_activate_app(28, 0, 0)
    assert window._has_focus and window.platform_visible
    window._cursor_activate_app(28, 1, 0)
    assert not window.platform_visible and window._event_setcursor(32, 0, 0) == 1
    window.set_mouse_visible(True)
    assert window.platform_visible and window._event_setcursor(32, 0, 0) is None
    window.close()


@pytest.mark.parametrize("origin", [(0, 0), (-1920, 0), (1920, -1080)])
@pytest.mark.parametrize("local,inside", [((10, 20), True), ((-1, 20), False), ((800, 20), False)])
def test_selected_client_bounds_include_negative_monitor_origins(monkeypatch, origin, local, inside):
    class Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    class Rect(ctypes.Structure):
        _fields_ = [(k, ctypes.c_long) for k in ("left", "top", "right", "bottom")]
    def position(pointer):
        pointer._obj.x, pointer._obj.y = origin[0]+local[0], origin[1]+local[1]
        return 1
    def convert(handle, pointer):
        assert handle == "SELECTED_VIEW"
        pointer._obj.x -= origin[0]
        pointer._obj.y -= origin[1]
        return 1
    def bounds(handle, pointer):
        assert handle == "SELECTED_VIEW"
        pointer._obj.left, pointer._obj.top, pointer._obj.right, pointer._obj.bottom = 0, 0, 800, 600
        return 1
    monkeypatch.setitem(sys.modules, "pyglet.libs.win32", SimpleNamespace(_user32=SimpleNamespace(
        GetForegroundWindow=lambda: "SELECTED_MAIN", GetCursorPos=position, ScreenToClient=convert, GetClientRect=bounds)))
    monkeypatch.setitem(sys.modules, "pyglet.libs.win32.types", SimpleNamespace(POINT=Point, RECT=Rect))
    assert cursor._pointer_in_client(SimpleNamespace(_hwnd="SELECTED_MAIN", _view_hwnd="SELECTED_VIEW")) is inside
    assert not cursor._pointer_in_client(SimpleNamespace(_hwnd="BACKGROUND_WINDOW", _view_hwnd="SELECTED_VIEW"))


@pytest.mark.parametrize("failure", [None, "resolution", "show"])
def test_presentation_initialisation_hides_before_show_and_always_closes_on_error(monkeypatch, failure):
    monkeypatch.setattr(cursor, "_pointer_in_client", lambda w: True)
    monkeypatch.setitem(sys.modules, "pyglet", SimpleNamespace(window=SimpleNamespace(Window=Window)))
    monkeypatch.setattr("psychophysics_lab.core.display.select_screen", lambda p: ("SELECTED", {}))
    created = []
    def create(screen, *, window_factory, **kwargs):
        assert screen == "SELECTED" and kwargs["fullscreen"] and kwargs["vsync"]
        assert kwargs["visible"] is False
        window = window_factory(**kwargs)
        created.append(window)
        assert not window.visible and not window._mouse_visible
        if failure == "show":
            def fail(_):
                raise RuntimeError("Native show failure")
            window.set_visible = fail
        return window, {}
    monkeypatch.setattr("psychophysics_lab.core.output_precision.create_output_window", create)
    profile = SimpleNamespace(expected_resolution_px=(100, 100) if failure == "resolution" else (800, 600),
                              refresh_rate_hz=60, id="display")
    if failure:
        with pytest.raises((ValueError, RuntimeError)):
            Presentation(profile, None)
        assert created[-1].closed and created[-1].platform_visible
    else:
        presentation = Presentation(profile, None)
        assert presentation.window.visible and not presentation.window.platform_visible
        presentation.close()
        assert created[-1].closed and created[-1].platform_visible
