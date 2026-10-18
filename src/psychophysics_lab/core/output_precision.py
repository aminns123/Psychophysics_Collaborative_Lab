"""Display signal reporting and central framebuffer selection; no photometry.

Imports of Windows/OpenGL stay inside hardware functions. Stimulus equations
remain floating-point and independent of the selected output format.
"""
import ctypes as ct
import sys
import warnings


def windows_output(device_id):
    """Read the active signal for one GDI display name, never the primary by guess.

    QueryDisplayConfig and DisplayConfigGetDeviceInfo are read-only. A clone
    source with multiple targets is ambiguous and is reported as such.
    """
    unknown = {"status": "unknown", "device_id": device_id,
               "bits_per_color_channel": None, "physical_precision_verified": False}
    if sys.platform != "win32" or not device_id:
        return unknown | {"reason": "Windows display identity is unavailable"}
    U = ct.c_uint32
    class Luid(ct.Structure):
        _fields_ = [("low", U), ("high", ct.c_int32)]
    class Ratio(ct.Structure):
        _fields_ = [("numerator", U), ("denominator", U)]
    class Source(ct.Structure):
        _fields_ = [("adapter", Luid), ("id", U), ("mode", U), ("flags", U)]
    class Target(ct.Structure):
        _fields_ = [("adapter", Luid), ("id", U), ("mode", U), ("technology", U),
                    ("rotation", U), ("scaling", U), ("refresh", Ratio),
                    ("scanline", U), ("available", ct.c_int32), ("flags", U)]
    class DisplayPath(ct.Structure):
        _fields_ = [("source", Source), ("target", Target), ("flags", U)]
    class Header(ct.Structure):
        _fields_ = [("type", U), ("size", U), ("adapter", Luid), ("id", U)]
    class SourceName(ct.Structure):
        _fields_ = [("header", Header), ("name", ct.c_wchar * 32)]
    class TargetName(ct.Structure):
        _fields_ = [("header", Header), ("flags", U), ("technology", U),
                    ("manufacturer", ct.c_uint16), ("product", ct.c_uint16),
                    ("connector", U), ("friendly", ct.c_wchar * 64), ("path", ct.c_wchar * 128)]
    class Advanced(ct.Structure):
        _fields_ = [("header", Header), ("flags", U), ("encoding", U), ("bits", U)]
    try:
        api = ct.windll.user32
        for _ in range(3):
            npaths, nmodes = U(), U()
            status = api.GetDisplayConfigBufferSizes(2, ct.byref(npaths), ct.byref(nmodes))
            if status: raise OSError(status, "GetDisplayConfigBufferSizes")
            paths = (DisplayPath * npaths.value)()
            # Mode records are not inspected; reserve more than the SDK stride.
            modes = ct.create_string_buffer(max(1, nmodes.value) * 128)
            status = api.QueryDisplayConfig(2, ct.byref(npaths), paths, ct.byref(nmodes), modes, None)
            if status != 122: break  # retry if display topology changed meanwhile
        if status: raise OSError(status, "QueryDisplayConfig")
        matches = []
        for path in paths[:npaths.value]:
            source = SourceName()
            source.header = Header(1, ct.sizeof(source), path.source.adapter, path.source.id)
            if api.DisplayConfigGetDeviceInfo(ct.byref(source)) or source.name.casefold() != device_id.casefold():
                continue
            advanced = Advanced()
            advanced.header = Header(9, ct.sizeof(advanced), path.target.adapter, path.target.id)
            status = api.DisplayConfigGetDeviceInfo(ct.byref(advanced))
            if status: raise OSError(status, "GetAdvancedColorInfo")
            name = TargetName()
            name.header = Header(2, ct.sizeof(name), path.target.adapter, path.target.id)
            name_status = api.DisplayConfigGetDeviceInfo(ct.byref(name))
            matches.append({"status": "reported", "device_id": source.name,
                "monitor_name": name.friendly if not name_status else None,
                "bits_per_color_channel": advanced.bits or None,
                "color_encoding": {0: "RGB", 1: "YCbCr444", 2: "YCbCr422", 3: "YCbCr420"}.get(advanced.encoding, str(advanced.encoding)),
                "advanced_color_enabled": bool(advanced.flags & 2),
                "refresh_hz": path.target.refresh.numerator / max(1, path.target.refresh.denominator),
                "physical_precision_verified": False})
        return matches[0] if len(matches) == 1 else unknown | {
            "reason": "Multiple active targets share this source" if matches else "No matching active display path"}
    except (OSError, AttributeError, ValueError) as exc:
        return unknown | {"reason": str(exc)}


