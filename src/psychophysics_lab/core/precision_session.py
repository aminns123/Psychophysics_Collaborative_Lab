"""Operator-entered output-precision measurements, separate from gamma mapping.

Reported signal depth, obtained framebuffer and measured differences are three
separate pieces of evidence. No inferred native panel bit depth or auto-pass.
"""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import random
from uuid import uuid4

from ..config.calibration_dataset import physical_snapshot
from ..config.local import config_root, content_hash
from ..data.identifiers import validate_path_component
from ..data.locking import file_lock
from ..data.session import atomic_write_json
from .luminance_session import (LuminanceSessionRequest, now_utc,
    parse_photometer_reading, summarise_readings, validate_luminance_session)
from .output_precision import format_summary


@dataclass(frozen=True)
class PrecisionSessionRequest:
    monitor_profile_id: str
    mode: str = "inspect"
    reference_bits: int = 10
    anchors: tuple[float, ...] = (.1, .5, .9)
    manufacturer_specification: str = ""
    instrument_notes: str = ""
    data_root: str | None = None


def precision_commands(mode, reference_bits=10, anchors=(.1, .5, .9)):
    if mode not in {"inspect", "halving", "fine"}:
        raise ValueError("Choose inspect, halving or fine output precision measurement.")
    if type(reference_bits) is not int or not 1 <= reference_bits <= 24:
        raise ValueError("Reference depth must be an integer from 1 to 24 bits.")
    if mode == "inspect": return []
    if mode == "halving": return [2.0**(-n) for n in range(17)] + [0.0]
    if not anchors or any(isinstance(a, bool) or not isinstance(a, (int, float)) or
                          not math.isfinite(a) or not 0 <= a <= 1 for a in anchors):
        raise ValueError("Fine-sweep centres must be finite digital commands in [0,1].")
    scale = 2**reference_bits - 1
    codes = {max(0, min(scale, round(a*scale)+offset)) for a in anchors for offset in range(-4, 5)}
    commands = [code/scale for code in sorted(codes)]
    random.Random(0).shuffle(commands)  # repeatable non-monotonic presentation order
    return commands


def measurement_summary(readings):
    rows = summarise_readings(readings)
    differences = []
    for lower, upper in zip(rows, rows[1:]):
        se = (math.sqrt(lower['sample_sd_cdm2']**2/lower['n'] + upper['sample_sd_cdm2']**2/upper['n'])
              if lower['n'] > 1 and upper['n'] > 1 else None)
        differences.append({"lower_command": lower['screen_intensity'], "upper_command": upper['screen_intensity'],
            "command_difference": upper['screen_intensity'] - lower['screen_intensity'],
            "mean_luminance_difference_cdm2": upper['luminance_cdm2'] - lower['luminance_cdm2'],
            "difference_standard_error_cdm2": se})
    return {"levels": rows, "adjacent_measured_differences": differences,
            "conclusion": "Unreviewed measurements; no automatic bit-depth estimate or verification.",
            "interpretation": "Compare repeated differences with instrument uncertainty and drift. A black-level floor or null difference alone does not determine bit depth. Dithering may produce distinct time-averaged luminances."}


def precision_directory(root, profile_id):
    return Path(root)/'diagnostics'/'output_precision'/validate_path_component(profile_id, label='monitor profile')


