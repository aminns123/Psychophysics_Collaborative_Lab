"""Lazy Pyglet 1.5 display binding, with a pure resolver for headless tests."""
from dataclasses import asdict, dataclass
from typing import Any

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
    mode=screen.get_mode() if hasattr(screen,'get_mode') else None
    rate=getattr(mode,'rate',None)
    identity=screen.get_device_name() if hasattr(screen,'get_device_name') else getattr(screen,'device_name',None)
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

def select_screen(profile):
    import pyglet
    screens=pyglet.canvas.get_display().get_screens()
    infos=[screen_info(screen,i) for i,screen in enumerate(screens)]
    if profile.display_binding:
        info=resolve_binding(profile.display_binding,infos)
    elif profile.id=='legacy_reference_display':
        # Explicit compatibility policy for the existing unbound reference only.
        screen=pyglet.canvas.get_display().get_default_screen()
        info=screen_info(screen,screens.index(screen))
    else: raise ValueError('Local profiles need an explicit monitor binding.')
    if profile.expected_resolution_px and (info.width,info.height)!=profile.expected_resolution_px:
        raise ValueError('Bound monitor resolution differs from the selected profile.')
    if profile.display_binding and info.refresh_hz and abs(info.refresh_hz-profile.refresh_rate_hz)>.5:
        raise ValueError('Bound monitor refresh mode differs from the selected profile.')
    return screens[info.index],asdict(info)|{'binding_status':'explicit' if profile.display_binding else 'legacy_default_unverified','refresh_source':'OS mode' if info.refresh_hz else 'unknown','photon_timing_verified':False}
