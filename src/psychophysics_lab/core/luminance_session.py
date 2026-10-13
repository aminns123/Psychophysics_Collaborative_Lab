"""Operator-entered photometer measurements, kept in machine-local calibration files.

This is NOT a synthetic observer, participant experiment, photometer interface,
or declaration of luminance calibration. Every Enter stores one actual operator
observation; repeats are retained and averaged only in the export.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
import statistics
from uuid import uuid4

from ..config.calibration_templates import FORMAT, VERSION, template_identity
from ..config.local import config_root, content_hash
from ..config.monitor import load_monitor_profiles
from ..data.identifiers import validate_path_component
from ..data.locking import file_lock
from ..data.session import atomic_write_json
from .display_tests import finite


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class LuminanceSessionRequest:
    monitor_profile_id: str
    background_command: float = 0.0
    command_step: float = 0.05
    patch_degrees: float = 6.0
    data_root: str | None = None


@dataclass(frozen=True)
class LuminanceSessionArtifacts:
    session_file: Path
    pilot_json_file: Path
    readings_count: int
    measured_commands: int
    status: str
    export_warning: str | None = None


def validate_luminance_session(request: LuminanceSessionRequest, profile) -> dict:
    """Return a physical plan; never conflate a normalized command with cd/m²."""
    background = finite(request.background_command, "Minimum background command")
    step = finite(request.command_step, "Intensity step", positive=True)
    patch = finite(request.patch_degrees, "Patch visual angle", positive=True)
    if not 0 <= background < 1:
        raise ValueError("Minimum background screen command must lie in [0, 1).")
    if not 0 < step <= 1:
        raise ValueError("Intensity step must be greater than 0 and at most 1.")
    if patch != 6:
        raise ValueError("The luminance measurement square is fixed at 6 degrees.")
    # 6° is a centred square in *visual-angle width and height*, requiring
    # different framebuffer pixel extents for different physical pixel pitches.
    length_m = 2 * profile.viewing_distance_m * math.tan(math.radians(patch / 2))
    if length_m > profile.physical_width_m or length_m > profile.physical_height_m:
        raise ValueError("6-degree measurement square will not fit on this monitor at the selected viewing distance.")
    return {
        "minimum_command": background, "starting_command": 1.0, "step": step,
        "patch_degrees": patch, "square_side_m": length_m,
        "surround_command": 0.0,
        "label_placement": "bottom-right outside measurement patch",
        "photometry_verified": False,
    }


def stepped_command(current: float, direction: int, minimum: float, step: float) -> float:
    """Left = decrease toward configured floor; Right = increase toward 1."""
    if direction not in (-1, 1):
        raise ValueError("Direction must be -1 (left) or 1 (right).")
    value = current + step * direction
    return round(max(minimum, min(1.0, value)), 6)


def parse_photometer_reading(raw: str) -> float:
    try:
        reading = float(raw.strip())
    except (ValueError, TypeError) as exc:
        raise ValueError("Enter a real measured luminance number in cd/m².") from exc
    if not math.isfinite(reading) or reading < 0:
        raise ValueError("Measured luminance must be a finite nonnegative number in cd/m².")
    return reading


def summarise_readings(readings: list[dict]) -> list[dict]:
    by_command: dict[float, list[float]] = {}
    for row in readings:
        by_command.setdefault(float(row["screen_intensity"]), []).append(float(row["luminance_cdm2"]))
    summaries = []
    for command, samples in sorted(by_command.items()):
        summaries.append({
            "screen_intensity": command,
            "luminance_cdm2": statistics.fmean(samples),
            "readings_cdm2": list(samples),
            "n": len(samples),
            "sample_sd_cdm2": statistics.stdev(samples) if len(samples) > 1 else None,
        })
    return summaries


class LocalLuminanceSession:
    """Crash-resistant local measurement session; no writes to participant data."""
    def __init__(self, root: Path, profile, request: LuminanceSessionRequest):
        self.root = root.resolve()
        self.profile = profile
        self.request = request
        self.plan = validate_luminance_session(request, profile)
        profile_id = validate_path_component(profile.id, label="monitor profile")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        self.folder = self.root / "calibration_sessions" / profile_id / (
            timestamp + "_" + uuid4().hex[:8]
        )
        self.folder.mkdir(parents=True, exist_ok=False)
        self.session_file = self.folder / "session.json"
        self.pilot_json_file = self.folder / "pilot_luminance.json"
        self.session = {
            "schema_version": 1,
            "kind": "physical_luminance_measurement_session",
            "session_uuid": str(uuid4()), "status": "in_progress",
            "started_utc": now_utc(), "finished_utc": None,
            "monitor_profile": profile.to_dict(),
            "monitor_profile_sha256": content_hash(profile.to_dict()),
            "request": asdict(request) | {"data_root": None},
            "resolved_test": self.plan,
            "readings": [],
            "measurement_provenance": (
                "Entered by a human operating a photometer; no automated "
                "hardware luminance measurement or physical verification."
            ),
        }
        from ..config.calibration_dataset import load_active,physical_snapshot
        active=load_active(self.root,profile)
        if active['physical_snapshot']!=physical_snapshot(profile):
            raise ValueError('Active measurements belong to an earlier physical configuration. Confirm replacement in the luminance editor first.')
        self.session['readings']=[dict(r) for r in active['observations'] if r.get('source')!='legacy_summary_only']
        self.session['retained_legacy_summaries']=bool(any(r.get('source')=='legacy_summary_only' for r in active['observations']))
        self.session['continued_active_version']=active['version']
        self._persist()

    def _pilot(self) -> dict:
        profile_id, revision = template_identity(self.profile)
        rows = summarise_readings(self.session["readings"])
        for row in rows:
            observations=[r for r in self.session['readings'] if float(r['screen_intensity'])==row['screen_intensity']]
            row['observation_ids']=[r.get('observation_id') or content_hash({'session':self.session['session_uuid'],'index':i,'reading':r}) for i,r in enumerate(observations)]
            row['reading_data_kinds']=[r.get('data_kind','unspecified') for r in observations]
            row['reading_recorded_utc']=[r.get('recorded_utc') for r in observations]
        if not rows:
            rows = [
                {"screen_intensity": command, "luminance_cdm2": None}
                for command in sorted(set((self.plan["minimum_command"], 1.0)))
            ]
        return {
            "format": FORMAT, "schema_version": VERSION,
            "monitor_profile_id": profile_id,
            "based_on_revision": revision,
            "photometer_model_and_method": "REPLACE_WITH_REAL_METER_AND_MEASUREMENT_METHOD",
            "measurement_date": datetime.now(timezone.utc).date().isoformat(),
            "notes": (
                "REPLACE: instrument, geometry, warm-up, ambient, display settings, "
                "repeat uncertainty and any deviations from measurement protocol."
            ),
            "measurements": rows,
            "data_kind": "synthetic" if any(r.get('data_kind')=='synthetic' for r in self.session['readings']) else "unspecified",
            "source_luminance_session_uuid": self.session["session_uuid"],
            "source_session_file": str(self.session_file),
            "instructions": (
                "Repeated readings are preserved under readings_cdm2 and in "
                "session.json. luminance_cdm2 is their arithmetic mean. "
                "Fill in real photometer model/method and notes before Import. "
                "At least two distinct commands are required. This is an "
                "UNVERIFIED draft, not a calibrated monitor certificate."
            ),
        }

    def _persist(self) -> None:
        self.raw_persisted = False
        with file_lock(self.folder / ".measurement.lock"):
            atomic_write_json(self.session_file, self.session)
            self.raw_persisted = True
            # Raw observations are authoritative. An export failure must not
            # roll back a reading already durably saved to session.json.
            self.export_warning = None
            try:
                atomic_write_json(self.pilot_json_file, self._pilot())
            except Exception as exc:
                self.export_warning = f"Raw readings saved, but mean JSON export failed: {exc}. Re-export from session.json."
                import warnings
                warnings.warn(self.export_warning, RuntimeWarning, stacklevel=2)

    def record(self, command: float, raw_reading: str) -> dict:
        if self.session["status"] != "in_progress":
            raise ValueError("This measurement session has ended; start a new session.")
        command = finite(command, "Screen intensity command")
        if command < self.plan["minimum_command"] - 1e-8 or command > 1 + 1e-8:
            raise ValueError("Measured command is outside the configured luminance sweep.")
        reading = parse_photometer_reading(raw_reading)
        entry = {
            "screen_intensity": round(command, 6), "luminance_cdm2": reading,
            "recorded_utc": now_utc(), "observation_id":str(uuid4()), "data_kind":"unspecified", "source":"operator_session",
        }
        self.session["readings"].append(entry)
        try:
            self._persist()
        except Exception:
            if not self.raw_persisted:
                self.session["readings"].pop()
            raise
        return entry

    def finish(self) -> LuminanceSessionArtifacts:
        old_status, old_finish = self.session["status"], self.session["finished_utc"]
        self.session["status"] = ("completed" if len(summarise_readings(self.session["readings"])) >= 2 else "incomplete")
        self.session["finished_utc"] = now_utc()
        try:
            self._persist()
        except Exception:
            self.session["status"], self.session["finished_utc"] = old_status, old_finish
            raise
        return LuminanceSessionArtifacts(
            session_file=self.session_file,
            pilot_json_file=self.pilot_json_file,
            readings_count=len(self.session["readings"]),
            measured_commands=len(summarise_readings(self.session["readings"])),
            status=self.session["status"],
            export_warning=self.export_warning,
        )


def recover_luminance_pilot(session_file: Path) -> Path:
    """Rebuild a missing derived pilot from authoritative raw observations.

    Existing editable pilot files are never overwritten. Raw records stay intact.
    """
    import json
    from ..config.monitor import _profile_from_dict
    path = session_file.resolve()
    if path.name != "session.json":
        raise ValueError("Select a luminance session.json raw record.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("kind") != "physical_luminance_measurement_session" or content_hash(raw["monitor_profile"]) != raw.get("monitor_profile_sha256"):
        raise ValueError("Invalid luminance session snapshot.")
    session = LocalLuminanceSession.__new__(LocalLuminanceSession)
    session.profile = _profile_from_dict(raw["monitor_profile"])
    session.session, session.plan = raw, raw["resolved_test"]
    session.session_file = path
    pilot = path.parent / "pilot_luminance.json"
    with file_lock(path.parent / ".measurement.lock"):
        if not pilot.exists():
            atomic_write_json(pilot, session._pilot())
    return pilot


def latest_luminance_pilot(root: Path, profile_id: str) -> Path | None:
    profile_id = validate_path_component(profile_id, label="monitor profile")
    base = root.resolve() / "calibration_sessions" / profile_id
    if not base.is_dir():
        return None
    for folder in sorted(base.iterdir(), reverse=True):
        pilot = folder / "pilot_luminance.json"
        if folder.is_dir() and not folder.is_symlink():
            if pilot.is_file() and not pilot.is_symlink():
                return pilot
            raw = folder / "session.json"
            if raw.is_file() and not raw.is_symlink():
                return recover_luminance_pilot(raw)
    return None


def run_interactive_luminance(
    request: LuminanceSessionRequest, *, repo_root: Path, data_root: Path | None = None
) -> LuminanceSessionArtifacts:
    """Fullscreen Pyglet 1.5 measurement loop. Never run inside Textual."""
    from .geometry_check import _draw_luminance_session
    profiles = load_monitor_profiles(repo_root)
    try:
        profile = profiles[request.monitor_profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown monitor profile: {request.monitor_profile_id}") from exc
    selected_data_root = (data_root if data_root is not None
                          else Path(request.data_root) if request.data_root else None)
    root = config_root(repo_root, selected_data_root)
    session = LocalLuminanceSession(root, profile, request)
    try:
        _draw_luminance_session(profile, request, session)
        return session.finish()
    except BaseException as exc:
        session.session["status"] = "error"
        session.session["finished_utc"] = now_utc()
        session.session["error"] = repr(exc)
        try:
            session._persist()
        except Exception as record_error:
            exc.add_note(f"Could not save interrupted session status: {record_error!r}")
        raise
