"""Windows/Pyglet display-selection regression tests without real hardware."""
from dataclasses import replace
from types import ModuleType, SimpleNamespace
import sys

import pytest

from psychophysics_lab.config.models import MonitorProfile
from psychophysics_lab.core.display import select_screen, screen_info


class Win32Screen:
    """Separate snapshots are deliberately different Python objects."""

    def __init__(self, x, y, width, height, device_id=None, refresh=60):
        self.x, self.y, self.width, self.height = x, y, width, height
        self.device_id = device_id
        self.refresh = refresh

    def get_device_name(self):
        return self.device_id

    def get_mode(self):
        return SimpleNamespace(rate=self.refresh)


def install_fake_displays(monkeypatch, screens, default):
    display = SimpleNamespace(get_screens=lambda: list(screens), get_default_screen=lambda: default)
    module = ModuleType("pyglet")
    module.canvas = SimpleNamespace(get_display=lambda: display)
    monkeypatch.setitem(sys.modules, "pyglet", module)


def profile(**overrides):
    basic = MonitorProfile("legacy_reference_display", "Legacy", .61, .35, 60, 1.0,
                           expected_resolution_px=(1920, 1080))
    return replace(basic, **overrides)


def test_default_monitor_snapshot_is_not_list_object(monkeypatch):
    first = Win32Screen(0, 0, 1920, 1080, "DISPLAY1")
    second = Win32Screen(1920, 0, 1920, 1080, "DISPLAY2")
    independently_created_default = Win32Screen(0, 0, 1920, 1080, "DISPLAY1")
    assert independently_created_default is not first
    install_fake_displays(monkeypatch, [first, second], independently_created_default)
    selected, identity = select_screen(profile())
    assert selected is first
    assert identity["index"] == 0
    assert identity["binding_status"] == "legacy_default_unverified"


def test_explicit_binding_survives_monitor_reordering(monkeypatch):
    left = Win32Screen(0, 0, 1920, 1080, "A")
    right = Win32Screen(1920, 0, 1920, 1080, "B")
    install_fake_displays(monkeypatch, [right, left], left)
    bound = profile(id="local_monitor", origin="local",
                    display_binding={"index": 1, "x": 1920, "y": 0, "width": 1920,
                                     "height": 1080, "device_id": "B"})
    chosen, identity = select_screen(bound)
    assert chosen is right
    assert identity["device_id"] == "B"
    assert identity["binding_status"] == "explicit"


def test_default_monitor_ambiguity_fails_closed(monkeypatch):
    one = Win32Screen(0, 0, 1920, 1080, None)
    two = Win32Screen(0, 0, 1920, 1080, None)
    install_fake_displays(monkeypatch, [one, two], Win32Screen(0, 0, 1920, 1080, None))
    with pytest.raises(ValueError, match="ambiguous"):
        select_screen(profile())


def test_dpi_or_resolution_mismatch_is_explained(monkeypatch):
    logical = Win32Screen(0, 0, 1536, 960, "DISPLAY1")
    install_fake_displays(monkeypatch, [logical], Win32Screen(0, 0, 1536, 960, "DISPLAY1"))
    with pytest.raises(ValueError, match="scaling/DPI"):
        select_screen(profile())


@pytest.mark.parametrize("rate", ["unknown", object(), 0, -5, float("nan"), float("inf")])
def test_driver_without_numeric_refresh_does_not_crash(rate):
    result = screen_info(Win32Screen(0, 0, 1920, 1080, "DISPLAY1", refresh=rate), 0)
    assert result.refresh_hz is None


def test_windows_display_driver_without_device_id(monkeypatch):
    screen = Win32Screen(0, 0, 1920, 1080, None)
    install_fake_displays(monkeypatch, [screen], Win32Screen(0, 0, 1920, 1080, None))
    chosen, _ = select_screen(profile())
    assert chosen is screen
