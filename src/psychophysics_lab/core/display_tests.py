"""Pure display diagnostic plans; no GUI imports or hardware access."""
from dataclasses import asdict, dataclass
import math
from ..stimuli.geometry import resolve_white_bar

TESTS = (("Size / ruler bar", "size"), ("Position / ruler bar", "position"),
         ("Spatial sine grating", "spatial"), ("Luminance / grayscale measurement patch", "luminance_patch"),
         ("Binary flicker (constant frame cycle)", "temporal_binary"),
         ("Frame-sampled sine modulation", "temporal_sine"))

def finite(value, name, *, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number.")
    number = float(value)
    if not math.isfinite(number) or positive and number <= 0:
        raise ValueError(f"{name} must be {'positive and ' if positive else ''}finite.")
    return number

def temporal_plan(refresh_hz, frequency_hz, mode):
    rate = finite(refresh_hz, "Refresh rate", positive=True)
    freq = finite(frequency_hz, "Temporal frequency", positive=True)
    if freq > rate / 2:
        raise ValueError("Temporal frequency exceeds the frame sampling Nyquist limit (refresh / 2).")
    if mode == "temporal_binary":
        half = max(1, round(rate / (2 * freq)))
        realised = rate / (2 * half)
        exact = math.isclose(realised, freq, rel_tol=1e-8)
        return {"mode": mode, "requested_hz": freq, "nominal_refresh_hz": rate,
                "on_frames": half, "off_frames": half, "realised_hz": realised,
                "error_hz": realised - freq, "exactly_representable": exact,
                "explanation": "Constant 50% duty cycle; f = refresh / (on frames + off frames). Requested frequency is rounded to a whole-frame half-cycle."}
    if mode == "temporal_sine":
        if math.isclose(freq, rate / 2):
            raise ValueError("Sine modulation must be below refresh / 2; the Nyquist boundary is phase dependent.")
        return {"mode": mode, "requested_hz": freq, "nominal_refresh_hz": rate,
                "realised_hz": freq, "phase_step_rad": 2 * math.pi * freq / rate,
                "explanation": "Phase is sampled by frame index. This is not a constant binary on/off cycle. Dropped frames change physical timing; photodiode verification is required."}
    raise ValueError("Unknown temporal diagnostic mode.")

def frame_command(plan, frame):
    if plan["mode"] == "temporal_binary":
        return 1.0 if frame % (plan["on_frames"] + plan["off_frames"]) < plan["on_frames"] else 0.0
    return 0.5 + 0.5 * math.cos(frame * plan["phase_step_rad"])

def resolve_test(profile, request, resolution):
    profile.validate()
    if request.test_kind not in dict((key, label) for label, key in TESTS):
        raise ValueError("Unknown display test.")
    bar = resolve_white_bar(profile=profile, resolution_px=resolution, mode=request.mode,
                            value=request.value, orientation=request.orientation, thickness_mm=request.thickness_mm)
    width, height = resolution
    x, y = finite(request.x_position, "X position"), finite(request.y_position, "Y position")
    if request.position_units == "degrees":
        if abs(x) >= 90 or abs(y) >= 90:
            raise ValueError("Angular position must be within -90 to 90 degrees.")
        x = profile.viewing_distance_m * math.tan(math.radians(x)) * 1000
        y = profile.viewing_distance_m * math.tan(math.radians(y)) * 1000
    elif request.position_units != "mm":
        raise ValueError("Position units must be mm or degrees.")
    cx = round(width / 2 + x / (profile.physical_width_m * 1000) * width)
    cy = round(height / 2 + y / (profile.physical_height_m * 1000) * height)
    bw, bh = (bar.length_px, bar.thickness_px) if bar.orientation == "horizontal" else (bar.thickness_px, bar.length_px)
    left, bottom, right, top = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
    if left < 0 or bottom < 0 or right > width or top > height:
        raise ValueError("The positioned stimulus extends beyond the selected display.")
    distance = profile.viewing_distance_m
    length_extent = profile.physical_width_m if bar.orientation == "horizontal" else profile.physical_height_m
    axis_size = width if bar.orientation == "horizontal" else height
    realised_position_mm = [(cx - width/2)*profile.physical_width_m/width*1000,
                            (cy - height/2)*profile.physical_height_m/height*1000]
    centre_mm = realised_position_mm[0 if bar.orientation == "horizontal" else 1]
    low_angle = math.degrees(math.atan((centre_mm / 1000 - bar.realised_length_mm / 2000) / distance))
    high_angle = math.degrees(math.atan((centre_mm / 1000 + bar.realised_length_mm / 2000) / distance))
    plan = {"test_kind": request.test_kind, "bar": bar.to_dict(), "rectangle_px": [left, bottom, right, top],
            "centre_px": [cx, cy], "position_mm": [x, y], "realised_position_mm": realised_position_mm,
            "off_axis_extent_deg": high_angle - low_angle,
            "size_semantics": "Size degrees specifies a centred-equivalent physical extent; off-axis extent uses atan of the realised endpoints.",
            "geometry_verified": False, "photometric_verified": False, "photon_timing_verified": False}
    if request.test_kind == "spatial":
        freq = finite(request.spatial_cpd, "Spatial frequency", positive=True)
        step_m = length_extent / axis_size
        # Most widely separated adjacent angular samples occur nearest the optical centre.
        maximum_step_deg = math.degrees(2 * math.atan(step_m / (2 * distance)))
        minimum_pixels_per_cycle = 1 / (freq * maximum_step_deg)
        if minimum_pixels_per_cycle < 2:
            raise ValueError("Spatial frequency exceeds the selected display's pixel sampling Nyquist limit.")
        plan["spatial"] = {"requested_cycles_per_degree": freq, "minimum_pixels_per_cycle": minimum_pixels_per_cycle,
                           "cycles_across_patch": freq * (high_angle - low_angle),
                           "phase_semantics": "Sine phase uses angular position atan((pixel-centre - screen-centre) * metres-per-pixel / distance), not a linear degrees-per-pixel approximation."}
    if request.test_kind == "luminance_patch":
        command = finite(request.digital_command, "Photometry digital command")
        if not 0 <= command <= 1:
            raise ValueError("Photometry digital command must be within [0, 1].")
        plan["luminance_patch"] = {
            "digital_command": command,
            "patch_rgb": [command, command, command],
            "patch_location": "centred rectangle on black surround",
            "measurement": "requires a real photometer (cd/m²), not obtained by PsyCoLab",
            "photometry_verified": False,
        }
    if request.test_kind.startswith("temporal_"):
        plan["temporal"] = temporal_plan(profile.refresh_rate_hz, request.temporal_hz, request.test_kind)
    # 0 means the researcher ends the display test with ESC or ENTER.
    # Any positive finite duration is also permitted for scripted acceptance.
    duration = finite(request.duration_s, "Duration")
    if duration < 0:
        raise ValueError("Duration must be nonnegative (0 = until ESC/ENTER).")
    plan["duration_s"] = duration
    plan["termination"] = ("manual_escape_or_enter" if duration == 0
                           else "manual_or_timeout")

    return bar, plan

def diagnostic_timeout_reached(duration_s, elapsed_s):
    """Never auto-close a manual diagnostic (duration 0); only Esc/Enter ends it."""
    return duration_s > 0 and elapsed_s >= duration_s


def interval_summary(timestamps, refresh_hz):
    import statistics
    intervals = [b-a for a,b in zip(timestamps,timestamps[1:])]
    if not intervals:
        return {"frames": len(timestamps), "software_timing_verified": False}
    expected = 1 / refresh_hz
    return {"frames": len(timestamps), "intervals_s": intervals,
            "median_interval_s": statistics.median(intervals), "maximum_interval_s": max(intervals),
            "suspected_missed_refreshes": sum(max(0, round(dt/expected)-1) for dt in intervals if dt > 1.5*expected),
            "measurement": "perf_counter after window.flip; software observation, not photon onset", "software_timing_verified": False}