def framebuffer_info(gl=None):
    """Best-effort description of the *obtained* draw buffer.

    Drivers (including some Windows OpenGL implementations) may reject a
    glGetIntegerv pname with GL_INVALID_ENUM. A rejected introspection query is
    NOT evidence that the graphics window or presentation cannot be used.
    Never substitute requested/assumed channel depths for unreadable values.
    """
    if gl is None:
        from pyglet import gl
    errors = []

    def query(label, enum):
        try:
            value = gl.GLint()
            gl.glGetIntegerv(enum, ct.byref(value))
            return value.value
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}: {exc}")
            return None

    bits = {name: query(f"{name}_bits", enum) for name, enum in (
        ("red", gl.GL_RED_BITS), ("green", gl.GL_GREEN_BITS),
        ("blue", gl.GL_BLUE_BITS), ("alpha", gl.GL_ALPHA_BITS))}
    try:
        supports_float_query = gl.gl_info.have_extension("GL_ARB_color_buffer_float")
    except Exception as exc:
        supports_float_query = False
        errors.append(f"color_buffer_float_extension: {type(exc).__name__}: {exc}")

    # The extension absent means the default buffer is not an ARB floating
    # format. If the extension is present but the query fails, its format is
    # UNKNOWN: treating its 16/32 storage bits as normalized integer would
    # overstate usable precision.
    floating = query("rgba_float_mode", 0x8820) if supports_float_query else 0
    numeric_format = ("unknown" if floating is None else
                      "floating_point" if floating else "normalized_integer")
    channels = [bits[c] for c in ("red", "green", "blue")]
    precision = None
    if floating is not None and all(type(v) is int and v > 0 for v in channels):
        if floating:
            # IEEE half has 11 significant bits; single has 24. Other
            # storage sizes are not assumed to have equivalent spacing.
            values = [{16: 11, 32: 24}.get(v) for v in channels]
            if all(v is not None for v in values):
                precision = min(values)
        else:
            precision = min(channels)

    def gl_string(label, fn):
        try:
            return fn()
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}: {exc}")
            return None

    return {"channel_bits": bits, "numeric_format": numeric_format,
            "buffer_precision_bits_in_0_1": precision,
            "inspection_status": "partial" if errors or precision is None else "measured_by_gl",
            "query_errors": errors,
            "renderer": gl_string("renderer", gl.gl_info.get_renderer),
            "gl_version": gl_string("gl_version", gl.gl_info.get_version)}


def format_summary(evidence):
    signal = evidence.get("windows_report", {})
    bits = signal.get("bits_per_color_channel")
    buffer = evidence.get("application_obtained", {})
    channels = buffer.get("channel_bits", {})
    rgb = "/".join(str(channels.get(c, "?")) for c in ("red", "green", "blue"))
    return (f"Windows reports: {str(bits) + '-bit per colour channel' if bits else 'unknown output depth'}"
            f" ({signal.get('monitor_name') or signal.get('device_id') or 'display unknown'}).\n"
            f"Application obtained: RGB {rgb}, {buffer.get('numeric_format', 'unknown')} framebuffer.\n"
            f"{evidence.get('message', '')}")


def inspect_output(window, device_id, *, requested_bits=None, selection="existing_window", attempts=()):
    window.switch_to()
    signal = windows_output(device_id)
    actual = framebuffer_info()
    # Do not let an 8-bit OS signal report silently impose an 8-bit
    # application framebuffer. Preserve the distinction in saved evidence.
    target = requested_bits if requested_bits is not None else max(10, signal.get("bits_per_color_channel") or 0)
    precision = actual.get("buffer_precision_bits_in_0_1")
    unknown = precision is None
    fallback = unknown or precision < target
    status = "unknown" if unknown else "fallback" if fallback else "buffer_sufficient"
    if unknown:
        message = ("OUTPUT PRECISION UNKNOWN: graphics driver rejected or could not "
                   "complete framebuffer inspection. Test presentation remains "
                   "available; do not treat the reported output as verified.")
    elif fallback:
        message = (f"OUTPUT FALLBACK: requested {target}-bit precision; obtained "
                   "lower buffer precision. Test presentation remains available.")
    else:
        message = ("Buffer format inspected; physical distinguishable increments "
                   "still require photometer measurements.")
    return {"schema_version": 1, "selection": selection, "requested_minimum_bits": target,
            "windows_report": signal, "application_obtained": actual,
            "fallback": fallback, "inspection_status": status, "attempts": list(attempts),
            "physical_precision_verified": False, "message": message}