def latest_precision(root, profile):
    for path in sorted(precision_directory(root, profile.id).glob('*/session.json'), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            if (payload.get('kind') == 'output_precision_session' and
                payload.get('physical_snapshot') == physical_snapshot(profile) and
                payload.get('output_precision') and payload.get('status') in {'inspected', 'measurements_saved', 'incomplete'}):
                return path, payload
        except (OSError, ValueError, TypeError):
            continue
    return None, None


def precision_status(root, profile):
    path, payload = latest_precision(root, profile)
    if not payload:
        return "Not checked. Inspect output, then measure fine increments with a photometer."
    summary = payload.get('measurement_summary', {})
    reviews = sorted(path.parent.glob('review_*.json'))
    assessment = 'not assessed'
    if reviews:
        try:
            review = json.loads(reviews[-1].read_text(encoding='utf-8'))
            assessment = (review['assessment'].replace('_', ' ') if review.get('session_sha256_at_review') == content_hash(payload)
                          else 'previous assessment is stale because the evidence changed')
        except (OSError, ValueError, KeyError, TypeError): pass
    return (format_summary(payload['output_precision']) +
        f"\nMeasurements demonstrate: {len(summary.get('levels', []))} measured command levels; researcher assessment: {assessment}."
        f"\nManufacturer specification (user recorded): {payload['request'].get('manufacturer_specification') or 'not recorded'}."
        f"\nSaved {payload['started_utc']}; recheck after output/driver/display changes.\nRaw evidence: {path}")


class PrecisionSession:
    """One isolated, crash-resistant raw record; never imported as gamma data."""
    export_warning = None
    def __init__(self, root, profile, request):
        self.profile, self.request = profile, request
        commands = precision_commands(request.mode, request.reference_bits, request.anchors)
        self.plan = validate_luminance_session(LuminanceSessionRequest(profile.id), profile)
        self.plan.update(commands=commands, starting_command=commands[0] if commands else 1.0,
                         minimum_command=0.0, mode=request.mode,
                         recommended_readings_per_command=5, random_order_seed=0 if request.mode == 'fine' else None,
                         command_encoding='Raw normalized RGB commands; no gamma/LUT change requested by this test.')
        self.folder = precision_directory(root, profile.id)/(now_utc().replace(':', '').replace('+', '_')+'_'+uuid4().hex[:8])
        self.folder.mkdir(parents=True, exist_ok=False)
        self.session_file = self.folder/'session.json'
        self.session = {'schema_version': 1, 'kind': 'output_precision_session', 'session_uuid': str(uuid4()),
            'started_utc': now_utc(), 'status': 'in_progress', 'finished_utc': None,
            'monitor_profile': profile.to_dict(), 'monitor_profile_sha256': content_hash(profile.to_dict()),
            'physical_snapshot': physical_snapshot(profile), 'request': asdict(request) | {'data_root': None},
            'resolved_test': self.plan, 'readings': [], 'physical_precision_verified': False,
            'measurement_provenance': 'Human-entered photometer readings. No instrument is queried by PsyCoLab; review the instrument, integration time, repeatability and drift.'}
        self._persist()

    def _persist(self):
        self.session['measurement_summary'] = measurement_summary(self.session['readings'])
        with file_lock(self.folder/'.measurement.lock'):
            atomic_write_json(self.session_file, self.session)

    def set_output(self, evidence):
        self.session['output_precision'] = evidence
        self._persist()

    def record(self, command, raw_reading):
        if self.session['status'] != 'in_progress': raise ValueError('Measurement session has ended.')
        if command not in self.plan['commands']: raise ValueError('Command is outside the planned precision sequence.')
        row = {'screen_intensity': command, 'luminance_cdm2': parse_photometer_reading(raw_reading),
               'recorded_utc': now_utc(), 'observation_id': str(uuid4()), 'data_kind': 'unspecified', 'source': 'operator_precision_session'}
        self.session['readings'].append(row)
        try: self._persist()
        except Exception:
            self.session['readings'].pop()
            raise
        return row

    def finish(self):
        rows = summarise_readings(self.session['readings'])
        complete = len(rows) == len(self.plan['commands']) and all(row['n'] >= 5 for row in rows)
        self.session['status'] = ('inspected' if self.request.mode == 'inspect' else
                                  'measurements_saved' if complete else 'incomplete')
        self.session['finished_utc'] = now_utc()
        self._persist()
        return self.session_file


def record_precision_review(root, profile, *, assessment, notes):
    if assessment not in {'resolved_increments', 'no_resolved_difference', 'inconclusive', 'not_assessed'}:
        raise ValueError('Choose a measurement assessment.')
    path, payload = latest_precision(root, profile)
    if not payload: raise ValueError('Inspect the selected output first.')
    if assessment in {'resolved_increments', 'no_resolved_difference'}:
        levels = payload.get('measurement_summary', {}).get('levels', [])
        if len(levels) < 2 or any(row['n'] < 2 for row in levels):
            raise ValueError('This assessment needs repeated readings at at least two commands; choose inconclusive otherwise.')
    if assessment != 'not_assessed' and not notes.strip():
        raise ValueError('Record the tested increments, instrument uncertainty and your reason in notes.')
    review = {'recorded_utc': now_utc(), 'session_uuid': payload['session_uuid'],
              'session_sha256_at_review': content_hash(payload), 'assessment': assessment, 'notes': notes.strip(),
              'physical_precision_verified': False, 'scope': 'Researcher assessment of tested increments; not certification of native panel bit depth.'}
    destination = path.parent/('review_'+now_utc().replace(':', '').replace('+', '_')+'_'+uuid4().hex[:8]+'.json')
    atomic_write_json(destination, review)
    return destination


def run_precision_session(request, *, repo_root, data_root=None):
    from ..config.monitor import load_monitor_profiles
    from .display import select_screen
    from .output_precision import create_output_window
    profile = load_monitor_profiles(repo_root)[request.monitor_profile_id]
    root = config_root(repo_root, data_root)
    session = PrecisionSession(root, profile, request)
    try:
        if request.mode == 'inspect':
            screen, _ = select_screen(profile)
            window, evidence = create_output_window(screen, width=64, height=64, visible=False, vsync=True)
            try:
                evidence['window_scope'] = 'hidden inspection; measure fullscreen to inspect the acquisition-size window'
                session.set_output(evidence)
            finally: window.close()
        else:
            from .geometry_check import _draw_luminance_session
            _draw_luminance_session(profile, request, session)
        return session.finish()
    except BaseException as exc:
        session.session.update(status='error', finished_utc=now_utc(), error=repr(exc))
        try: session._persist()
        except Exception as record_error: exc.add_note(f'Could not save interrupted precision status: {record_error!r}')
        raise
