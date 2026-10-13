"""Lazy Pyglet 1.5 display binding, with a pure resolver for headless tests."""
from dataclasses import asdict, dataclass
from typing import Any
import math

@dataclass(frozen=True)
class DisplayInfo:
    index: int
    x: int
    y: int
    width: int
    height: int
    refresh_hz: float | None = None
    device_id: str | None = None

def screen_info(screen, index):
    try:
        mode=screen.get_mode() if hasattr(screen,'get_mode') else None
    except (OSError, NotImplementedError):
        mode = None
    rate = getattr(mode, 'rate', None)
    try:
        rate = float(rate) if rate is not None else None
        if rate is not None and (not math.isfinite(rate) or rate <= 0):
            rate = None
    except (TypeError, ValueError, OverflowError):
        rate = None
    try:
        identity = screen.get_device_name() if hasattr(screen, 'get_device_name') else getattr(screen, 'device_name', None)
    except (OSError, NotImplementedError):
        identity = getattr(screen, 'device_name', None)
    if isinstance(identity,bytes): identity=identity.decode(errors='replace')
    return DisplayInfo(index,int(screen.x),int(screen.y),int(screen.width),int(screen.height),float(rate) if rate else None,str(identity) if identity else None)

def enumerate_displays():
    import pyglet
    return [screen_info(screen,i) for i,screen in enumerate(pyglet.canvas.get_display().get_screens())]

def resolve_binding(binding: dict, displays: list[DisplayInfo]) -> DisplayInfo:
    if not binding: raise ValueError('Select and save a physical display binding first.')
    if binding.get('device_id'):
        matches=[d for d in displays if d.device_id==binding['device_id']]
    else:
        matches=[d for d in displays if all(getattr(d,k)==binding.get(k) for k in ('index','x','y','width','height'))]
    if len(matches)!=1: raise ValueError('Bound monitor is missing or ambiguous; reselect it. No primary-screen fallback was used.')
    return matches[0]

def preflight_fullscreen_display(profile, displays=None) -> DisplayInfo | None:
    """Check a saved physical monitor binding *before* closing the Textual UI.

    An unbound local profile is a legitimate saved geometry draft, NOT a
    runnable hardware calibration. We must not silently choose the primary
    screen, even when Windows reports only one monitor.
    """
    if not profile.display_binding and profile.id != "legacy_reference_display":
        raise ValueError(
            f"Monitor profile '{profile.id}' is an UNBOUND DRAFT. "
            "Its geometry was saved, but no physical display was selected. "
            "Go to Calibrate → Edit / copy display profile → "
            "Detect connected displays; select the correct display and "
            "press Save local revision. Then launch the display test."
        )
    if displays is None:
        displays = enumerate_displays()
    if not displays:
        raise ValueError(
            "No connected monitors were detected. Check the display connection "
            "before launching a fullscreen calibration test."
        )
    if not profile.display_binding:
        # Only the original historical reference profile permits legacy
        # primary-screen selection; select_screen checks its identity later.
        return None
    info = resolve_binding(profile.display_binding, displays)
    if profile.expected_resolution_px and (
        info.width, info.height
    ) != profile.expected_resolution_px:
        raise ValueError(
            f"Bound display currently reports {info.width} × {info.height} pixels, "
            f"but the saved profile expects "
            f"{profile.expected_resolution_px[0]} × {profile.expected_resolution_px[1]}. "
            "Use Calibrate → Edit / copy display profile, select the monitor, "
            "verify Windows resolution/DPI and save an updated local revision."
        )
    if info.refresh_hz and abs(info.refresh_hz - profile.refresh_rate_hz) > .5:
        raise ValueError(
            f"Bound display currently reports {info.refresh_hz:g} Hz, "
            f"but profile expects {profile.refresh_rate_hz:g} Hz. "
            "Use Calibrate → Edit / copy display profile to review its refresh "
            "rate, then save a revised profile."
        )
    return info


def select_screen(profile):
    import pyglet
    display = pyglet.canvas.get_display()
    screens = display.get_screens()
    if not screens:
        raise ValueError('No connected displays were found.')
    infos=[screen_info(screen,i) for i,screen in enumerate(screens)]
    if profile.display_binding:
        info=resolve_binding(profile.display_binding,infos)
    elif profile.id=='legacy_reference_display':
        # Explicit compatibility policy for the existing unbound reference only.
        # Pyglet 1.5 on Windows re-enumerates screens for each call. Match
        # physical identity, then return a handle from our single snapshot.
        default = screen_info(display.get_default_screen(), -1)
        if default.device_id:
            matches = [item for item in infos if item.device_id == default.device_id]
        else:
            matches = [item for item in infos if all(
                getattr(item, key) == getattr(default, key) for key in ('x', 'y', 'width', 'height'))]
        if len(matches) != 1:
            raise ValueError('Default monitor is missing or ambiguous; detect displays again.')
        info = matches[0]
    else: raise ValueError('Local profiles need an explicit monitor binding.')
    if profile.expected_resolution_px and (info.width,info.height)!=profile.expected_resolution_px:
        raise ValueError(
            f"Selected display reports {info.width}x{info.height} pixels, but profile "
            f"expects {profile.expected_resolution_px[0]}x{profile.expected_resolution_px[1]}. "
            "Check Windows resolution, display scaling/DPI awareness and the physical monitor binding; "
            "do not assume reported logical pixels are the framebuffer size."
        )
    if profile.display_binding and info.refresh_hz and abs(info.refresh_hz-profile.refresh_rate_hz)>.5:
        raise ValueError('Bound monitor refresh mode differs from the selected profile.')
    return screens[info.index],asdict(info)|{'binding_status':'explicit' if profile.display_binding else 'legacy_default_unverified','refresh_source':'OS mode' if info.refresh_hz else 'unknown','photon_timing_verified':False}
