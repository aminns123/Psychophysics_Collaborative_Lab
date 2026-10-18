"""Fullscreen display-geometry diagnostic.

This is framework/display infrastructure, not a participant experiment.  It
writes diagnostic records under machine-local configuration, separately from
participant acquisition runs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config.monitor import load_monitor_profiles
from ..data.session import atomic_write_json
from ..config.local import config_root, content_hash
from ..data.identifiers import validate_path_component
from ..data.locking import file_lock
from .display import select_screen
from .display_tests import resolve_test, frame_command, interval_summary, finite, diagnostic_timeout_reached
from ..stimuli.geometry import geometry_reference_table, physical_length_for_visual_angle


@dataclass(frozen=True)
class GeometryCheckRequest:
    monitor_profile_id: str
    mode: str
    value: float
    orientation: str = "horizontal"
    thickness_mm: float = 5.0
    data_root: str | None = None
    test_kind: str = "size"
    x_position: float = 0.0
    y_position: float = 0.0
    position_units: str = "mm"
    spatial_cpd: float = 1.0
    temporal_hz: float = 7.5
    duration_s: float = 0.0
    digital_command: float = 0.5


@dataclass(frozen=True)
class GeometryCheckArtifacts:
    report_file: Path
    output_directory: Path
    resolution_px: tuple[int, int]
    intended_length_mm: float
    realised_length_mm: float
    realised_visual_angle_deg: float


def _allocate_output(data_root: Path, monitor_profile_id: str) -> Path:
    validate_path_component(monitor_profile_id, label="monitor profile")
    date = datetime.now().astimezone().strftime("%Y-%m-%d")
    base = data_root / "diagnostics" / "display_geometry" / monitor_profile_id / date
    base.mkdir(parents=True, exist_ok=True)
    for index in range(1, 10000):
        path = base / f"check_{index:03d}"
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise RuntimeError("Could not allocate a display-geometry diagnostic folder.")


def _draw_fullscreen(profile, request: GeometryCheckRequest):
    """Selected-screen, vsynced diagnostic; software timing is not a photodiode."""
    import math
    import time
    from collections import deque
    import pyglet
    from pyglet import gl
    screen, identity = select_screen(profile)
    # Unlimited manual sessions must not retain one timestamp per frame forever.
    # Keep a bounded recent window for timing diagnostics and count all flips.
    timestamps = deque(maxlen=6000)
    class DiagnosticWindow(pyglet.window.Window):
        frame_index = 0
        def flip(self):
            super().flip()
            timestamps.append(time.perf_counter())
            self.frame_index += 1
    from .output_precision import create_output_window
    window, precision = create_output_window(screen, window_factory=DiagnosticWindow, fullscreen=True, vsync=True, caption="PsyCoLab Display Test")
    termination = "window_closed"
    def invalidate(dt):
        nonlocal termination
        if diagnostic_timeout_reached(request.duration_s, time.perf_counter() - start):
            termination = "timeout"
            window.close()
        else:
            window.invalid = True
    primary_error = None
    try:
        resolution = (int(window.width), int(window.height))
        if profile.expected_resolution_px and resolution != profile.expected_resolution_px:
            raise ValueError("Actual fullscreen resolution differs from the selected profile.")
        bar, plan = resolve_test(profile, request, resolution)
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        left, bottom, right, top = plan["rectangle_px"]
        start = time.perf_counter()
        label = pyglet.text.Label(
            f"PsyCoLab {request.test_kind}: {bar.realised_length_mm:.2f} mm / {bar.length_px} px. Esc or Enter to finish.\n"
            + (f"Requested {request.temporal_hz:g} Hz, planned {plan['temporal']['realised_hz']:.6g} Hz at {profile.refresh_rate_hz:g} Hz. " if "temporal" in plan else "")
            + "Diagnostic only; laboratory validation required.",
            x=24,y=window.height-24,anchor_y="top", multiline=True,width=max(100,window.width-48))
        # Precompute spatial pixels once; phase follows exact angular pixel centres.
        spatial = []
        if request.test_kind == "spatial":
            horizontal = request.orientation == "horizontal"
            lo, hi = (left,right) if horizontal else (bottom,top)
            extent = profile.physical_width_m if horizontal else profile.physical_height_m
            axis = resolution[0] if horizontal else resolution[1]
            for pixel in range(math.floor(lo), math.ceil(hi)):
                angle = math.degrees(math.atan(((pixel+.5)-axis/2)*extent/axis/profile.viewing_distance_m))
                command = .5+.5*math.cos(2*math.pi*request.spatial_cpd*angle)
                spatial.append((max(lo,pixel),min(hi,pixel+1),command))
        def rectangle(l,b,r,t,command):
            # Avoid pyglet 1.5's deprecated graphics.draw sequence slicing
            # on some Windows/Python/OpenGL combinations. Use compatibility
            # OpenGL calls with scalar vertex coordinates instead.
            gl.glColor3f(command, command, command)
            gl.glBegin(gl.GL_QUADS)
            gl.glVertex2f(l, b)
            gl.glVertex2f(r, b)
            gl.glVertex2f(r, t)
            gl.glVertex2f(l, t)
            gl.glEnd()
        @window.event
        def on_draw():
            window.clear()
            if spatial:
                for lo, hi, command in spatial:
                    if request.orientation == "horizontal": rectangle(lo,bottom,hi,top,command)
                    else: rectangle(left,lo,right,hi,command)
            else:
                command = (
                    frame_command(plan["temporal"],window.frame_index) if "temporal" in plan
                    else plan["luminance_patch"]["digital_command"] if "luminance_patch" in plan
                    else 1.0
                )
                rectangle(left,bottom,right,top,command)
            label.draw()
        @window.event
        def on_key_press(symbol, modifiers):
            nonlocal termination
            if symbol in {pyglet.window.key.ESCAPE,pyglet.window.key.ENTER}:
                termination = "escape" if symbol == pyglet.window.key.ESCAPE else "enter"
                window.close()
                return True
        pyglet.clock.schedule_interval(invalidate,1/profile.refresh_rate_hz)
        pyglet.app.run()
        if not timestamps:
            raise ValueError("Display test ended before any software flip was observed; rerun the diagnostic.")
        plan["termination_reason"] = termination
        plan["display_identity"] = identity
        plan["output_precision"] = precision
        plan["frame_timing"] = interval_summary(timestamps,profile.refresh_rate_hz)
        plan["frame_timing"]["total_flips"] = window.frame_index
        plan["frame_timing"]["sampled_recent_flips"] = len(timestamps)
        plan["frame_timing"]["sampling_note"] = (
            "Timing intervals cover at most the last 6000 software flips; "
            "not measured photon-onset times."
        )
        return resolution,bar,plan
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors = []
        for operation in (lambda: pyglet.clock.unschedule(invalidate), window.close):
            try:
                operation()
            except Exception as exc:
                cleanup_errors.append(exc)
        if cleanup_errors:
            if primary_error is not None:
                for exc in cleanup_errors:
                    primary_error.add_note(f"Diagnostic cleanup failed: {exc!r}")
            else:
                raise cleanup_errors[0]


def _draw_luminance_session(profile, request, session) -> None:
    """6° centred square; keyboard entry in a dim corner away from the patch.

    Pyglet 1.5 OpenGL is imported lazily after Textual closes. Photometer
    readings are human-entered, NOT sampled or verified by this software.
    Escape closes; Enter saves each reading. Every saved observation is
    flushed to a local session file immediately for crash recovery.
    """
    import pyglet
    from pyglet import gl
    from .display import select_screen
    from .luminance_session import stepped_command, summarise_readings
    from .presentation import FloatingTexture
    import numpy as np

    screen, _ = select_screen(profile)
    from .output_precision import create_output_window, format_summary
    window, precision = create_output_window(
        screen, fullscreen=True, vsync=True,
        caption="PsyCoLab — Photometer Measurement (Esc to finish)"
    )
    # Force an explicitly black surround; OpenGL's default clear colour
    # is not a laboratory brightness calibration or a reliable UI setting.
    sequence = session.plan.get("commands")
    sequence_index = 0
    current = session.plan.get("starting_command", 1.0)
    entry = ""
    feedback = "Type measured cd/m²; Enter saves. Left dimmer / Right brighter. Esc finishes."
    patch_texture = None
    patch_texture_command = None
    try:
        precision["window_scope"] = "fullscreen photometer measurement"
        precision["photometer_patch_path"] = "GL_LUMINANCE32F_ARB floating texture, nearest sampling; same upload/sampling path as scientific stimuli"
        if hasattr(session, "set_output"):
            session.set_output(precision)
        else:
            session.session["output_precision"] = precision
            session._persist()
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        resolution = (int(window.width), int(window.height))
        if profile.expected_resolution_px and resolution != profile.expected_resolution_px:
            raise ValueError("Actual fullscreen pixel resolution changed since calibration; rebind the monitor.")
        patch_m = session.plan["square_side_m"]
        px_w = patch_m / profile.physical_width_m * resolution[0]
        px_h = patch_m / profile.physical_height_m * resolution[1]
        if px_w > resolution[0] or px_h > resolution[1]:
            raise ValueError("6° photometer square would exceed the physical display.")
        x1 = (resolution[0] - px_w)/2
        y1 = (resolution[1] - px_h)/2
        x2, y2 = x1 + px_w, y1 + px_h
        label = pyglet.text.Label(
            "", font_size=10, color=(100, 100, 100, 255),
            x=resolution[0] - 12, y=10,
            anchor_x="right", anchor_y="bottom",
            multiline=True, width=min(640, max(200, resolution[0] - 24)),
        )
        def update_label():
            rows = summarise_readings(session.session["readings"])
            selected = next((row for row in rows if row["screen_intensity"] == current), None)
            sample_status = (
                f"n={selected['n']}, mean={selected['luminance_cdm2']:.5g} cd/m²"
                if selected else "n=0, no measurements"
            )
            label.text = (
                f"Command: {current:.10g}  |  Photometer cd/m²: {entry or '_'}\n"
                f"{sample_status}  |  {feedback}\n" +
                (f"Level {sequence_index+1}/{len(sequence)}; aim for 5 readings per command. " if sequence else "") +
                "Left/Right: command  |  Enter: save reading  |  Esc: end\n" +
                format_summary(precision)
            )

        def draw_patch():
            nonlocal patch_texture, patch_texture_command
            if patch_texture is None or patch_texture_command != current:
                # A single float texel is constant across the 6° aperture.
                # Reuse the scientific FloatingTexture upload path; do not
                # silently convert photometer commands to 8-bit glColor values.
                next_texture = FloatingTexture(np.array([[current]], dtype=np.float32))
                previous_texture = patch_texture
                patch_texture = next_texture
                patch_texture_command = current
                if previous_texture is not None:
                    previous_texture.delete()
            patch_texture.blit(x1, y1, width=px_w, height=px_h)

        @window.event
        def on_draw():
            window.clear()
            draw_patch()
            update_label()
            label.draw()

        @window.event
        def on_text(text):
            nonlocal entry, feedback
            if text and all(char in "0123456789." for char in text) and len(entry) < 18:
                entry += text
                feedback = "Enter saves a reading (repeat at same intensity as needed)."
                window.invalid = True
                return True

        @window.event
        def on_key_press(symbol, modifiers):
            nonlocal current, entry, feedback, sequence_index
            k = pyglet.window.key
            if symbol == k.ESCAPE:
                if entry:
                    feedback = "Unsaved reading: Enter saves, or Backspace clears before Esc finishes."
                    window.invalid = True
                    return True
                window.close()
                return True
            if symbol == k.BACKSPACE:
                entry = entry[:-1]
                feedback = "Reading edited; press Enter to save."
            elif symbol in (k.LEFT, k.RIGHT):
                if entry:
                    feedback = "Unsaved reading: Enter to save or Backspace to clear before changing command."
                else:
                    if sequence:
                        sequence_index = max(0, min(len(sequence)-1, sequence_index + (-1 if symbol == k.LEFT else 1)))
                        current = sequence[sequence_index]
                    else:
                        current = stepped_command(
                            current, -1 if symbol == k.LEFT else 1,
                            session.plan["minimum_command"], session.plan["step"]
                        )
                    feedback = "Intensity changed; measure and type a reading in cd/m²."
            elif symbol in (k.ENTER, getattr(k, "NUM_ENTER", k.ENTER)):
                if not entry:
                    feedback = "Type a measured luminance value in cd/m² before Enter."
                else:
                    try:
                        session.record(current, entry)
                    except (ValueError, OSError, RuntimeError) as exc:
                        feedback = f"Reading NOT saved: {exc}"
                    else:
                        feedback = session.export_warning or f"Reading saved to local calibration session (command {current:.4f})."
                        entry = ""
            else:
                return
            window.invalid = True
            return True

        pyglet.app.run()
    finally:
        try:
            if patch_texture is not None:
                patch_texture.delete()
        finally:
            window.close()


def run_geometry_check(
    request: GeometryCheckRequest,
    *,
    repo_root: Path,
    data_root: Path | None = None,
) -> GeometryCheckArtifacts:
    """Run one fullscreen ruler check and save its diagnostic record."""
    # The legacy data_root argument is retained for callers, but diagnostics now
    # belong to this machine's configuration root, never to acquisition data.
    external_root = config_root(repo_root, data_root or (Path(request.data_root) if request.data_root else None))
    external_root.mkdir(parents=True, exist_ok=True)

    profiles = load_monitor_profiles(repo_root)
    try:
        profile = profiles[request.monitor_profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown monitor profile: {request.monitor_profile_id}") from exc

    output = _allocate_output(external_root, profile.id)
    report = output / "geometry_check.json"
    started = datetime.now(timezone.utc).isoformat()
    diagnostic_uuid = str(uuid4())

    try:
        resolution, bar, plan = _draw_fullscreen(profile, request)
        payload: dict[str, Any] = {
            "schema_version": 1,
            "diagnostic": "display_test",
            "diagnostic_uuid": diagnostic_uuid,
            "status": "completed",
            "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "monitor_profile": profile.to_dict(),
            "monitor_profile_sha256": content_hash(profile.to_dict()),
            "actual_fullscreen_resolution_px": list(resolution),
            "request": asdict(request) | {"data_root": None},
            "resolved_bar": bar.to_dict(),
            "resolved_test": plan,
            "reference_table_horizontal": geometry_reference_table(
                profile, resolution,
                angles_deg=tuple(angle for angle in (0.5, 1., 2., 5., 10.)
                                 if physical_length_for_visual_angle(angle, profile.viewing_distance_m) <= profile.physical_width_m)),
            "measurement": {
                "measured_length_mm": None,
                "error_mm": None,
                "error_percent": None,
                "recorded_utc": None,
            },
            "interpretation": (
                "This display diagnostic records the requested display command, selected "
                "monitor profile, fullscreen resolution and derived geometry. A grayscale "
                "patch is NOT a luminance measurement: enter the real cd/m² obtained from "
                "a photometer separately. The test does not certify geometry, photometry, "
                "photon timing or scientific contrast by itself."
            ),
        }
        atomic_write_json(report, payload)
        update_active_diagnostic(external_root,payload)
    except BaseException as exc:
        try:
            atomic_write_json(
                report,
                {
                    "schema_version": 1,
                    "diagnostic": "display_test",
                    "diagnostic_uuid": diagnostic_uuid,
                    "status": "error",
                    "started_utc": started,
                    "finished_utc": datetime.now(timezone.utc).isoformat(),
                    "monitor_profile": profile.to_dict(),
                    "request": asdict(request) | {"data_root": None},
                    "error": repr(exc),
                },
            )
        except Exception as record_error:
            exc.add_note(f"Could not save diagnostic failure: {record_error!r}")
        raise

    return GeometryCheckArtifacts(
        report_file=report,
        output_directory=output,
        resolution_px=resolution,
        intended_length_mm=bar.intended_length_mm,
        realised_length_mm=bar.realised_length_mm,
        realised_visual_angle_deg=bar.realised_visual_angle_deg,
    )


def latest_geometry_report(data_root: Path, monitor_profile_id: str | None = None, *, ruler_only: bool = False) -> Path | None:
    base = data_root / "diagnostics" / "display_geometry"
    if monitor_profile_id:
        base = base / monitor_profile_id
    if not base.exists():
        return None
    reports = []
    for path in base.rglob("geometry_check.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            if ruler_only and payload.get("request", {}).get("test_kind", "size") not in {"size", "position"}:
                continue
            reports.append(path)
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return max(reports, key=lambda path: path.stat().st_mtime_ns) if reports else None


def record_geometry_measurement(
    *,
    data_root: Path,
    report_file: Path,
    measured_length_mm: float,
    profile=None,
) -> dict[str, Any]:
    """Add a ruler measurement to a diagnostic report, never to acquisition data."""
    root = data_root.resolve()
    diagnostics_root = (root / "diagnostics" / "display_geometry").resolve()
    report = report_file.resolve()
    if not report.is_relative_to(diagnostics_root):
        raise ValueError("Geometry report is not inside this workspace's diagnostics area.")
    payload = json.loads(report.read_text(encoding="utf-8"))
    from ..config.readiness import diagnostic_matches_profile
    if payload.get("request", {}).get("test_kind", "size") not in {"size", "position"}:
        raise ValueError(
            "A ruler measurement can only be recorded for a Size or Position "
            "bar test. Run a ruler diagnostic first; do not record photometer "
            "values or grating measurements in this field."
        )
    if payload.get("status") != "completed":
        raise ValueError("Only a completed ruler presentation can receive a measurement.")
    if profile is not None and not diagnostic_matches_profile(payload, profile):
        raise ValueError("Ruler evidence is stale or belongs to another physical display setup. Run a fresh test.")
    intended = float(payload["resolved_bar"]["intended_length_mm"])
    measured = finite(measured_length_mm, "Measured ruler length", positive=True)
    error = measured - intended
    payload["measurement"] = {
        "measured_length_mm": measured,
        "error_mm": error,
        "error_percent": (error / intended) * 100.0,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
    }
    with file_lock(report.parent / "measurement.lock"):
        latest = json.loads(report.read_text(encoding="utf-8"))
        if latest.get("status") != "completed" or (profile is not None and not diagnostic_matches_profile(latest, profile)):
            raise ValueError("Ruler evidence changed while recording; reload before saving.")
        latest.setdefault("measurement_history", []).append(dict(latest.get("measurement", {})))
        latest["measurement"] = payload["measurement"]
        atomic_write_json(report, latest)
    update_active_diagnostic(root,latest)
    return latest


def update_active_diagnostic(root,payload):
    from ..config.monitor import _profile_from_dict
    from ..config.calibration_dataset import active_directory
    profile=_profile_from_dict(payload['monitor_profile'])
    kind=payload.get('request',{}).get('test_kind','size')
    category='timing' if kind.startswith('temporal_') else 'spatial' if kind=='spatial' else 'luminance_diagnostic' if kind=='luminance_patch' else 'geometry'
    path=active_directory(root,profile)/(category+'.json')
    with file_lock(root/'profiles.lock'):
        current=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'profile_revision':profile.revision}
        current.setdefault('diagnostics',{})[kind]=payload
        atomic_write_json(path,current)
