"""Optional TUI refresh: check saved files, then resume in a fresh interpreter.

The temporary handoff is navigation state, never another parameter format or a
scientific source. Ordinary JSON/Python files retain authority. A small launcher
loop keeps repeated refreshes from accumulating parent TUI processes.
"""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

STATE_ENV = "PSYCOLAB_REFRESH_STATE"
REFRESH_EXIT = 75


@dataclass(frozen=True)
class RefreshRequest:
    state: dict


def _environment(root, cache):
    return os.environ | {
        "PSYCOLAB_REPO_ROOT": str(root),
        # A fresh cache also prevents same-second/same-size Python edits from
        # loading stale .pyc files. No researcher files or caches are deleted.
        "PYTHONPYCACHEPREFIX": str(cache),
        "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root), os.environ.get("PYTHONPATH", "")]),
    }


def capture_state(app):
    from textual.widgets import Input, Select
    from .setup import ExperimentConfigScreen, ReviewScreen, DisplayCheckScreen
    from .stimulus_parameters import StimulusParametersPanel
    from .review_files import actual_json_sources
    from ..config.stimulus_parameters import document_for
    from ..stimuli.registry import get_stimulus
    from ..experiments._internal.registry import get_experiment

    screen = app.screen
    pages = {"StimuliScreen": "stimuli", "ExperimentsScreen": "experiments",
             "HelpScreen": "help", "DataScreen": "data", "DisplayCheckScreen": "display"}
    if screen is not app.screen_stack[0] and not isinstance(screen, (ExperimentConfigScreen, ReviewScreen)) and type(screen).__name__ not in pages:
        raise ValueError("Save or close this editor/dialog before refreshing")
    home = app.screen_stack[0]
    state = dict(repo_root=str(app.repo_root), data_root=str(app.data_root), run_intent=app.run_intent,
                 include_historical=app.include_historical, page=pages.get(type(screen).__name__, "setup"),
                 home={widget.id: widget.value for widget in home.query("Input, Select")
                       if widget.id and widget.value is not Select.BLANK},
                 source_paths=list(app.loaded_source_hashes))
    if isinstance(screen, DisplayCheckScreen):
        state["display_values"] = {w.id: w.value for w in screen.query("Input, Select")
                                   if w.id and w.value is not Select.BLANK}
        state["display_stage"] = screen.active_calibration_stage
    configuration = next((s for s in reversed(app.screen_stack) if isinstance(s, ExperimentConfigScreen)), None)
    if isinstance(screen, ReviewScreen):
        request = screen.request
        sources = getattr(screen, "_file_sources", None) or actual_json_sources(app, request)
        spec = get_experiment(request.experiment_id)
        raw = dict(request.experiment_values)
        stimuli = dict(request.stimulus_snapshots)
        state["page"] = "review"
    elif configuration is screen:
        from ..config.models import SetupRequest
        spec = configuration.experiment
        raw = configuration._field_values(allow_incomplete=True)
        request = SetupRequest(configuration.participant_id, configuration.session_mode, spec.id,
                               configuration.monitor_profile_id, raw, data_root=str(configuration.data_root))
        panels = list(configuration.query(StimulusParametersPanel))
        stimuli = {p.slot: p.loaded for p in panels if p.loaded}
        sources = {"experiment": getattr(configuration, "parameter_json_path", None),
                   "stimuli": {p.slot: p.path for p in panels if p.path}}
        state["page"] = "configuration"
    else:
        return state
    # Values still equal to the loaded defaults follow Python default edits.
    # Deliberate overrides and selected ordinary JSON retain their precedence.
    defaults = {field.key: field.default for field in spec.fields}
    overrides = {}
    for field in spec.fields:
        if field.key not in raw:
            continue
        try:
            value = field.coerce(raw[field.key])
        except (ValueError, TypeError):
            value = raw[field.key]
        if value != defaults[field.key]:
            overrides[field.key] = value
    follow_defaults = [slot for slot, selected in stimuli.items()
                       if selected["file_identity"] == "library_defaults" and
                       selected["document"]["parameters"] == document_for(get_stimulus(selected["document"]["stimulus_id"]))["parameters"]]
    key = (request.participant_id, request.experiment_id, request.monitor_profile_id)
    state.update(request=asdict(request), overrides=overrides, stimuli=stimuli,
                 follow_defaults=follow_defaults, mapping=app.mapping_drafts.get(key, {}),
                 sources={"experiment": str(sources["experiment"]) if sources["experiment"] else None,
                          "stimuli": {slot: str(path) for slot, path in sources["stimuli"].items()}})
    return state