def create_output_window(screen, *, requested_bits=None, window_factory=None, **kwargs):
    """Negotiate a float-preserving buffer centrally, with a visible fallback.

    Prefer exact fixed-point depth where offered; otherwise a float32 buffer
    avoids treating 16-bit float storage as 16-bit uniformly spaced precision.
    Always inspect the obtained context. Never changes HDR, LUT or display mode
    beyond the caller's ordinary window/fullscreen request.
    """
    import pyglet
    from pyglet import gl
    from .display import screen_info
    device_id = screen_info(screen, 0).device_id
    reported = windows_output(device_id)
    # Prefer at least 10-bit *internal* precision where available, even when
    # Windows currently reports an 8-bit output signal. This cannot upgrade
    # the physical link or panel, and fallback remains visible.
    target = requested_bits if requested_bits is not None else max(10, reported.get("bits_per_color_channel") or 0)
    if type(target) is not int or not 1 <= target <= 32:
        raise ValueError("Requested output precision must be an integer from 1 to 32.")
    factory = window_factory or pyglet.window.Window
    visible = kwargs.pop('visible', True)
    candidates, attempts = [], []
    for width in dict.fromkeys((target, 32)):
        try:
            configs = screen.get_matching_configs(gl.Config(
                red_size=width, green_size=width, blue_size=width,
                alpha_size=0, double_buffer=True))
            candidates.extend(configs)
        except Exception as exc:
            # A driver may not expose high-bit-depth formats through Pyglet.
            # A failed format query must not prohibit an ordinary window.
            attempts.append(f"enumerate {width}-bit formats: {type(exc).__name__}: {exc}")
    candidates.sort(key=lambda c: (0 if (c.red_size, c.green_size, c.blue_size) == (target,)*3 else
                                   1 if min(c.red_size, c.green_size, c.blue_size) >= 32 else 2))
    # An ordinary graphics window remains available for test presentation.
    candidates.append(None)
    seen = set()
    saved = None
    for config in candidates:
        key = getattr(config, "_pf", id(config)) if config is not None else "default"
        if key in seen:
            continue
        seen.add(key)
        label = ("default window" if config is None else
                 f"requested RGB {getattr(config, 'red_size', '?')}/"
                 f"{getattr(config, 'green_size', '?')}/"
                 f"{getattr(config, 'blue_size', '?')}")
        window = None
        try:
            window = factory(screen=screen, visible=False, **kwargs,
                             **({"config": config} if config is not None else {}))
        except Exception as exc:
            attempts.append(f"create {label}: {type(exc).__name__}: {exc}")
            if window is not None:
                window.close()
            continue
        try:
            evidence = inspect_output(window, device_id, requested_bits=target,
                                      selection="automatic", attempts=attempts)
        except Exception as exc:
            # A functioning window must not be discarded because diagnostic
            # OpenGL queries fail. This is UNKNOWN, never a verified 8/10-bit.
            detail = f"inspect {label}: {type(exc).__name__}: {exc}"
            attempts.append(detail)
            evidence = {
                "schema_version": 1, "selection": "automatic",
                "requested_minimum_bits": target,
                "windows_report": reported,
                "application_obtained": {
                    "channel_bits": {}, "numeric_format": "unknown",
                    "buffer_precision_bits_in_0_1": None,
                    "inspection_status": "unavailable",
                    "query_errors": [detail],
                },
                "inspection_status": "unknown", "fallback": True,
                "attempts": list(attempts), "physical_precision_verified": False,
                "message": ("OUTPUT PRECISION UNKNOWN: OpenGL inspection failed; "
                            "test presentation remains available. Do not "
                            "interpret the unknown format as verified."),
            }
        if not evidence["fallback"] or config is None:
            saved = (window, evidence)
            break
        attempts.append(
            f"{label}: lower or unknown buffer precision "
            f"({evidence['application_obtained'].get('buffer_precision_bits_in_0_1')}); "
            "trying another format")
        window.close()
    if saved is None:
        raise RuntimeError("Unable to create a presentation window: " + "; ".join(attempts))
    window, evidence = saved
    if evidence["fallback"]:
        warnings.warn(evidence["message"], RuntimeWarning, stacklevel=2)
        qualifier = ("UNKNOWN" if evidence.get("inspection_status") == "unknown"
                     else "FALLBACK")
        window.set_caption(f"PsyCoLab — OUTPUT PRECISION {qualifier} (see Calibration → Output precision)")
    if visible:
        window.set_visible(True)
    return window, evidence
