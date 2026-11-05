"""Window-scoped cursor visibility through the existing Pyglet backend."""
import sys


def _pointer_in_client(window):
    """Read the selected HWND's client area, including negative monitor origins.

    Pyglet's mouse-enter flag can still be false when a stationary pointer is
    already inside a newly focused window. Do not move or clip the pointer.
    """
    from ctypes import byref
    from pyglet.libs.win32 import _user32
    from pyglet.libs.win32.types import POINT, RECT
    handle = getattr(window, "_view_hwnd", None)
    if _user32.GetForegroundWindow() != getattr(window, "_hwnd", None):
        return False
    if handle:
        point, bounds = POINT(), RECT()
        if (_user32.GetCursorPos(byref(point))
                and _user32.ScreenToClient(handle, byref(point))
                and _user32.GetClientRect(handle, byref(bounds))):
            return bounds.left <= point.x < bounds.right and bounds.top <= point.y < bounds.bottom
    return bool(getattr(window, "_mouse_in_window", False))


def presentation_window_class(window_type, *, show_mouse_cursor=False):
    """Keep logical visibility across Pyglet 1.5 Windows focus transitions.

    Pyglet's focus handler calls set_exclusive_mouse(False), which requests a
    visible platform cursor even when set_mouse_visible(False) was selected.
    Reconcile that request only for this focused window's client area. Public
    set_mouse_visible(True) remains an explicit opt-in for mouse-response tasks.
    """
    if type(show_mouse_cursor) is not bool:
        raise ValueError("Show mouse cursor must be a boolean.")
    native_events = sys.platform == "win32" and hasattr(window_type, "_platform_event_names")
    if native_events:
        from pyglet.window import _PlatformEventHandler
        from pyglet.libs.win32.constants import WM_ACTIVATEAPP, WM_SETCURSOR

    class PresentationWindow(window_type):
        def __init__(self, *args, **kwargs):
            self._cursor_policy_active = True
            self._cursor_app_active = False
            super().__init__(*args, **kwargs)
            self.set_mouse_visible(show_mouse_cursor)

        def set_visible(self, visible=True):
            self._cursor_app_active = bool(visible)
            super().set_visible(visible)
            self.set_mouse_platform_visible()

        def set_mouse_platform_visible(self, platform_visible=None):
            if (sys.platform == "win32" and self._cursor_policy_active and self._cursor_app_active
                    and not self._mouse_visible
                    and _pointer_in_client(self)):
                platform_visible = False
            return super().set_mouse_platform_visible(platform_visible)

        if native_events:
            @_PlatformEventHandler(WM_ACTIVATEAPP)
            def _cursor_activate_app(self, msg, active, data):
                # Foreground loss can precede/omit Pyglet's remembered keyboard
                # focus update. Restore the desktop cursor on this OS event.
                self._cursor_app_active = bool(active)
                self.set_mouse_platform_visible(None if active else True)

            @_PlatformEventHandler(WM_SETCURSOR)
            def _event_setcursor(self, msg, window, data):
                if (self._cursor_policy_active and self._cursor_app_active
                        and not self._mouse_visible and _pointer_in_client(self)):
                    self.set_mouse_platform_visible(False)
                    return 1
                return super()._event_setcursor(msg, window, data)

        def close(self):
            if not self._cursor_policy_active:
                return super().close()
            self._cursor_policy_active = False
            try:
                self.set_mouse_visible(True)
            finally:
                super().close()

    return PresentationWindow