def prepare_state(state, root):
    """Resolve the current files using fresh definitions, before touching widgets."""
    from dataclasses import replace
    from ..config.models import SetupRequest
    from ..config.monitor import load_monitor_profiles
    from ..config.preflight import validate_setup
    from ..config.stimulus_parameters import document_for, load_parameters, snapshot, resolve_stimuli
    from ..experiments._internal.registry import get_experiment, list_experiments
    from ..stimuli.registry import get_stimulus, list_stimuli
    from .parameter_files import load_experiment_json, file_hash

    for name in state.get("source_paths", []):
        path = Path(name)
        if path.is_relative_to(root) and path.suffix == ".py" and path.is_file():
            compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
    list_experiments(include_historical=True)
    list_stimuli()
    if "request" not in state:
        return state
    request = SetupRequest(**state["request"])
    spec = get_experiment(request.experiment_id)
    sources = state["sources"]
    values = (load_experiment_json(Path(sources["experiment"]), spec) if sources["experiment"]
              else spec.field_defaults() | state["overrides"])
    stimuli = dict(state["stimuli"])
    for slot in state["follow_defaults"]:
        stimulus = get_stimulus(stimuli[slot]["document"]["stimulus_id"])
        stimuli[slot] = snapshot(document_for(stimulus), file_identity="library_defaults")
    for slot, name in sources["stimuli"].items():
        document = json.loads(Path(name).read_text(encoding="utf-8-sig"))
        stimuli[slot] = load_parameters(Path(name), get_stimulus(document["stimulus_id"]))
    # Field bindings remain owned by the experiment. Never leave old bound
    # values inside a separately saved stimulus snapshot.
    for slot, bindings in spec.stimulus_field_bindings.items():
        if slot in stimuli:
            selected = stimuli[slot]
            document = selected["document"] | {"parameters": selected["document"]["parameters"] |
                       {key: values[field] for key, field in bindings.items()}}
            stimuli[slot] = snapshot(document, file_identity=selected["file_identity"],
                                     file_sha256=selected.get("file_sha256"))
    files = {name: file_hash(Path(name)) for name in
             [sources["experiment"], *sources["stimuli"].values()] if name}
    if state["page"] == "review":
        values = spec.normalise_values(values)
        stimuli = resolve_stimuli(spec, values, stimuli, repo_root=root)
        request = validate_setup(replace(request, experiment_values=values, stimulus_snapshots=stimuli,
                                        monitor_profile_hash=None), spec,
                                 load_monitor_profiles(root)[request.monitor_profile_id], mode="configuration")
    else:
        # Incomplete fields are allowed on Configuration, as before refresh.
        request = replace(request, experiment_values=values, stimulus_snapshots=stimuli,
                          monitor_profile_hash=None)
        if request.monitor_profile_id not in load_monitor_profiles(root):
            raise ValueError("The selected display profile is no longer available")
    return state | {"prepared_request": asdict(request), "files": files}


def check_refresh(state, root):
    """Check in a separate interpreter while the current interface stays intact."""
    with TemporaryDirectory(prefix="psycolab-refresh-check-") as folder:
        path = Path(folder) / "navigation.json"
        path.write_text(json.dumps(state, allow_nan=False), encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "psychophysics_lab.ui.refresh", str(path)],
                                cwd=root, env=_environment(root, Path(folder) / "bytecode"),
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise ValueError((result.stderr or result.stdout or "File check failed").strip()[-4000:])


def read_refresh_state(root):
    name = os.environ.get(STATE_ENV)
    if not name:
        return None
    state = json.loads(Path(name).read_text(encoding="utf-8"))
    if Path(state["repo_root"]).resolve() != root.resolve():
        raise ValueError("Refresh belongs to a different repository")
    return state


