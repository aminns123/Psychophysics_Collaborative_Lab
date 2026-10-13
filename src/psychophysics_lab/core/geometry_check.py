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
    window = DiagnosticWindow(fullscreen=True, screen=screen, vsync=True, caption="PsyCoLab Display Test")
    def invalidate(dt):
        if diagnostic_timeout_reached(request.duration_s, time.perf_counter() - start):
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
            gl.glColor3f(command,command,command)
            pyglet.graphics.draw(4,gl.GL_QUADS,("v2f",(l,b,r,b,r,t,l,t)))
        @window.event
        def on_draw():
            window.clear()
            if spatial:
                for lo, hi, command in spatial:
                    if request.orientation == "horizontal": rectangle(lo,bottom,hi,top,command)
                    else: rectangle(left,lo,right,hi,command)
            else:
                command = frame_command(plan["temporal"],window.frame_index) if "temporal" in plan else 1.0
                rectangle(left,bottom,right,top,command)
            label.draw()
        @window.event
        def on_key_press(symbol, modifiers):
            if symbol in {pyglet.window.key.ESCAPE,pyglet.window.key.ENTER}:
                window.close()
                return True
        pyglet.clock.schedule_interval(invalidate,1/profile.refresh_rate_hz)
        pyglet.app.run()
        plan["display_identity"] = identity
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
                "This ruler check validates the relationship between the selected monitor "
                "profile, actual fullscreen resolution and physical geometry. It does not "
                "by itself certify photometric calibration, temporal accuracy or stimulus "
                "contrast."
            ),
        }
        atomic_write_json(report, payload)
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


def latest_geometry_report(data_root: Path, monitor_profile_id: str | None = None) -> Path | None:
    base = data_root / "diagnostics" / "display_geometry"
    if monitor_profile_id:
        base = base / monitor_profile_id
    if not base.exists():
        return None
    reports = [path for path in base.rglob("geometry_check.json") if path.is_file()]
    return max(reports, key=lambda path: path.stat().st_mtime_ns) if reports else None


def record_geometry_measurement(
    *,
    data_root: Path,
    report_file: Path,
    measured_length_mm: float,
) -> dict[str, Any]:
    """Add a ruler measurement to a diagnostic report, never to acquisition data."""
    root = data_root.resolve()
    diagnostics_root = (root / "diagnostics" / "display_geometry").resolve()
    report = report_file.resolve()
    if not report.is_relative_to(diagnostics_root):
        raise ValueError("Geometry report is not inside this workspace's diagnostics area.")
    payload = json.loads(report.read_text(encoding="utf-8"))
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
        latest.setdefault("measurement_history", []).append(dict(latest.get("measurement", {})))
        latest["measurement"] = payload["measurement"]
        atomic_write_json(report, latest)
    return latest
