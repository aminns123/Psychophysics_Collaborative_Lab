"""Fullscreen display-geometry diagnostic.

This is framework/display infrastructure, not a participant experiment.  It
writes diagnostic records under the external PsyCoLab workspace and never under
a participant acquisition run.
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
from ..paths import resolve_data_root
from ..stimuli.geometry import geometry_reference_table, resolve_white_bar


@dataclass(frozen=True)
class GeometryCheckRequest:
    monitor_profile_id: str
    mode: str
    value: float
    orientation: str = "horizontal"
    thickness_mm: float = 5.0
    data_root: str | None = None


@dataclass(frozen=True)
class GeometryCheckArtifacts:
    report_file: Path
    output_directory: Path
    resolution_px: tuple[int, int]
    intended_length_mm: float
    realised_length_mm: float
    realised_visual_angle_deg: float


def _allocate_output(data_root: Path, monitor_profile_id: str) -> Path:
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
    """Open Pyglet only after Textual has exited and return resolved geometry."""
    import pyglet
    from pyglet import gl

    window = pyglet.window.Window(fullscreen=True, caption="PsyCoLab Display Geometry Check")
    resolution = (int(window.width), int(window.height))
    bar = resolve_white_bar(
        profile=profile,
        resolution_px=resolution,
        mode=request.mode,
        value=request.value,
        orientation=request.orientation,
        thickness_mm=request.thickness_mm,
    )

    gl.glClearColor(0.0, 0.0, 0.0, 1.0)
    label = pyglet.text.Label(
        (
            "PsyCoLab display geometry check\n"
            f"Expected physical length: {bar.intended_length_mm:.2f} mm\n"
            f"Rendered: {bar.length_px} px = {bar.realised_length_mm:.2f} mm\n"
            f"Realised visual angle: {bar.realised_visual_angle_deg:.4f} deg\n"
            "Measure the white bar with a ruler.  Press Esc or Enter to finish."
        ),
        x=24,
        y=window.height - 24,
        anchor_x="left",
        anchor_y="top",
        multiline=True,
        width=max(300, window.width - 48),
        color=(255, 255, 255, 255),
    )

    @window.event
    def on_draw():
        window.clear()
        cx = window.width / 2.0
        cy = window.height / 2.0
        if bar.orientation == "horizontal":
            left = cx - bar.length_px / 2.0
            right = cx + bar.length_px / 2.0
            bottom = cy - bar.thickness_px / 2.0
            top = cy + bar.thickness_px / 2.0
        else:
            left = cx - bar.thickness_px / 2.0
            right = cx + bar.thickness_px / 2.0
            bottom = cy - bar.length_px / 2.0
            top = cy + bar.length_px / 2.0
        gl.glColor3f(1.0, 1.0, 1.0)
        pyglet.graphics.draw(
            4,
            gl.GL_QUADS,
            ("v2f", (left, bottom, right, bottom, right, top, left, top)),
        )
        label.draw()

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol in {pyglet.window.key.ESCAPE, pyglet.window.key.ENTER}:
            window.close()
            return True
        return None

    pyglet.app.run()
    return resolution, bar


def run_geometry_check(
    request: GeometryCheckRequest,
    *,
    repo_root: Path,
    data_root: Path | None = None,
) -> GeometryCheckArtifacts:
    """Run one fullscreen ruler check and save its diagnostic record."""
    selected_root = data_root or (Path(request.data_root).expanduser() if request.data_root else None)
    if selected_root is None:
        raise ValueError("A data workspace is required for the geometry diagnostic.")
    external_root = resolve_data_root(selected_root, repo_root)
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
        resolution, bar = _draw_fullscreen(profile, request)
        payload: dict[str, Any] = {
            "schema_version": 1,
            "diagnostic": "display_geometry_white_bar",
            "diagnostic_uuid": diagnostic_uuid,
            "status": "completed",
            "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "monitor_profile": profile.to_dict(),
            "actual_fullscreen_resolution_px": list(resolution),
            "request": asdict(request) | {"data_root": None},
            "resolved_bar": bar.to_dict(),
            "reference_table_horizontal": geometry_reference_table(profile, resolution),
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
    except Exception as exc:
        atomic_write_json(
            report,
            {
                "schema_version": 1,
                "diagnostic": "display_geometry_white_bar",
                "diagnostic_uuid": diagnostic_uuid,
                "status": "error",
                "started_utc": started,
                "finished_utc": datetime.now(timezone.utc).isoformat(),
                "monitor_profile": profile.to_dict(),
                "request": asdict(request) | {"data_root": None},
                "error": repr(exc),
            },
        )
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
    measured = float(measured_length_mm)
    if measured <= 0:
        raise ValueError("Measured ruler length must be positive.")
    error = measured - intended
    payload["measurement"] = {
        "measured_length_mm": measured,
        "error_mm": error,
        "error_percent": (error / intended) * 100.0,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(report, payload)
    return payload