def launch_refreshed(request, root):
    existing = os.environ.get(STATE_ENV)
    if existing:
        Path(existing).write_text(json.dumps(request.state, allow_nan=False), encoding="utf-8")
        return REFRESH_EXIT
    with TemporaryDirectory(prefix="psycolab-refresh-") as folder:
        path = Path(folder) / "navigation.json"
        path.write_text(json.dumps(request.state, allow_nan=False), encoding="utf-8")
        while True:
            env = _environment(root, Path(folder) / uuid4().hex) | {STATE_ENV: str(path)}
            result = subprocess.run([sys.executable, "-m", "psychophysics_lab"], cwd=root, env=env)
            if result.returncode != REFRESH_EXIT:
                return result.returncode


async def restore_state(app, state):
    from textual.widgets import Input, Select
    from .setup import ExperimentConfigScreen, ReviewScreen
    from .parameter_files import file_hash
    from ..config.models import SetupRequest
    from ..experiments._internal.registry import get_experiment

    prepared = prepare_state(state, app.repo_root)
    home = app.screen_stack[0]
    with app.prevent(Input.Changed, Select.Changed):
        for name, value in state["home"].items():
            widget = home.query_one("#" + name)
            if isinstance(widget, Select) and value not in [option[1] for option in widget._options]:
                continue
            widget.value = value
    app._refresh_experiment_context()
    app._refresh_monitor_context()
    app.run_intent = state["run_intent"]
    home.query_one("#run-intent", Select).value = app.run_intent
    app._refresh_run_intent()
    if "prepared_request" not in prepared:
        if state["page"] == "display":
            selected = state.get("display_values", {}).get("geometry-monitor")
            if selected not in app.monitor_profiles:
                raise ValueError("The selected calibration display is no longer available")
            app.display_guide_target_profile_id = selected
        if state["page"] != "setup":
            app.open_hub_page(state["page"])
        if state["page"] == "display":
            # Calibration pages have their own saved navigation. Avoid restoring
            # obsolete report options; preserve plain diagnostic entry fields.
            await app.screen._mounted_event.wait()
            with app.prevent(Input.Changed, Select.Changed):
                for name, value in state.get("display_values", {}).items():
                    widgets = list(app.screen.query("#" + name))
                    if widgets:
                        widget = widgets[0]
                        if isinstance(widget, Input) or (isinstance(widget, Select) and
                                value in [option[1] for option in widget._options]):
                            widget.value = value
            app.screen._refresh_preview()
            app.screen._refresh_latest()
            app.screen._go_to_stage(state["display_stage"], remember=False)
        return
    request = SetupRequest(**prepared["prepared_request"])
    spec = get_experiment(request.experiment_id)
    key = (request.participant_id, request.experiment_id, request.monitor_profile_id)
    app.config_drafts[key] = dict(request.experiment_values)
    app.mapping_drafts[key] = state["mapping"]
    app.review_parameter_files[app.settings_key(request)] = prepared["files"]
    for slot, selected in request.stimulus_snapshots.items():
        name = state["sources"]["stimuli"].get(slot)
        app.stimulus_drafts[(*key, slot)] = (selected, Path(name) if name else None)
    configuration = ExperimentConfigScreen(data_root=Path(state["data_root"]), participant_id=request.participant_id,
        session_mode=request.session_mode, experiment=spec, monitor_profile_id=request.monitor_profile_id,
        defaults=dict(request.experiment_values))
    await app.push_screen(configuration)
    name = state["sources"]["experiment"]
    if name:
        configuration.parameter_json_path = Path(name)
        configuration.parameter_json_hash = file_hash(Path(name))
        configuration.parameter_json_pending = False
    if state["page"] == "review":
        await app.push_screen(ReviewScreen(request=request))


if __name__ == "__main__":
    try:
        payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        # Verify the startup and UI imports as well as scientific definitions.
        from psychophysics_lab.app import build_parser
        from psychophysics_lab.ui.setup import PsyCoLabSetupApp
        prepare_state(payload, Path(payload["repo_root"]))
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
