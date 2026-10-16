from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
import traceback
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, Collapsible, ContentSwitcher
from textual.widgets._select import InvalidSelectValueError

from ..analysis.thresholds import analyse_thresholds
from ..config.models import SetupRequest
from ..config.monitor import load_monitor_profiles
from ..config.local import config_root, content_hash, preferences, save_preferences, load_presets, save_preset
from ..config.preflight import compatible, validate_setup
from ..config.readiness import readiness_text
from .editor import open_source
from ..core.display_tests import TESTS, resolve_test
from ..core.geometry_check import (
    GeometryCheckRequest,
    latest_geometry_report,
    record_geometry_measurement,
)
from ..data.participants import list_participants, validate_participant_id
from ..data.workspace import load_workspace_state, request_from_workspace_state
from ..experiments.registry import get_experiment, list_experiments
from ..experiments.spec import ConfigField, ExperimentSpec
from ..paths import resolve_data_root
from ..stimuli.geometry import physical_length_for_visual_angle
from .calibration_stages import STAGES, stage_states, stage_next_action
from ..config.readiness import diagnostic_matches_profile


NAV_PAGES = (
    ("setup", "Experiment"),
    ("stimuli", "Build Stimuli"),
    ("experiments", "Build Experiments"),
    ("display", "Calibrate"),
    ("simulations", "Scenarios"),
    ("data", "Data"),
    ("help", "Developer"),
)


def _report_ui_exception(app: App, exc: BaseException, *, phase: str) -> None:
    """Best-effort logging for exceptions raised inside Textual message handlers."""
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    try:
        from ..diagnostics import write_crash_report

        report = write_crash_report(
            exc,
            repo_root=getattr(app, "repo_root", None),
            data_root=getattr(app, "data_root", None),
            phase=phase,
        )
        if report is not None:
            print(f"PsyCoLab UI crash report saved to: {report}")
    except Exception:
        pass


def _field_widget_id(field: ConfigField) -> str:
    return f"field-{field.key.replace('_', '-')}"


def _is_blank_select_value(value: Any) -> bool:
    return (
        value is getattr(Select, "BLANK", None)
        or value is getattr(Select, "NULL", None)
    )


def _restorable_calibration_field(widget_id: str | None) -> bool:
    """Only draft actual diagnostic inputs, never dynamic report selectors.

    A saved spatial-report value is a *path*, and Select's options are built
    later from the current diagnostic index. Restoring that path during mount
    raises InvalidSelectValueError and used to terminate PsyCoLab.
    """
    return bool(widget_id and (
        widget_id.startswith("geometry-") or widget_id == "cal-temporal-mode"
    ))


def _workspace_request(data_root: Path) -> SetupRequest | None:
    try:
        return request_from_workspace_state(load_workspace_state(data_root))
    except ValueError:
        return None


def _monitor_summary(profile) -> str:
    width_mm = profile.physical_width_m * 1000.0
    height_mm = profile.physical_height_m * 1000.0
    resolution = (
        f"{profile.expected_resolution_px[0]} × {profile.expected_resolution_px[1]} px expected"
        if profile.expected_resolution_px
        else "fullscreen resolution measured at launch"
    )
    calibration = profile.calibration_status.replace("_", " ")
    notes = profile.notes.strip()
    calibration_notes = profile.calibration_notes.strip()
    lines = [
        f"[b]{profile.display_name}[/b]",
        f"Profile ID: {profile.id} · origin: {profile.origin} · revision {profile.revision}",
        f"Display binding: {'saved' if profile.display_binding else 'NOT BOUND (draft; cannot run human acquisition)' if profile.origin == 'local' else 'legacy reference/verify at launch'}",
        f"Qualified experiments: {', '.join(profile.qualified_experiments) or 'none explicitly qualified'}",
        f"{width_mm:.0f} × {height_mm:.0f} mm · {profile.refresh_rate_hz} Hz · "
        f"viewing distance {profile.viewing_distance_m:.3f} m",
        f"Resolution: {resolution}",
        f"Calibration: {calibration}",
        "Physical dimensions and viewing distance: user/reference values; OS detection cannot validate them.",
        f"Resolution source: {profile.measurement_sources.get('expected_resolution_px', 'unspecified/reference')}; "
        f"refresh source: {profile.measurement_sources.get('refresh_rate_hz', 'unspecified/reference')}",
    ]
    if notes:
        lines.append(notes)
    if calibration_notes:
        lines.append(calibration_notes)
    return "\n".join(lines)


def _prospective_run_path(request: SetupRequest, experiment: ExperimentSpec, profile) -> str:
    values = experiment.normalise_values(request.experiment_values)
    grouping = experiment.data_path_parts(values, profile)
    parts = [
        request.participant_id,
        request.experiment_id,
        request.monitor_profile_id,
        *grouping,
        datetime.now().astimezone().strftime("%Y-%m-%d"),
        "run_NNN",
    ]
    return "/".join(parts)


def _source_candidates(repo_root: Path, experiment: ExperimentSpec) -> tuple[Path, ...]:
    candidates = [repo_root / path for path in experiment.source_paths]
    if not candidates:
        import importlib.util
        for module in (experiment.legacy_module,):
            try:
                spec = importlib.util.find_spec(module)
                if spec and spec.origin:
                    candidates.append(Path(spec.origin))
            except (ImportError, ValueError, AttributeError):
                pass
    unique: list[Path] = []
    for path in candidates:
        if path.resolve().is_relative_to(repo_root.resolve()) and path.is_file() and path not in unique:
            unique.append(path)
    return tuple(unique)


def _stimulus_sources(repo_root: Path) -> tuple[Path, ...]:
    from ..stimuli.registry import list_stimuli
    return tuple(repo_root / item.source_path for item in list_stimuli()
                 if (repo_root / item.source_path).is_file())


def _source_inventory(repo_root, experiment):
    import importlib.util
    from ..stimuli.registry import list_stimuli
    sources = _source_candidates(repo_root, experiment)
    entries = [("Definition", sources[0])] if sources else []
    if experiment.procedure is not None:
        import inspect
        path = Path(inspect.getsourcefile(experiment.procedure))
    else:
        module = importlib.util.find_spec(experiment.legacy_module)
        path = Path(module.origin) if module and module.origin else None
    if path and path.is_file() and path.resolve().is_relative_to(repo_root.resolve()):
        entries.append(("Procedure", path))
    families = set(experiment.stimulus_slots.values())
    for stimulus in list_stimuli():
        if stimulus.family in families:
            path = repo_root / stimulus.source_path
            if path.is_file():
                entries.append((f"Stimulus / renderer: {stimulus.id}", path))
    timeline = repo_root / "configs" / "experiments" / f"{experiment.id}.json"
    if timeline.is_file():
        entries.append(("Trial timeline JSON", timeline))
    return entries


class HubNavigation(Horizontal):
    def on_mount(self):
        page = {"ExperimentsScreen": "experiments", "StimuliScreen": "stimuli",
                "DisplayCheckScreen": "display", "ProfileScreen": "display",
                "DataScreen": "data", "HelpScreen": "help",
                "SimulationsScreen": "simulations",
                "SimulationReviewScreen": "simulations"}.get(type(self.screen).__name__, "setup")
        self.query_one("#nav-" + page, Button).variant = "primary"


def _nav_bar() -> Horizontal:
    return HubNavigation(
        *[Button(label, id=f"nav-{key}") for key, label in NAV_PAGES],
        id="hub-nav",
    )


def _handle_nav(screen: Screen, event: Button.Pressed) -> bool:
    button_id = event.button.id or ""
    if not button_id.startswith("nav-"):
        return False
    event.stop()
    screen.app.open_hub_page(button_id.removeprefix("nav-"))
    return True


class CodeViewScreen(Screen):
    def __init__(self, *, title: str, path: Path) -> None:
        super().__init__()
        self.title_text = title
        self.path = path

    def compose(self) -> ComposeResult:
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Back", id="back", variant="primary")
        with VerticalScroll(id="code-body"):
            yield Static(f"[b]{self.title_text}[/b]\n{self.path}")
            try:
                text = self.path.read_text(encoding="utf-8")
            except Exception as exc:
                text = f"Could not read file: {exc}"
            yield Static(text, id="code-text", markup=False)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "back":
            event.stop()
            self.app.pop_screen()


class HubPage(Screen):
    page_title = "PsyCoLab"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        _handle_nav(self, event)


class ExperimentsScreen(HubPage):
    page_title = "Experiments"

    def compose(self) -> ComposeResult:
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
        specs = list_experiments()
        options = [(spec.display_name, spec.id) for spec in specs]
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]Registered experiments[/b]\n"
                "Experiments are registered explicitly. CSF is the current reference experiment, "
                "not the definition of PsyCoLab."
            )
            yield Select(options, value=specs[0].id, allow_blank=False, id="inspect-experiment")
            yield Static("", id="experiment-inspection")
            yield Select([], id="inspect-source-file", prompt="Choose a definition, procedure or stimulus/renderer")
            yield Button("Open selected source", id="view-selected-source")
            with Horizontal(classes="buttons"):
                yield Button("Inspect definition", id="view-exp-definition")
                yield Button("Inspect runtime", id="view-exp-runtime")
            yield Static("[b]Build a new experiment[/b]: generates a draft procedure and chronological timeline JSON. Test in USER_env before marking Ready; no registry edits.")
            yield Input(placeholder="e.g. new_orientation_task", id="new-experiment-name")
            yield Button("Build new experiment", id="build-new-experiment", variant="primary")
            yield Button("Open USER_env test workbench", id="launch-user-env-experiments")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    def _selected(self) -> ExperimentSpec:
        value = self.query_one("#inspect-experiment", Select).value
        return get_experiment(str(value))

    def _refresh(self) -> None:
        spec = self._selected()
        profiles = ", ".join(spec.compatible_monitor_profiles) or "Any registered profile"
        fields = "\n".join(f"  • {field.label} ({field.kind})" for field in spec.fields)
        sources = _source_candidates(self.app.repo_root, spec)
        inventory = _source_inventory(self.app.repo_root, spec)
        self.query_one("#inspect-source-file", Select).set_options([(f"{role} — {path.relative_to(self.app.repo_root)}", str(path)) for role, path in inventory])
        source_text = "\n".join(f"  • {path.relative_to(self.app.repo_root)}" for path in sources)
        self.query_one("#experiment-inspection", Static).update(
            f"[b]{spec.display_name}[/b]\n{spec.description}\n\n"
            f"ID: {spec.id}\nCompatible displays: {profiles}\n\n"
            f"[b]Configuration fields[/b]\n{fields or '  None'}\n\n"
            f"[b]Inspectable source[/b]\n{source_text or '  No source file located.'}"
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "inspect-experiment":
            self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id in {"launch-user-env-experiments", "launch-user-env-stimuli"}:
            event.stop()
            from ..user_env import UserEnvRequest
            self.app.exit(UserEnvRequest())
            return
        if event.button.id == "build-new-experiment":
            event.stop()
            try:
                from ..authoring import scaffold_draft
                paths = scaffold_draft(self.app.repo_root, self.query_one("#new-experiment-name", Input).value.strip(), kind="experiment")
                self.app.notify(f"Created {len(paths)} draft files; test and publish in USER_env.")
                self.app.inspect_source(paths[0])
            except (ValueError, OSError) as exc:
                self.app.notify(str(exc), severity="error")
            return
        spec = self._selected()
        sources = _source_candidates(self.app.repo_root, spec)
        if event.button.id == "view-selected-source":
            event.stop()
            value = self.query_one("#inspect-source-file", Select).value
            if not _is_blank_select_value(value):
                self.app.inspect_source(Path(str(value)))
            return
        if event.button.id == "view-exp-definition" and sources:
            event.stop()
            self.app.inspect_source(sources[0])
        elif event.button.id == "view-exp-runtime":
            event.stop()
            path = next((path for role, path in _source_inventory(self.app.repo_root, spec) if role == "Procedure"), None)
            if path:
                self.app.inspect_source(path)


class StimuliScreen(HubPage):
    page_title = "Stimuli"

    def compose(self) -> ComposeResult:
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
        sources = _stimulus_sources(self.app.repo_root)
        options = [(path.stem.replace("_", " ").title(), str(path)) for path in sources]
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]Reusable stimuli[/b]\n"
                "Stimuli define what is presented. Experiment procedures, adaptive methods and "
                "framework lifecycle remain separate responsibilities."
            )
            if options:
                yield Select(options, value=options[0][1], allow_blank=False, id="inspect-stimulus")
                yield Static("", id="stimulus-inspection")
                yield Button("Inspect stimulus code", id="view-stimulus-source", variant="primary")
                yield Static("[b]Build a new stimulus[/b]: generates Python and JSON parameters as a draft. Preview and mark Ready in USER_env; no registry edits.")
                yield Input(placeholder="e.g. my_ellipse", id="new-stimulus-name")
                yield Button("Build new stimulus", id="build-new-stimulus")
                yield Button("Open USER_env test workbench", id="launch-user-env-stimuli")
            else:
                yield Static("No reusable stimulus modules are currently registered in the package.")
        yield Footer()

    def on_mount(self) -> None:
        if self.query("#inspect-stimulus"):
            self._refresh()

    def _selected_path(self) -> Path:
        value = self.query_one("#inspect-stimulus", Select).value
        return Path(str(value))

    def _refresh(self) -> None:
        path = self._selected_path()
        relative = path.relative_to(self.app.repo_root)
        text = path.read_text(encoding="utf-8")
        first_doc = ""
        if '"""' in text:
            chunks = text.split('"""', 2)
            if len(chunks) >= 3:
                first_doc = chunks[1].strip()
        self.query_one("#stimulus-inspection", Static).update(
            f"[b]{path.stem.replace('_', ' ').title()}[/b]\n{relative}\n\n{first_doc}"
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "inspect-stimulus":
            self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id in {"launch-user-env-experiments", "launch-user-env-stimuli"}:
            event.stop()
            from ..user_env import UserEnvRequest
            self.app.exit(UserEnvRequest())
            return
        if event.button.id == "build-new-stimulus":
            event.stop()
            try:
                from ..authoring import scaffold_draft
                paths = scaffold_draft(self.app.repo_root, self.query_one("#new-stimulus-name", Input).value.strip(), kind="stimulus")
                self.app.notify(f"Created {len(paths)} draft files; preview and publish in USER_env.")
                self.app.inspect_source(paths[0])
            except (ValueError, OSError) as exc:
                self.app.notify(str(exc), severity="error")
            return
        if event.button.id == "view-stimulus-source":
            event.stop()
            path = self._selected_path()
            self.app.inspect_source(path)


class DisplayCheckScreen(HubPage):
    page_title = "Display Calibration"

    def compose(self) -> ComposeResult:
        profiles = list(self.app.monitor_profiles.values())
        options = [(f"{p.display_name} [{p.id} · rev {p.revision}]", p.id) for p in profiles]
        selected = next(iter(self.app.monitor_profiles))
        state = _workspace_request(self.app.data_root)
        preferred = preferences(self.app.local_config_root).get("active_monitor_profile_id")
        if preferred in self.app.monitor_profiles:
            selected = preferred
        elif state and state.monitor_profile_id in self.app.monitor_profiles:
            selected = state.monitor_profile_id
        guided = getattr(self.app, "display_guide_target_profile_id", None)
        if guided in self.app.monitor_profiles:
            selected = guided
        self.app.display_guide_target_profile_id = None
        remembered = preferences(self.app.local_config_root).get("calibration_active_stage", "bind")
        self.active_calibration_stage = remembered if remembered in dict(STAGES) else "bind"
        from ..core.luminance_session import latest_luminance_pilot
        try:
            pilot_json = latest_luminance_pilot(self.app.local_config_root, selected)
        except (OSError, ValueError):
            # A damaged or locked prior pilot must not prevent the entire
            # calibration hub from opening. The researcher can pick a file.
            pilot_json = None

        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(id="calibration-stage-nav"):
                for stage, label in STAGES:
                    yield Button(label, id=f"cal-stage-{stage}", variant="error")
            yield Static("", id="calibration-stage-summary")
            yield Static("", id="calibration-next-action", markup=False, classes="info-card")
            with Horizontal(classes="buttons"):
                if getattr(self, "return_to_configuration", False):
                    yield Button("Return to Experiment Review" if getattr(self,"return_to_review",False) else "Return to display choice", id="calibration-return")
                yield Button("Start at page 1", id="calibration-start")
                yield Button("Previous", id="calibration-previous")
                yield Button("Next stage", id="calibration-next", variant="primary")
                yield Button("Refresh status", id="calibration-refresh")
            yield Button("Finish calibration setup → Return to Experiment", id="calibration-finish", variant="success")
            yield Static("", id="geometry-status")

        with ContentSwitcher(initial=f"cal-panel-{self.active_calibration_stage}", id="calibration-pages"):
            with VerticalScroll(id="cal-panel-bind", classes="page-body calibration-panel"):
                yield Static(
                    "[b]1 / 6 — DISPLAY[/b]\n"
                    "1. Bind the correct monitor and copy its detected pixel resolution.\n"
                    "2. Measure the illuminated image width/height and eye distance.\n"
                    "3. Save the profile, then choose Next stage. "
                    "Windows scaling and bezel size are not physical measurements.",
                    classes="info-card",
                )
                yield Label("Monitor profile (shared across all six stages)")
                yield Select(options, value=selected, allow_blank=False, id="geometry-monitor")
                yield Button("Bind / edit monitor profile", id="edit-profile", variant="primary")
                yield Static("", id="calibration-bind-detail", classes="info-card")
                with Collapsible(title="Further help · What exactly do I measure?", collapsed=True):
                    yield Static(
                        "1. Use a ruler to measure the illuminated image WIDTH and HEIGHT, "
                        "not the bezel. Convert mm to metres: 610 mm = 0.610 m.\n"
                        "2. Measure the distance from the observer's eye to the display plane.\n"
                        "3. Choose Bind / edit, click Detect connected displays, select your "
                        "physical monitor and copy its displayed pixel resolution/refresh.\n"
                        "4. Enter the physical measurements, save a local revision and return.\n"
                        "A green Display tab means saved binding and recorded manual geometry, "
                        "not automatic laboratory certification."
                    )

            with VerticalScroll(id="cal-panel-geometry", classes="page-body calibration-panel"):
                yield Static(
                    "[b]2 / 6 — GEOMETRY[/b]\n"
                    "1. Choose a bar length, then Launch ruler.\n"
                    "2. Measure the displayed bar with a physical ruler (mm).\n"
                    "3. Enter the measured length, click Record, and inspect the percent error. "
                    "Only declare physical Geometry verified when real measurements support it.",
                    classes="info-card",
                )
                yield Label("Fullscreen test (choose Size / ruler bar for this stage)")
                yield Select(list(TESTS), value="size", allow_blank=False, id="geometry-test")
                yield Label("Requested length units")
                yield Select([("Visual angle (degrees)", "visual_angle_deg"),
                              ("Physical length (mm)", "physical_mm")],
                             value="visual_angle_deg", allow_blank=False, id="geometry-mode")
                yield Label("Requested length")
                yield Input(value="5", id="geometry-value")
                yield Label("Orientation")
                yield Select([("Horizontal", "horizontal"), ("Vertical", "vertical")],
                             value="horizontal", allow_blank=False, id="geometry-orientation")
                yield Label("Bar thickness (mm)")
                yield Input(value="5", id="geometry-thickness")
                yield Label("Position units (relative to screen centre)")
                yield Select([("Millimetres", "mm"), ("Degrees", "degrees")],
                             value="mm", allow_blank=False, id="geometry-position-units")
                yield Static("", id="live-input-domains", markup=False, classes="info-card")
                yield Label("X position")
                yield Input(value="0", id="geometry-x")
                yield Label("Y position")
                yield Input(value="0", id="geometry-y")
                yield Label("Duration (seconds; 0 keeps fullscreen open until Esc / Enter)")
                yield Input(value="0", id="geometry-duration")
                yield Button("Launch ruler / selected fullscreen test", id="launch-geometry",
                             variant="primary")
                yield Static("", id="geometry-preview", classes="info-card")
                yield Static("[b]Latest ruler diagnostic[/b]", classes="section-title")
                yield Static("", id="latest-geometry", classes="info-card")
                yield Label("Physically measured bar length (mm)")
                yield Input(value="", placeholder="e.g. 99.5", id="geometry-measured")
                yield Button("Record measurement in latest diagnostic",
                             id="record-geometry-measurement")
                yield Button("Review physical Geometry (only if measured)",
                             id="edit-geometry-profile")
                with Collapsible(title="Further help · Worked example", collapsed=True):
                    yield Static(
                        "Set size units to Physical length (mm), requested length to 100, "
                        "and run the size/ruler test. If a real ruler shows 99.5 mm, type "
                        "99.5 into Measured bar length and Record. Review the -0.5% error. "
                        "Decide whether this meets your experiment's required tolerance. "
                        "Only then use the profile editor to mark Geometry status Verified. "
                        "Do not mark Verified simply because the fullscreen test ran."
                    )

            with VerticalScroll(id="cal-panel-spatial", classes="page-body calibration-panel"):
                yield Static(
                    "[b]3 / 6 — SPATIAL FREQUENCY[/b]\n"
                    "1. Enter cycles/degree and Launch grating.\n"
                    "2. Return here, choose its report and compare the observed cycles.\n"
                    "3. Select Yes / No / Uncertain and any abnormality, then Record observation. "
                    "A visual assessment is not independent optical certification.",
                    classes="info-card",
                )
                yield Static("", id="spatial-calibration-summary", classes="info-card")
                yield Label("Requested grating frequency (cycles/degree)")
                yield Input(value="1", id="geometry-spatial")
                yield Button("Launch fullscreen spatial grating", id="launch-spatial",
                             variant="primary")
                yield Label("Presentation to review (separate reports are never overwritten)")
                yield Select([], id="spatial-report")
                yield Static("", id="spatial-observation-summary", markup=False, classes="info-card")
                yield Label("Did the displayed pattern match the expected structure?")
                yield Select([("Yes — visually consistent", "consistent"), ("No — discrepancy observed", "discrepancy"),
                              ("Uncertain — needs inspection", "uncertain"), ("Not assessed", "not_assessed")],
                             value="not_assessed", allow_blank=False, id="spatial-assessment")
                yield Label("Optional observed count (a complete light–dark period is one cycle)")
                yield Input(value="", id="spatial-observed-count")
                yield Select([("Complete light–dark cycles", "cycles"), ("Bright maxima (phase/edge dependent)", "bright_maxima")],
                             value="cycles", allow_blank=False, id="spatial-count-kind")
                yield Label("Visible rendering abnormality (use notes for additional abnormalities)")
                yield Select([("Not assessed", "not_assessed"), ("No obvious abnormality", "none"), ("Aliasing", "aliasing"),
                              ("Unexpected orientation", "orientation"), ("Nonuniform spacing", "spacing"),
                              ("Clipping or cutoff", "clipping"), ("Other", "other")],
                             value="not_assessed", allow_blank=False, id="spatial-abnormality")
                yield Input(placeholder="Optional observation notes", id="spatial-observation-notes")
                yield Button("Record observation", id="record-spatial-observation", variant="primary")
                with Collapsible(title="Further help · What should I see?", collapsed=True):
                    yield Static(
                        "A 1 cycle/degree grating has one complete dark-and-light "
                        "period per degree near gaze centre. Compare this with the "
                        "pixels/degree and Nyquist values above. The software pattern "
                        "is a diagnostic, not a physical luminance measurement. "
                        "Changing viewing distance or resolution requires a new check."
                    )

            with VerticalScroll(id="cal-panel-luminance", classes="page-body calibration-panel"):
                yield Static(
                    "[b]4 / 6 — LUMINANCE MAPPING[/b]\n"
                    "1. Open the selected display's intensity / luminance table.\n"
                    "2. Keep the saved mapping or add/correct readings with their original source.\n"
                    "3. Choose Accept luminance values → Timing. Acceptance records your "
                    "selection, not physical verification. Human acquisition still needs real instrument evidence.",
                    classes="info-card",
                )
                yield Button("Step 1 — Review or add saved luminance readings", id="open-active-luminance", variant="primary")
                yield Label("Single-patch normalized digital command (0 to 1)")
                yield Input(value="0.5", id="geometry-luminance")
                yield Button("Launch one static photometer patch", id="launch-patch")
                yield Label("Minimum digital command for interactive sweep (0 <= value < 1)")
                yield Input(
                    value=str(state.experiment_values.get("Background_Screen_intensity", 0.0)
                              if state is not None else 0.0),
                    id="geometry-luminance-background",
                )
                yield Label("Left/Right arrow step (e.g. 0.05 digital intensity)")
                yield Input(value="0.05", id="geometry-luminance-step")
                yield Button("Start fullscreen interactive photometer entry",
                             id="launch-luminance-session", variant="primary")
                yield Button("Open my pilot/test or blank measurement JSON",
                             id="open-luminance-pilot")
                yield Button("Open completed FAKE example JSON (education only)",
                             id="open-luminance-demo")
                yield Label("Optional: full path to a REAL measurement JSON")
                yield Input(value=str(pilot_json) if pilot_json else "",
                            placeholder="C:\\...\\pilot_luminance.json", id="cal-luminance-json-path")
                yield Button("Import and save REAL photometer measurements",
                             id="calibration-import-luminance", variant="success")
                yield Static("", id="cal-luminance-import-feedback")
                yield Button("Advanced: edit all monitor fields / manual entry",
                             id="edit-luminance-profile")
                with Collapsible(title="Further help · Real and example JSON", collapsed=True):
                    yield Static(
                        "Real JSON row: screen_intensity=0.50, luminance_cdm2=(your real meter reading). "
                        "The FAKE example uses 57.2 cd/m² at intensity 0.50 purely to show formatting. "
                        "Demo files are marked example_only and cannot be imported.\n"
                        "For interactive measurement: Left/Right changes intensity; type the meter "
                        "reading (cd/m²) and Enter records one value. Repeat Enter with another "
                        "reading at the same command for repetitions. Esc ends the session.\n"
                        "To import genuine photometer readings instead of using the editor, "
                        "open a pilot JSON and enter at least TWO real cd/m² pairs. "
                        "Method, date and notes are optional. Import + Save keeps you "
                        "on Luminance to inspect the outcome; choose Next stage explicitly. "
                        "Fake/pilot data are only for software Test mode and cannot certify "
                        "physical photometry."
                    )

            with VerticalScroll(id="cal-panel-timing", classes="page-body calibration-panel"):
                yield Static(
                    "[b]5 / 6 — TIMING[/b]\n"
                    "1. Choose binary or sine flicker and a frequency in Hz.\n"
                    "2. Launch the fullscreen diagnostic and review its frame-cycle report.\n"
                    "3. Choose Next stage. Only independent photodiode/equivalent "
                    "measurements can verify physical photon timing.",
                    classes="info-card",
                )
                yield Label("Timing diagnostic type")
                yield Select([("Binary frame flicker", "temporal_binary"),
                              ("Frame-sampled sine wave", "temporal_sine")],
                             value="temporal_binary", allow_blank=False, id="cal-temporal-mode")
                yield Label("Requested temporal frequency (Hz)")
                yield Input(value="7.5", id="geometry-temporal")
                yield Button("Launch fullscreen timing diagnostic", id="launch-temporal",
                             variant="primary")
                yield Button("Review physical photon timing (if independently measured)",
                             id="edit-timing-profile")
                with Collapsible(title="Further help · What is verified?", collapsed=True):
                    yield Static(
                        "Check requested versus realised frame-cycle frequencies and the "
                        "monitor refresh rate. Neither the Windows refresh setting nor "
                        "software flip timestamps measure photon onset. Take independent "
                        "instrument measurements and document them before declaring "
                        "Timing status Verified in the monitor editor. The timing tab "
                        "turns green when a diagnostic is saved, even if physical "
                        "photon-onset verification remains pending."
                    )

            with VerticalScroll(id="cal-panel-review", classes="page-body calibration-panel"):
                yield Static(
                    "[b]6 / 6 — REVIEW[/b]\n"
                    "1. Review the saved results. Green means saved evidence, NOT physical certification.\n"
                    "2. For Human acquisition, review real Geometry, Photometry and Timing "
                    "evidence individually, then qualify the experiment.\n"
                    "3. For software Test/Simulation, finish setup and return to Experiment. "
                    "A photometer is not required for those modes.",
                    classes="info-card",
                )
                yield Static("", id="calibration-review-detail", classes="info-card")
                yield Static("", id="calibration-review-outstanding", classes="info-card", markup=False)
                yield Button("Review physical verification", id="review-physical-verification", variant="primary")
                yield Button("Check / qualify experiment", id="review-qualification", variant="primary")
                yield Button("Advanced monitor profile editor", id="edit-review-profile")
                if self.app.geometry_summary:
                    yield Static(self.app.geometry_summary, id="geometry-last-outcome",
                                 classes="info-card")
                with Collapsible(title="Further help · What if I lack a photometer?", collapsed=True):
                    yield Static(
                        "Leave stages without physical evidence red. You can still develop "
                        "stimuli, inspect model predictions and run simulations. "
                        "An experiment may have different calibration requirements: "
                        "return to Experiment > Review to see its specific blockers. "
                        "Finish setup to return to Experiment at any time. Use Check / "
                        "qualify experiment for deliberate qualification after laboratory review."
                    )
        yield Footer()

    def _go_to_stage(self, stage: str, *, remember: bool = True) -> None:
        if stage not in dict(STAGES):
            return
        self.active_calibration_stage = stage
        self.query_one("#calibration-pages", ContentSwitcher).current = f"cal-panel-{stage}"
        if remember:
            try:
                save_preferences(self.app.local_config_root, calibration_active_stage=stage)
            except (OSError, ValueError) as exc:
                self.app.notify(
                    f"Page changed, but remembering it failed: {exc}",
                    severity="warning", timeout=7,
                )
        self._refresh_stage_status()

    def _refresh_stage_status(self) -> None:
        if not self.is_mounted:
            return
        selected = self.query_one("#geometry-monitor", Select).value
        if _is_blank_select_value(selected) or str(selected) not in self.app.monitor_profiles:
            return
        profile = self._profile()
        states = stage_states(profile, self.app.local_config_root)
        from ..config.calibration_progress import calibration_progress
        from ..config.preflight import qualification_checks
        progress = calibration_progress(profile, self.app.local_config_root)
        # These physical indicators use the same declarations as acquisition.
        from ..experiments.contrast_sensitivity import CSF_SPEC
        physical = {row['key']: row['passed'] for row in qualification_checks(CSF_SPEC, profile)}
        colours = {key: ('green' if physical.get(key, item['completed']) else
                         'yellow' if item['completed'] else 'red') for key, item in progress.items()}
        for stage, title in STAGES:
            ready, _ = states[stage]
            button = self.query_one(f"#cal-stage-{stage}", Button)
            button.variant = {'green': 'success', 'yellow': 'warning', 'red': 'error'}[colours[stage]]
            button.label = f"{title} {'✓' if colours[stage] == 'green' else '!' if ready else '✕'}"
            button.set_class(stage == self.active_calibration_stage, "calibration-active")
        self.query_one("#calibration-stage-summary", Static).update(
            "[b]GREEN = stated check satisfied; AMBER = saved, physical verification pending; RED = missing.[/b] "
            "Spatial and Review describe setup records only. Human readiness applies the selected experiment's requirements.\n"
            f"[b]{profile.display_name}[/b] · revision {profile.revision} | "
            + "   ".join(
                f"[{colours[k]}]"
                f"{'✓' if states[k][0] else '✕'} {title.split(' · ')[1]}[/]"
                for k, title in STAGES
            )
            + "\n" + states[self.active_calibration_stage][1]
        )
        from ..config.calibration_progress import calibration_progress
        progress = calibration_progress(profile, self.app.local_config_root)
        self.query_one("#calibration-next-action", Static).update(
            stage_next_action(self.active_calibration_stage, progress)
        )
        self.query_one("#calibration-finish", Button).display = self.active_calibration_stage == "review"
        if self.active_calibration_stage == "review":
            self.query_one("#calibration-stage-summary", Static).update(
                f"{profile.display_name} · revision {profile.revision}\nSetup completion, physical verification and experiment qualification are separate.")
        self.query_one("#calibration-bind-detail", Static).update(
            _monitor_summary(profile) + "\n\n[b]Display status:[/b] " + states["bind"][1]
        )
        from ..config.calibration_review import review_summary
        summary, outstanding = review_summary(profile, self.app.local_config_root)
        self.query_one("#calibration-review-detail", Static).update(summary)
        self.query_one("#calibration-review-outstanding", Static).update("Outstanding actions\n\n" + outstanding)

    def on_mount(self) -> None:
        for key, value in self.app.display_draft.items():
            # Old preferences and navigation drafts may include a selected
            # spatial diagnostic path, populated only after this screen mounts.
            # Ignore that transient selector instead of crashing at startup.
            if not _restorable_calibration_field(key):
                continue
            matches = self.query("#" + key)
            if matches:
                try:
                    matches.first().value = value
                except (ValueError, TypeError, InvalidSelectValueError):
                    # A saved monitor/diagnostic option can disappear following
                    # a physical display change or upgrade. Retain the current
                    # safe default rather than terminate the full TUI.
                    continue
        self._refresh_preview()
        self._refresh_latest()
        self._refresh_stage_status()
        if self.app.geometry_summary:
            self.query_one("#geometry-status", Static).update(self.app.geometry_summary)

    def on_screen_resume(self) -> None:
        if not self.is_mounted:
            return
        selector = self.query_one("#geometry-monitor", Select)
        current = selector.value
        selector.set_options([
            (f"{p.display_name} [{p.id} · rev {p.revision}]", p.id)
            for p in self.app.monitor_profiles.values()
        ])
        preferred = preferences(self.app.local_config_root).get("active_monitor_profile_id")
        selector.value = preferred if preferred in self.app.monitor_profiles else current
        self._refresh_preview()
        self._refresh_latest()
        remembered = preferences(self.app.local_config_root).get(
            "calibration_active_stage", self.active_calibration_stage
        )
        self._go_to_stage(remembered, remember=False)

    def _profile(self):
        value = self.query_one("#geometry-monitor", Select).value
        return self.app.monitor_profiles[str(value)]

    def _request(self):
        return GeometryCheckRequest(
            monitor_profile_id=str(self.query_one("#geometry-monitor", Select).value),
            mode=str(self.query_one("#geometry-mode", Select).value),
            value=float(self.query_one("#geometry-value", Input).value),
            orientation=str(self.query_one("#geometry-orientation", Select).value),
            thickness_mm=float(self.query_one("#geometry-thickness", Input).value),
            data_root=str(self.app.data_root),
            test_kind=str(self.query_one("#geometry-test", Select).value),
            position_units=str(self.query_one("#geometry-position-units", Select).value),
            x_position=float(self.query_one("#geometry-x", Input).value),
            y_position=float(self.query_one("#geometry-y", Input).value),
            spatial_cpd=float(self.query_one("#geometry-spatial", Input).value),
            temporal_hz=float(self.query_one("#geometry-temporal", Input).value),
            digital_command=float(self.query_one("#geometry-luminance", Input).value),
            duration_s=float(self.query_one("#geometry-duration", Input).value))

    def _luminance_request(self):
        from ..core.luminance_session import LuminanceSessionRequest
        return LuminanceSessionRequest(
            monitor_profile_id=str(self.query_one("#geometry-monitor", Select).value),
            background_command=float(self.query_one("#geometry-luminance-background", Input).value),
            command_step=float(self.query_one("#geometry-luminance-step", Input).value),
            patch_degrees=6.0,
            data_root=str(self.app.data_root),
        )

    def _refresh_preview(self) -> None:
        try:
            from .domain_feedback import diagnostic_domains
            diagnostic_domains(self)
            profile = self._profile()
            resolution = profile.expected_resolution_px
            if resolution:
                bar, plan = resolve_test(profile, self._request(), resolution)
                details = json.dumps(plan, indent=2)
            else:
                # Refresh-rate planning is pure even before display enumeration.
                from ..core.display_tests import temporal_plan
                request = self._request()
                details = "Resolution will be verified at launch."
                if request.test_kind.startswith("temporal_"):
                    details += "\n" + json.dumps(temporal_plan(profile.refresh_rate_hz, request.temporal_hz, request.test_kind), indent=2)
            self.query_one("#geometry-preview", Static).update(_monitor_summary(profile) + "\n\n" + details)
            status = self.query_one("#geometry-status", Static)
            if profile.origin == "local" and not profile.display_binding:
                status.update(
                    "[yellow]Saved geometry is an UNBOUND DRAFT: fullscreen calibration "
                    "cannot start yet. Click Bind / edit monitor profile → "
                    "Detect connected displays, choose your monitor, then Save local revision.[/yellow]"
                )
            elif not self.app.geometry_summary:
                status.update("")
            from ..stimuli.spatial_calibration import resolve_spatial_geometry
            if resolution is not None:
                calibration = resolve_spatial_geometry(profile, resolution)
                self.query_one("#spatial-calibration-summary", Static).update(
                    "[b]Geometric frequency calibration (gaze centre)[/b]\n"
                    f"Physical pixel pitch: X={calibration.pixel_pitch_m[0] * 1000:.4f} mm, "
                    f"Y={calibration.pixel_pitch_m[1] * 1000:.4f} mm\n"
                    f"Pixels/degree: X={calibration.pixels_per_degree_at_centre[0]:.3f}, "
                    f"Y={calibration.pixels_per_degree_at_centre[1]:.3f}\n"
                    f"Nyquist: X={calibration.nyquist_cpd_at_centre[0]:.3f}, "
                    f"Y={calibration.nyquist_cpd_at_centre[1]:.3f} cpd\n"
                    f"Geometry verification status: {profile.geometry_status}\n"
                    "At 1 cpd the local period is approximately the listed pixels/degree. "
                    "Remeasure if display resolution, viewing distance or active image size changes."
                )
            else:
                self.query_one("#spatial-calibration-summary", Static).update(
                    "[yellow]This monitor profile has no expected fullscreen pixel resolution. "
                    "Bind and inspect the monitor in Edit / copy display profile, record its "
                    "active resolution, then check it with the fullscreen display test.[/yellow]"
                )
        except (ValueError, TypeError) as exc:
            self.query_one("#geometry-preview", Static).update(str(exc))

    def _refresh_latest(self) -> None:
        profile_id = str(self.query_one("#geometry-monitor", Select).value)
        report = latest_geometry_report(self.app.local_config_root, profile_id, ruler_only=True)
        if report is None:
            text = "No geometry check has been saved for this display in the active workspace."
        else:
            try:
                payload = json.loads(report.read_text(encoding="utf-8"))
                bar = payload.get("resolved_bar", {})
                measurement = payload.get("measurement", {})
                measured = measurement.get("measured_length_mm")
                measured_text = "not entered" if measured is None else (
                    f"{float(measured):.2f} mm; error {float(measurement['error_percent']):+.2f}%"
                )
                text = (
                    f"{report.relative_to(self.app.local_config_root)}\n"
                    f"Status: {payload.get('status', 'unknown')}\n"
                    f"Profile revision in report: {payload.get('monitor_profile', {}).get('revision', 'unknown')}"
                    f" — {'CURRENT' if diagnostic_matches_profile(payload, self._profile()) else 'STALE: check current revision'}\n"
                    f"Expected: {bar.get('intended_length_mm', 'n/a')} mm\n"
                    f"Rendered: {bar.get('length_px', 'n/a')} px\n"
                    f"Ruler measurement: {measured_text}"
                )
            except Exception as exc:
                text = f"Could not read latest diagnostic: {exc}"
        self.query_one("#latest-geometry", Static).update(text)
        self._refresh_spatial_observation()

    def _refresh_spatial_observation(self):
        from ..config.calibration_progress import diagnostic_evidence
        from ..config.spatial_observation import report_summary, observations
        rows = diagnostic_evidence(self._profile(), self.app.local_config_root)["spatial"]
        selector = self.query_one("#spatial-report", Select)
        previous = getattr(self, "_spatial_report", None)
        self._spatial_rows = {row["path"]: row for row in rows}
        selected = previous if previous in self._spatial_rows else rows[0]["path"] if rows else None
        with self.prevent(Select.Changed):
            selector.set_options([(f"{row['payload'].get('finished_utc', row['payload'].get('started_utc', 'Historical'))} · {row['payload'].get('diagnostic_uuid', row['path'])} · {row['payload'].get('status')}", row["path"]) for row in rows])
            selector.value = selected if selected is not None else Select.BLANK
        self._spatial_report = selected
        self._show_spatial_observation()

    def _show_spatial_observation(self):
        from ..config.spatial_observation import report_summary, observations
        row = self._spatial_rows.get(self._spatial_report)
        record = None
        if row:
            payload = row["payload"]
            records = observations(self.app.local_config_root / row["path"], payload)
            record = records[-1] if records else None
            text = report_summary(payload) + ("\nSTALE / unsuccessful evidence: present a fresh test." if not row["compatible"] else "")
            text += (f"\nLatest observation: {record['assessment']} / {record['abnormality']} at {record['recorded_utc']}" if record else "\nAwaiting researcher observation. Closing fullscreen is not validation.")
        else:
            text = "Not tested. Present a spatial grating, then record your observation here."
        self.query_one("#spatial-observation-summary", Static).update(text)
        record = record or {}
        with self.prevent(Select.Changed, Input.Changed):
            self.query_one("#spatial-assessment", Select).value = record.get("assessment", "not_assessed")
            self.query_one("#spatial-abnormality", Select).value = record.get("abnormality", "not_assessed")
            self.query_one("#spatial-count-kind", Select).value = record.get("count_kind", "cycles")
            self.query_one("#spatial-observed-count", Input).value = str(record["observed_count"]) if record.get("observed_count") is not None else ""
            self.query_one("#spatial-observation-notes", Input).value = record.get("notes", "")

    def _save_fullscreen_navigation(self, kind):
        # Temporary UI state only; no monitor revision or certification write.
        settings = {widget.id: widget.value for widget in self.query("Input, Select")
                    if _restorable_calibration_field(widget.id)
                    and not _is_blank_select_value(widget.value)}
        save_preferences(self.app.local_config_root, calibration_navigation={
            "section": "calibrate", "profile": self._profile().id,
            "stage": self.active_calibration_stage, "diagnostic_kind": kind,
            "settings": settings, "return_to_review": bool(getattr(self, "return_to_review", False)),
        })

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "spatial-report" and not _is_blank_select_value(event.value):
            self._spatial_report = str(event.value)
            self._show_spatial_observation()
        if event.select.id and (event.select.id.startswith("geometry-") or event.select.id=='cal-temporal-mode'):
            self._refresh_preview()
            if event.select.id == "geometry-monitor":
                self._refresh_latest()
                self._refresh_stage_status()
                from ..core.luminance_session import latest_luminance_pilot
                chosen = str(event.select.value)
                if chosen in self.app.monitor_profiles:
                    try:
                        pilot = latest_luminance_pilot(self.app.local_config_root, chosen)
                    except (OSError, ValueError) as exc:
                        pilot = None
                        self.app.notify(
                            f"Could not load latest pilot automatically: {exc}. Enter the JSON path manually.",
                            severity="warning", timeout=8,
                        )
                    self.query_one("#cal-luminance-json-path", Input).value = str(pilot) if pilot else ""

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id and event.input.id.startswith("geometry-") and event.input.id != "geometry-measured":
            self._refresh_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "record-spatial-observation":
            event.stop()
            try:
                from ..config.spatial_observation import record_observation
                if not self._spatial_report:
                    raise ValueError("Present a spatial diagnostic first.")
                count = self.query_one("#spatial-observed-count", Input).value.strip()
                record_observation(self.app.local_config_root, self.app.local_config_root / self._spatial_report,
                    self._profile(), assessment=str(self.query_one("#spatial-assessment", Select).value),
                    abnormality=str(self.query_one("#spatial-abnormality", Select).value),
                    observed_count=float(count) if count else None,
                    count_kind=str(self.query_one("#spatial-count-kind", Select).value),
                    notes=self.query_one("#spatial-observation-notes", Input).value)
                self._refresh_spatial_observation()
                self._refresh_stage_status()
                self.query_one("#geometry-status", Static).update("Observation saved. Review it here, then use Next stage deliberately. This is not physical certification.")
            except (OSError, ValueError, TypeError) as exc:
                self.query_one("#geometry-status", Static).update(f"Observation not saved: {exc}")
            return
        if event.button.id == "open-active-luminance":
            event.stop()
            from .luminance_data import open_luminance_editor
            error = open_luminance_editor(self.app, self._profile())
            if error:
                self.query_one("#geometry-status", Static).update(error)
                self.app.notify(error, title="Luminance data need inspection", severity="warning", timeout=12)
            return
        if event.button.id in {"calibration-finish", "review-physical-verification", "review-qualification"}:
            event.stop()
            try:
                profile_id = self._profile().id
                self.app.reload_profiles()
                profile = self.app.monitor_profiles.get(profile_id)
                if profile is None:
                    raise ValueError("Selected monitor is no longer available. Restore it on Display; no fallback was selected.")
                save_preferences(self.app.local_config_root, active_monitor_profile_id=profile_id,
                                 calibration_active_stage="review")
                if event.button.id == "calibration-finish":
                    from ..config.calibration_progress import calibration_progress
                    progress = calibration_progress(profile, self.app.local_config_root)
                    pending = [name for name in ("bind", "geometry", "spatial", "luminance", "timing") if not progress[name]["completed"] or (name in {"geometry", "timing"} and not progress[name]["verified"]) or (name=="luminance" and not progress[name].get("accepted"))]
                    draft = preferences(self.app.local_config_root).get("calibration_experiment_draft")
                    if isinstance(draft, dict):
                        save_preferences(self.app.local_config_root, calibration_experiment_draft=dict(draft, profile=profile_id))
                    if getattr(self, "return_to_review", False):
                        save_preferences(self.app.local_config_root, calibration_review_return=None)
                        self.app.pop_screen()
                        return
                    self.app.open_hub_page("setup")
                    self.app.screen_stack[0].query_one("#monitor-profile", Select).value = profile_id
                    message = "Calibration setup saved. " + ("Incomplete observations or laboratory verification remain: " + ", ".join(pending) + ". " if pending else "Setup records are available. ") + "Continue configuring experiments; human acquisition remains subject to experiment-specific preflight."
                    self.app.screen_stack[0].query_one("#setup-status", Static).update(message)
                    self.app.notify(message, timeout=15)
                else:
                    from .calibration_review import PhysicalVerificationScreen, ExperimentQualificationScreen
                    cls = PhysicalVerificationScreen if event.button.id == "review-physical-verification" else ExperimentQualificationScreen
                    self.app.push_screen(cls(profile))
            except (OSError, ValueError) as exc:
                self.query_one("#geometry-status", Static).update(str(exc))
            return
        if event.button.id == "calibration-return":
            event.stop()
            if getattr(self, "return_to_review", False):
                save_preferences(self.app.local_config_root, calibration_review_return=None)
            self.app.pop_screen()
            return
        if (event.button.id or "").startswith("cal-stage-"):
            event.stop()
            self._go_to_stage(event.button.id.removeprefix("cal-stage-"))
            return
        if event.button.id in {"calibration-start", "calibration-previous", "calibration-next"}:
            event.stop()
            stages = [key for key, _ in STAGES]
            position = stages.index(self.active_calibration_stage)
            if event.button.id == "calibration-start":
                destination = "bind"
            elif event.button.id == "calibration-previous":
                destination = stages[max(0, position - 1)]
            else:
                destination = stages[min(len(stages) - 1, position + 1)]
                from ..config.calibration_progress import calibration_progress
                current = calibration_progress(self._profile(), self.app.local_config_root)[self.active_calibration_stage]
                if not current["completed"]:
                    self.query_one("#geometry-status", Static).update(
                        f"[yellow]Continuing past an INCOMPLETE {self.active_calibration_stage} stage; "
                        "you can return later. This does not certify the monitor.[/yellow]"
                    )
            self._go_to_stage(destination)
            return
        if event.button.id == "calibration-refresh":
            event.stop()
            self._refresh_preview()
            self._refresh_latest()
            self._refresh_stage_status()
            return
        if event.button.id in {"edit-geometry-profile", "edit-timing-profile"}:
            event.stop()
            from .calibration_review import PhysicalVerificationScreen
            focus = ("geometry_status" if event.button.id == "edit-geometry-profile"
                     else "timing_status")
            self.app.push_screen(PhysicalVerificationScreen(self._profile(), focus_category=focus))
            return
        if event.button.id in {"edit-profile", "edit-luminance-profile", "edit-review-profile"}:
            event.stop()
            from .profiles import ProfileScreen
            save_preferences(self.app.local_config_root, active_monitor_profile_id=self._profile().id)
            focus = {
                "edit-luminance-profile": "profile-luminance-path",

                "edit-geometry-profile": "profile-geometry_status",
                "edit-timing-profile": "profile-timing_status",
            }.get(event.button.id)
            self.app.push_screen(ProfileScreen(profile=self._profile(), focus_field=focus))
            return
        status = self.query_one("#geometry-status", Static)
        if event.button.id == "calibration-import-luminance":
            event.stop()
            try:
                from ..config.calibration_workflow import (
                    import_and_save_luminance, advance_if_completed,
                )
                path = self.query_one("#cal-luminance-json-path", Input).value
                saved, warnings = import_and_save_luminance(
                    self._profile(), self.app.local_config_root, path
                )
                self.app.reload_profiles()
                persisted = self.app.monitor_profiles.get(saved.id)
                if persisted != saved:
                    raise RuntimeError("Saved luminance profile failed to reload from disk.")
                selector = self.query_one("#geometry-monitor", Select)
                selector.set_options([
                    (f"{p.display_name} [{p.id} · rev {p.revision}]", p.id)
                    for p in self.app.monitor_profiles.values()
                ])
                selector.value = saved.id
                self._refresh_preview()
                self._refresh_latest()
                self._refresh_stage_status()
                message = (
                    f"[green]SAVED {len(saved.luminance_calibration)} entered intensity / cd/m² pairs "
                    f"to monitor {saved.id}, revision {saved.revision}.[/green] "
                    "Measurement stage COMPLETE; physical certification is still UNVERIFIED."
                )
                if warnings:
                    message += "\n[yellow]Optional information: " + "; ".join(warnings) + "[/yellow]"
                if self.active_calibration_stage == "luminance":
                    message += "\nSaved. Review the values here, then select Next stage → Timing when ready."
                status.update(message)
                self.query_one("#cal-luminance-import-feedback", Static).update(message)
                self.app.notify("Real luminance measurements saved to profile. No automatic certification.",
                                timeout=10)
            except (ValueError, TypeError, OSError, RuntimeError, KeyError) as exc:
                message = f"[red]Luminance NOT imported or confirmed: {exc}[/red]"
                status.update(message)
                self.query_one("#cal-luminance-import-feedback", Static).update(message)
                self.app.notify(str(exc), title="Luminance import failed",
                                severity="error", timeout=12)
            return
        if event.button.id == "launch-luminance-session":
            event.stop()
            try:
                from ..core.display import preflight_fullscreen_display
                from ..core.luminance_session import validate_luminance_session
                profile = self._profile()
                request = self._luminance_request()
                preflight_fullscreen_display(profile)
                validate_luminance_session(request, profile)
                self._save_fullscreen_navigation("luminance_session")
                self.app.exit(request)
            except (ValueError, TypeError, OSError) as exc:
                status.update(f"[red]Luminance test NOT launched: {exc}[/red]")
                self.app.notify(str(exc), title="Luminance test blocked", severity="error", timeout=12)
        elif event.button.id == "open-luminance-demo":
            event.stop()
            try:
                import os
                import sys
                from ..config.calibration_templates import write_luminance_demo
                path = write_luminance_demo(self.app.local_config_root, self._profile())
                note = (f"FAKE EXAMPLE ONLY: {path}. The data were invented for learning. "
                        "They are NOT photometer observations and cannot be imported.")
                if sys.platform == "win32":
                    try:
                        os.startfile(str(path))
                    except OSError as exc:
                        note += f" Open the path manually: {exc}"
                status.update(f"[yellow]{note}[/yellow]")
                self.app.notify("Synthetic example opened — NOT calibration.", timeout=8)
            except (OSError, ValueError) as exc:
                status.update(f"[red]Could not create demo JSON: {exc}[/red]")
        elif event.button.id == "open-luminance-pilot":
            event.stop()
            try:
                import os
                import sys
                from ..core.luminance_session import latest_luminance_pilot
                from ..config.calibration_templates import write_luminance_example
                profile = self._profile()
                path = (latest_luminance_pilot(self.app.local_config_root, profile.id)
                        or write_luminance_example(self.app.local_config_root, profile))
                note = f"Editable luminance JSON: {path}. Fill at least TWO genuine intensity/cd/m² pairs. Method, date and notes are optional. Load into profile editor, then SAVE."
                if sys.platform == "win32":
                    try:
                        os.startfile(str(path))
                    except OSError as exc:
                        note += f" Windows could not open it automatically ({exc}); copy and open the displayed path in your editor."
                else:
                    note += " Open the displayed path using your local JSON editor."
                status.update(f"[yellow]{note}[/yellow]")
                self.app.notify("Editable luminance JSON prepared; measurements remain unverified.", timeout=8)
            except (OSError, ValueError) as exc:
                status.update(f"[red]Could not open luminance JSON: {exc}[/red]")
                self.app.notify(str(exc), title="Luminance JSON not opened", severity="error", timeout=10)
        elif event.button.id in {"launch-geometry", "launch-spatial", "launch-temporal", "launch-patch"}:
            event.stop()
            try:
                requested_kind = {
                    "launch-spatial": "spatial",
                    "launch-temporal": str(self.query_one("#cal-temporal-mode", Select).value),
                    "launch-patch": "luminance_patch",
                }.get(event.button.id)
                if requested_kind:
                    self.query_one("#geometry-test", Select).value = requested_kind
                request = self._request()
                profile = self._profile()
                # Check the physical binding and actual OS mode while the
                # Textual screen is still open. If it fails, never exit into
                # the fullscreen runner (which previously crashed the launcher).
                from ..core.display import preflight_fullscreen_display
                preflight_fullscreen_display(profile)
                if profile.expected_resolution_px:
                    resolve_test(profile, request, profile.expected_resolution_px)
                self._save_fullscreen_navigation(request.test_kind)
                self.app.exit(request)
            except Exception as exc:
                status.update(f"[red]Calibration NOT launched: {exc}[/red]")
                self.app.notify(str(exc), title="Calibration blocked", severity="error", timeout=12)
        elif event.button.id == "record-geometry-measurement":
            event.stop()
            try:
                profile_id = str(self.query_one("#geometry-monitor", Select).value)
                report = latest_geometry_report(self.app.local_config_root, profile_id, ruler_only=True)
                if report is None:
                    raise ValueError("Run a fullscreen geometry check first.")
                recorded = json.loads(report.read_text(encoding="utf-8"))
                if not diagnostic_matches_profile(recorded, self._profile()):
                    raise ValueError("Latest diagnostic belongs to a different profile revision. Launch a check for the selected revision before recording its measurement.")
                measured = float(self.query_one("#geometry-measured", Input).value)
                payload = record_geometry_measurement(
                    data_root=self.app.local_config_root,
                    report_file=report,
                    measured_length_mm=measured,
                    profile=self._profile(),
                )
                error = payload["measurement"]["error_percent"]
                status.update(f"[green]Measurement recorded and saved. Error: {error:+.2f}%[/green]")
                self.app.notify(f"Measurement saved; error {error:+.2f}%.", timeout=7)
                self._refresh_latest()
                self._refresh_stage_status()
                from ..config.calibration_workflow import advance_if_completed
                if self.active_calibration_stage == "geometry":
                    self.app.notify(
                        "Ruler measurement saved. Review the error, then choose Next stage → Spatial.",
                        timeout=9,
                    )
            except Exception as exc:
                status.update(f"[red]{exc}[/red]")
                self.app.notify(str(exc), title="Calibration action failed", severity="error", timeout=8)


class DataScreen(HubPage):
    page_title = "Data"

    def compose(self) -> ComposeResult:
        rows = self._rows()
        options = [
            (
                f"{row.get('date','')} · {row.get('participant_id','')} · "
                f"{row.get('experiment_id','')} · run_{int(row.get('run_number') or 0):03d} · "
                f"{row.get('status','')}",
                row.get("relative_path", ""),
            )
            for row in reversed(rows)
            if row.get("relative_path")
        ]
        if not options:
            options = [("No runs found in this workspace", "__none__")]

        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            yield Static("", id="data-status")
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]Acquisition data[/b]\n"
                f"Active external workspace: {self.app.data_root}\n"
                "Every run folder contains canonical trial records and its own analysis/ "
                "subfolder for staircase plots and versioned thresholds. "
                "Virtual runs also save scenario_report.json beside trials.tsv."
            )
            yield Select(options, value=options[0][1], allow_blank=False, id="data-run")
            yield Static("", id="data-details", classes="info-card")
            with Horizontal(classes="buttons wrap-buttons"):
                yield Button("Latest uncalibrated test manifest",id="inspect-presentation-manifest")
                yield Button("Latest uncalibrated test trials",id="inspect-presentation-trials")
            with Horizontal(classes="buttons wrap-buttons"):
                yield Button("Manifest", id="inspect-manifest")
                yield Button("Trials", id="inspect-trials")
                yield Button("Staircase state", id="inspect-adaptive")
            with Horizontal(classes="buttons wrap-buttons"):
                yield Button("Scenario report", id="inspect-scenario")
                yield Button("Open run folder", id="open-run-folder")
            yield Static("[b]Derived staircase threshold[/b]", classes="section-title")
            yield Label("How to select reversal observations (derived analysis only)")
            yield Select([
                ("Final fraction of reversals within each staircase", "fraction"),
                ("Last N reversals within each staircase", "count"),
            ], value="fraction", allow_blank=False, id="threshold-retention-mode")
            yield Label("Fraction (when fraction mode selected): allowed 0 < fraction ≤ 1")
            yield Input(value="0.80", id="threshold-fraction")
            yield Label("N final reversals (when count mode selected): positive whole number")
            yield Input(value="8", id="threshold-last-n")
            yield Label("Reversal contrast value")
            yield Select(
                [
                    ("Post-response / next display contrast (current legacy reversal basis)", "next_display_contrast"),
                    ("Presented display contrast", "presented_display_contrast"),
                ],
                value="next_display_contrast",
                allow_blank=False,
                id="threshold-column",
            )
            yield Button("Generate Threshold Table + Plot", id="analyse-threshold", variant="primary")
            yield Static("[b]Inspect saved trial staircases and quick-look figures[/b]", classes="section-title")
            with Horizontal(classes="buttons wrap-buttons"):
                yield Button("Generate staircase + THC previews", id="preview-figures")
                yield Button("Open staircase image", id="open-staircase-image")
                yield Button("Open THC image", id="open-threshold-image")
            yield Static(
                "Quick-look plots are derived from the canonical human or synthetic trial files. "
                "They do not change any accepted response, staircase value or original run. "
                "THC can be recalculated using final fraction or last N reversals.",
                classes="field-help",
            )
            yield Static(
                "Default convention: retain the final 80% of reversal values within each "
                "staircase, average those values to get a staircase threshold, then average "
                "staircase thresholds that share a condition. This is derived analysis only.",
                classes="field-help",
            )
        yield Footer()

    def _rows(self) -> list[dict[str, str]]:
        path = self.app.data_root / "runs_index.csv"
        if not path.exists():
            return []
        with path.open("r", newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _run_dir(self) -> Path:
        value = str(self.query_one("#data-run", Select).value)
        if value == "__none__":
            raise ValueError("No PsyCoLab acquisition run is available in this workspace.")
        path = (self.app.data_root / value).resolve()
        if not path.is_relative_to(self.app.data_root.resolve()):
            raise ValueError("Run path escapes the active data workspace.")
        return path

    def _refresh(self) -> None:
        try:
            run = self._run_dir()
            manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
            text = (
                f"[b]{run.relative_to(self.app.data_root)}[/b]\n"
                f"Participant: {manifest.get('participant_id', 'n/a')}\n"
                f"Experiment: {manifest.get('experiment_id', 'n/a')}\n"
                f"Data kind: {manifest.get('data_kind', 'human')}\n"
                f"Display: {manifest.get('monitor_profile_id', 'n/a')} · revision {manifest.get('monitor_profile', {}).get('revision', 'unknown')}\n"
                f"Profile SHA256: {manifest.get('monitor_profile_sha256', 'unrecorded')}\n"
                f"Status: {manifest.get('status', 'n/a')}\n"
                f"Accepted responses: {manifest.get('accepted_trials', 'n/a')}\n"
                f"Run UUID: {manifest.get('run_uuid', 'n/a')}"
            )
            summary_file = run / "analysis" / "staircase_preview.json"
            if summary_file.is_file():
                summary = json.loads(summary_file.read_text(encoding="utf-8"))
                text += (
                    f"\nStaircases plotted: {summary.get('staircases_plotted', 0)}"
                    f"\nStaircases per condition: {summary.get('condition_staircase_counts', {})}"
                    f"\nQuick-look figures: {run / 'analysis'}"
                )
        except Exception as exc:
            text = str(exc)
        self.query_one("#data-details", Static).update(text)

    def on_mount(self) -> None:
        self._refresh()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "data-run":
            self._refresh()

    def on_input_changed(self,event):
        if event.input.id not in ('threshold-fraction','threshold-last-n'): return
        import math
        try:
            value=float(event.input.value)
            valid=math.isfinite(value) and (0<value<=1 if event.input.id=='threshold-fraction' else value>0 and value.is_integer())
            if not valid: raise ValueError('Allowed fraction: (0,1]; reversal count: positive whole number. Entered value retained.')
            event.input.remove_class('invalid-input')
        except ValueError as exc:
            event.input.add_class('invalid-input'); self.query_one('#data-status',Static).update(str(exc))

    def _inspect(self, filename: str, title: str) -> None:
        run = self._run_dir()
        path = run / filename
        if not path.exists():
            raise ValueError(f"This run does not contain {filename}.")
        self.app.push_screen(CodeViewScreen(title=title, path=path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        status = self.query_one("#data-status", Static)
        try:
            if event.button.id in ('inspect-presentation-manifest','inspect-presentation-trials'):
                event.stop()
                root=self.app.local_config_root.parent/'psycolab_presentation_tests'
                from ..core.presentation_testing import MARKER
                if not (root/MARKER).is_file(): raise ValueError('No isolated uncalibrated presentation results exist yet.')
                candidates=[p for p in root.rglob('manifest.json') if not p.is_symlink() and p.resolve().is_relative_to(root.resolve()) and json.loads(p.read_text(encoding='utf-8')).get('data_kind')=='uncalibrated_presentation_test']
                if not candidates: raise ValueError('No uncalibrated presentation run is available.')
                manifest=max(candidates,key=lambda p:p.stat().st_mtime_ns)
                path=manifest if event.button.id=='inspect-presentation-manifest' else manifest.parent/'trials.tsv'
                self.app.push_screen(CodeViewScreen(title='UNCALIBRATED PRESENTATION TEST — NOT HUMAN DATA',path=path))
            elif event.button.id == "inspect-manifest":
                event.stop(); self._inspect("manifest.json", "Run manifest")
            elif event.button.id == "inspect-trials":
                event.stop(); self._inspect("trials.tsv", "Canonical accepted-response table")
            elif event.button.id == "inspect-scenario":
                event.stop(); self._inspect("scenario_report.json", "Synthetic scenario report and checks")
            elif event.button.id == "open-run-folder":
                event.stop()
                from .plots import open_run_directory
                open_run_directory(self.app.data_root, self._run_dir())
                status.update("Opened the selected run folder in the system file browser.")
            elif event.button.id == "inspect-adaptive":
                event.stop(); self._inspect("adaptive_session.json", "Saved staircase/adaptive state")
            elif event.button.id in {"analyse-threshold", "preview-figures"}:
                event.stop()
                from ..analysis.previews import create_staircase_preview
                preview = None
                if event.button.id == "preview-figures":
                    preview = create_staircase_preview(
                        data_root=self.app.data_root, run_directory=self._run_dir(),
                    )
                mode = str(self.query_one("#threshold-retention-mode", Select).value)
                last_n = int(self.query_one("#threshold-last-n", Input).value) if mode == "count" else None
                fraction = float(self.query_one("#threshold-fraction", Input).value) if mode == "fraction" else .80
                column = str(self.query_one("#threshold-column", Select).value)
                try:
                    result = analyse_thresholds(
                        data_root=self.app.data_root,
                        run_directory=self._run_dir(),
                        retain_fraction=fraction,
                        last_n_reversals=last_n,
                        reversal_value_column=column,
                        create_plot=True,
                    )
                except ValueError as exc:
                    if preview is None or "No reversal observations" not in str(exc):
                        raise
                    status.update(
                        "[yellow]Staircases plotted; no threshold estimate is possible yet.[/yellow]\n"
                        f"Staircase image: {preview.plot_file}\nReason: {exc}"
                    )
                    return
                plot_text = str(result.plot_file) if result.plot_file else "plot unavailable"
                status.update(
                    "[green]Exploratory derived figures created.[/green]\n"
                    + (f"Staircase image: {preview.plot_file}\n" if preview else "")
                    + f"THC plot: {plot_text}\n"
                    + f"Derived condition table: {result.condition_table}\n"
                    + f"Retention: {'last ' + str(last_n) + ' reversals' if last_n is not None else str(fraction) + ' fraction'}"
                )
            elif event.button.id in {"open-staircase-image", "open-threshold-image"}:
                event.stop()
                from ..analysis.previews import latest_staircase_plot, latest_threshold_plot
                from .plots import open_analysis_png
                plot = (latest_staircase_plot if event.button.id == "open-staircase-image"
                        else latest_threshold_plot)(
                    data_root=self.app.data_root, run_directory=self._run_dir(),
                )
                if plot is None:
                    raise ValueError("No saved PNG for this run. Choose Generate staircase + THC previews first.")
                open_analysis_png(self.app.data_root, plot)
                status.update(f"Opened derived figure: {plot}")
        except Exception as exc:
            status.update(f"[red]{exc}[/red]")


class HelpScreen(HubPage):
    page_title = "Help / Developer"

    def compose(self) -> ComposeResult:
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]PsyCoLab development map[/b]\n\n"
                "[b]Stimuli[/b] — what is presented. Reusable stimulus code belongs under "
                "src/psychophysics_lab/stimuli/.\n\n"
                "[b]Experiment procedures[/b] — how stimuli, timing, conditions and responses "
                "are combined. Build a procedure and ordered timeline; register the new module in "
                "src/psychophysics_lab/contributions.py.\n\n"
                "[b]Adaptive methods[/b] — how parameters change from accepted responses. "
                "Reusable algorithms live in adaptive/. Experiments declare the method and its controls.\n\n"
                "[b]Framework infrastructure[/b] — configuration, display profiles, lifecycle, "
                "recording and provenance.\n\n"
                "[b]Data rule[/b] — participant/acquisition data must stay outside this Git "
                "repository. The active workspace is validated by PsyCoLab before use.\n\n"
                "[b]Scientific rule[/b] — do not silently change stimulus mathematics, timings, "
                "response mappings, staircase rules, calibration semantics, contrast definitions "
                "or the retained 31.5 scaling. Such changes require explicit scientific review.\n\n"
                "The Build Experiments and Build Stimuli pages create a template and inspect source. This build "
                "also includes an extension guide/template, while intentionally avoiding an "
                "unrestricted source-code editor inside the acquisition TUI."
            )
            yield Static("[b]Start a contribution[/b]\nRun: python -m psychophysics_lab --scaffold my_task\nEdit the two generated stimuli/ and experiments/ files, then test and publish them in USER_env.\n\n[b]Human or virtual experiment[/b]\nUse Experiment → Configure → Review, then choose Run human experiment or Run simulation. The Scenarios page retains an advanced direct scenario runner.\nCLI alternative: python -m simulations --seed 123\nSaved under the same external data root using a reserved synthetic_ participant ID. No physical display or human participant is used. See docs/SIMULATION_TESTING.md.", classes="info-card")
            yield Button("Open researcher registration in editor", id="edit-contributions")
            yield Button("Open Extension Guide", id="view-extension-guide", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "edit-contributions":
            event.stop()
            self.app.inspect_source(self.app.repo_root / "src/psychophysics_lab/contributions.py")
        if event.button.id == "view-extension-guide":
            event.stop()
            path = self.app.repo_root / "docs" / "RESEARCHER_QUICKSTART.md"
            self.app.push_screen(CodeViewScreen(title="Extending PsyCoLab", path=path))


class ExperimentConfigScreen(Screen):
    def __init__(
        self,
        *,
        data_root: Path,
        participant_id: str,
        session_mode: str,
        experiment: ExperimentSpec,
        monitor_profile_id: str,
        defaults: dict[str, Any],
        review_return=None,
        focus_field: str | None = None,
    ) -> None:
        super().__init__()
        self.data_root = data_root
        self.participant_id = participant_id
        self.session_mode = session_mode
        self.experiment = experiment
        self.monitor_profile_id = monitor_profile_id
        self.defaults = dict(defaults)
        self.review_return = review_return
        self.focus_field = focus_field
        # Preserve historical pre-cpd workspaces explicitly when reusing.
        if (self.experiment.id == "contrast_sensitivity"
                and "condition_values" in self.defaults
                and "condition_unit" not in self.defaults):
            self.defaults["condition_unit"] = "legacy_shader_radians"

    def compose(self) -> ComposeResult:
        profile = self.app.monitor_profiles[self.monitor_profile_id]
        self.draft_key = (self.participant_id, self.experiment.id, self.monitor_profile_id)
        self.defaults.update(self.app.config_drafts.get(self.draft_key, {}))
        mapping = self.app.mapping_drafts.get(self.draft_key, {})
        self._mapping_requires_confirmation = bool(mapping.get("pending", False))
        self._mapping_manual = bool(mapping.get("manual", False))
        if mapping.get("identity"):
            self._mapping_identity = tuple(mapping["identity"])
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Back", id="back")
                yield Button("Change display / Calibrate", id="change-display")
                yield Button("Review", id="review", variant="primary")
            yield Static("", id="config-status")
            yield Static("", id="constraint-summary", markup=False)
        with VerticalScroll(id="config-body"):
            yield Static(
                f"[b]{self.experiment.display_name}[/b]\n{self.experiment.description}\n\n"
                + _monitor_summary(profile),
                id="experiment-description",
            )
            groups = {}
            from .stimulus_parameters import StimulusParametersPanel
            if self.experiment.stimulus_slots:
                yield Label("Stimulus Parameters")
                for slot in self.experiment.stimulus_slots:
                    yield StimulusParametersPanel(self, slot)
            controls = set(self.experiment.adaptive.controls) if self.experiment.adaptive else set()
            for field in self.experiment.fields:
                group = "Adaptive settings" if field.key in controls else field.section
                groups.setdefault(group, []).append(field)
            for group, fields in groups.items():
                with Collapsible(title=group, collapsed=group not in {"Experiment", "Display and contrast", "Stimulus conditions"}):
                    if group == "Adaptive settings":
                        yield Static("The experiment declares its adaptive method; these settings control this run.")
                    elif group == "Stimulus conditions":
                        yield Static(
                            "Enter the number of conditions and their comma-separated values. "
                            "They must match. Units are shown below and follow your selected mode.",
                            id="condition-unit-help", classes="field-help",
                        )
                    for field in fields:
                        if self.experiment.id == "contrast_sensitivity" and field.key == "Background_Luminance":
                            yield Label("Select background luminance and digital intensity from this monitor")
                            yield Select(
                                [("Manual entry (only when deliberately selected)", "manual")],
                                value="manual", allow_blank=False, id="background-mapping",
                            )
                            yield Static("", id="mapping-provenance", markup=False, classes="field-help")
                            yield Button("Review / repair saved luminance measurements", id="edit-background-calibration")
                        yield from self._compose_field(field)
                        yield Static("", id="domain-"+field.key.replace('_','-'), markup=False, classes="field-help")
                        if self.experiment.id == "contrast_sensitivity" and field.key == "starting_probe_intensity":
                            yield Static("", id="contrast-live-validation", markup=False, classes="field-help")
                    if group == "Adaptive settings" and self.experiment.adaptive.step_calculator:
                        from ..adaptive.steps import NOTICE
                        yield Static(NOTICE, classes="field-help")
                        yield Static("", id="step-status", markup=False)
            with Collapsible(title="Local presets", collapsed=True):
                yield Label("Saved local preset")
                presets = load_presets(self.app.local_config_root, self.experiment.id)
                yield Select([(name, name) for name in presets], id="config-preset")
                yield Button("Load preset", id="load-preset")
                yield Input(placeholder="New preset name", id="preset-name")
                yield Button("Save new preset", id="save-preset")
                yield Button("Update selected preset", id="update-preset")
        yield Footer()

    def on_mount(self):
        for group in self.query(Collapsible):
            if group.title == "Stimulus conditions":
                group.display = False  # Values remain the CSF adapter's authoritative fields.
        self._refresh_unit_help()
        self._refresh_contrast_help()
        self._refresh_constraints()
        self._refresh_mapping_choices()
        if self.focus_field:
            field = next(item for item in self.experiment.fields if item.key == self.focus_field)
            widget = self.query_one("#" + _field_widget_id(field))
            for parent in widget.ancestors:
                if isinstance(parent, Collapsible):
                    parent.collapsed = False
            self.call_after_refresh(widget.scroll_visible)
            self.call_after_refresh(widget.focus)

    def _refresh_mapping_choices(self):
        if not self.is_mounted or self.experiment.id != 'contrast_sensitivity':
            return
        from ..config.background_mapping import configuration_mapping_choices, background_provenance
        from ..config.calibration_dataset import dataset_hash, physical_snapshot
        profile = self.app.monitor_profiles[self.monitor_profile_id]
        selector = self.query_one('#background-mapping', Select)
        old_identity = getattr(self, '_mapping_identity', None)
        all_rows, dataset, state, source = configuration_mapping_choices(
            self.app.local_config_root, profile
        )
        # Full command 1.0 may define the measured luminance endpoint,
        # but is not a valid CSF background (the background must be < 1).
        self._all_mapping_rows = all_rows
        rows = [row for row in all_rows if 0 <= row['screen_intensity'] < 1]
        # The source and the actual physical setup are part of selection identity.
        # Notes-only revisions should not invalidate a selection.
        mapping_hash = dataset_hash(dataset) if dataset is not None else content_hash({
            "saved_pairs": [(p.screen_intensity, p.luminance_cdm2)
                            for p in profile.luminance_calibration],
            "physical_setup": physical_snapshot(profile),
        })
        identity = (profile.id, profile.profile_uuid, source, mapping_hash)
        self._mapping_rows = rows
        self._mapping_identity = identity
        selected = 'manual'
        intensity = luminance = None
        try:
            intensity = float(self.query_one('#field-Background-Screen-intensity', Input).value)
            luminance = float(self.query_one('#field-Background-Luminance', Input).value)
            selected = next((str(i) for i, point in enumerate(rows)
                             if point['screen_intensity'] == intensity
                             and point['luminance_cdm2'] == luminance), 'manual')
        except (ValueError, TypeError):
            pass
        if old_identity is not None and old_identity != identity:
            self._mapping_requires_confirmation = True
        pending = getattr(self, '_mapping_requires_confirmation', False)
        options = [('Manual entry — retain or edit values independently', 'manual')]
        if pending:
            options.insert(0, ('DISPLAY/CALIBRATION CHANGED — explicitly choose a new pair or Manual', 'confirm'))
            selected = 'confirm'
        elif getattr(self, '_mapping_manual', False):
            selected = 'manual'
        if rows:
            prefix = 'TEST ONLY — profile-stored, unverified: ' if source == 'profile_only' else ''
            options += [(f"{prefix}{p['luminance_cdm2']:g} cd/m² — intensity {p['screen_intensity']:g}",
                         str(i)) for i, p in enumerate(rows)]
        with self.prevent(Select.Changed):
            selector.set_options(options)
            selector.value = selected
        # Linked selection is the normal control. Manual inputs become editable
        # only after deliberately choosing Manual (or for an unmatched old draft).
        linked = selected not in ('manual', 'confirm')
        self.query_one('#field-Background-Screen-intensity', Input).disabled = linked
        self.query_one('#field-Background-Luminance', Input).disabled = linked
        text = state + '\nSelect a saved pair to set BOTH fields. Repeated readings contribute to one mean; no interpolation. Starting probe intensity is independent.'
        if source == 'profile_only':
            text += '\nThese values come from a saved, UNVERIFIED profile summary, not a matching active raw dataset. Repair calibration before human acquisition.'
        if not rows:
            text += '\nNo usable calibrated choices. Choose Manual for tests, or review/repair this monitor’s luminance dataset.'
        if pending:
            text += '\nPrevious experimental values were retained. Select a current pair or choose Manual explicitly before Review.'
        elif intensity is not None and luminance is not None:
            evidence = background_provenance(
                self.app.local_config_root, profile,
                {'Background_Screen_intensity': intensity, 'Background_Luminance': luminance},
            )
            text += f"\nCurrent: {luminance:g} cd/m² — Digital intensity {intensity:g}. "
            if linked and source == 'active':
                text += 'Exact saved mean pair; physical verification depends on the source evidence.'
            elif linked:
                text += 'PROFILE-ONLY TEST PAIR — not calibrated or physically verified.'
            else:
                text += 'Manual / unmatched pair. Use the selector for a saved pair.'
        self.query_one('#mapping-provenance', Static).update(text)

    def _refresh_constraints(self):
        if not self.is_mounted: return
        from ..config.input_constraints import experiment_constraints
        raw={field.key:self.query_one("#"+_field_widget_id(field)).value for field in self.experiment.fields}
        profile=self.app.monitor_profiles[self.monitor_profile_id]
        reports,errors=experiment_constraints(self.experiment,profile,raw)
        for field in self.experiment.fields:
            report=reports[field.key]; widget=self.query_one("#"+_field_widget_id(field))
            widget.set_class(bool(report['error']),"invalid-input")
            widget.tooltip=report['domain']+"\n"+report['error']
            self.query_one("#domain-"+field.key.replace('_','-'),Static).update(report['domain']+("\nINVALID: "+report['error'] if report['error'] else ""))
        self.query_one('#constraint-summary',Static).update("\n".join(errors))
        # Shader range affects human/test launch, but does not block numerical simulation Review.
        # Submission runs the same validator again; retaining an enabled button
        # avoids stale disabled state between the last keystroke and its event.
        # Invalid values cannot be committed by _collect/validate_setup.

    def _refresh_contrast_help(self):
        if not self.is_mounted or self.experiment.id != "contrast_sensitivity":
            return
        try:
            from ..stimuli.contrast_validation import contrast_limit_text
            fields = {field.key:field for field in self.experiment.fields}
            def value(key):
                return float(self.query_one("#" + _field_widget_id(fields[key]), Input).value)
            message = contrast_limit_text(value("Background_Screen_intensity"), value("starting_probe_intensity"), value("logUNIT_UP"))
        except (ValueError, TypeError) as exc:
            message = f"Contrast range requires valid numeric inputs: {exc}"
        self.query_one("#contrast-live-validation", Static).update(message)

    def _refresh_unit_help(self):
        if self.experiment.id != "contrast_sensitivity" or not self.is_mounted:
            return
        unit = self.query_one("#field-condition-unit", Select).value
        messages = {"cycles_per_degree": "Conditions are spatial frequencies in cycles/degree (cpd), e.g. 2,4,8. Derived from measured display geometry; not photometrically verified.",
            "degrees_per_cycle": "Conditions are periods in degrees/cycle, e.g. 0.5,0.25,0.125. Stored trial frequencies are their reciprocals in cycles/degree.",
            "legacy_shader_radians": "Explicit historical shader phase values, e.g. 63,252. These are uncalibrated scalars and must never be relabelled cycles/degree."}
        self.query_one("#condition-unit-help", Static).update(messages.get(str(unit), "Select spatial-frequency units."))

    def on_screen_resume(self):
        if not hasattr(self, "draft_key"):
            return
        applied = getattr(self, "applied_review_values", None)
        if applied is not None:
            self.applied_review_values = None
            for field in self.experiment.fields:
                if field.key in applied:
                    value = applied[field.key]
                    self.query_one("#" + _field_widget_id(field)).value = value if field.kind == "choice" else str(value)
            self._refresh_contrast_help()
        current = self.app.monitor_profiles.get(self.monitor_profile_id)
        if current is not None:
            self.query_one("#experiment-description", Static).update(
                f"[b]{self.experiment.display_name}[/b]\n{self.experiment.description}\n\n" +
                _monitor_summary(current) + "\n" + readiness_text(self.experiment, current, self.app.repo_root))
        self._refresh_unit_help()
        self._refresh_constraints()
        self._refresh_mapping_choices()

    def _save_calibration_draft(self):
        save_preferences(self.app.local_config_root, active_monitor_profile_id=self.monitor_profile_id, calibration_experiment_draft={
            "participant": self.participant_id, "experiment": self.experiment.id,
            "profile": self.monitor_profile_id, "values": dict(self.app.config_drafts[self.draft_key]),
            "background_selection": dict(self.app.mapping_drafts.get(self.draft_key, {}))})

    def _apply_display(self, profile_id):
        if profile_id not in self.app.monitor_profiles:
            raise ValueError("Selected display is no longer available; reload profiles.")
        self.remember_draft()
        draft = dict(self.app.config_drafts[self.draft_key])
        self.monitor_profile_id = profile_id
        self.draft_key = (self.participant_id, self.experiment.id, profile_id)
        self.app.config_drafts[self.draft_key] = draft
        self.on_screen_resume()
        self.remember_draft()
        self._save_calibration_draft()
        self.query_one("#config-status", Static).update("Display changed. Draft experiment values retained; Review revalidates against this profile.")

    def _compose_field(self, field):
        yield Label(field.label)
        value = self.defaults.get(field.key, field.default)
        widget_id = _field_widget_id(field)
        if field.kind == "choice":
            options = [(str(choice), choice) for choice in field.choices]
            kwargs = {"id": widget_id, "allow_blank": field.default is None}
            if value is not None:
                kwargs["value"] = value
            yield Select(options, disabled=not field.editable, **kwargs)
        else:
            with Horizontal(classes="field-row"):
                yield Input(value="" if value is None else str(value), id=widget_id, disabled=not field.editable)
                if self.experiment.adaptive and self.experiment.adaptive.step_calculator:
                    if field.key == "logUNIT_UP":
                        yield Button("From down", id="calculate-up", disabled=not field.editable)
                    elif field.key == "logUNIT_DW":
                        yield Button("From up", id="calculate-down", disabled=not field.editable)
        if field.help_text:
            yield Static(field.help_text, classes="field-help")

    def _calculate_step(self, direction):
        from ..adaptive.steps import paired_step
        fields = {field.key: field for field in self.experiment.fields}
        def value(key):
            return fields[key].coerce(self.query_one("#" + _field_widget_id(fields[key]), Input).value)
        selection = self.experiment.adaptive
        target = "logUNIT_UP" if direction == "up" else "logUNIT_DW"
        known = "logUNIT_DW" if direction == "up" else "logUNIT_UP"
        if not fields[target].editable:
            raise ValueError("This experiment fixes the requested step size.")
        result = paired_step(known_value=value(known), calculate=direction,
            n_down=value("n_down"), n_up=value("n_up"),
            alternatives=len(self.experiment.response_paradigm.alternatives) if self.experiment.response_paradigm else None,
            parameterization=selection.step_parameterization)
        self.query_one("#" + _field_widget_id(fields[target]), Input).value = repr(result)
        self.remember_draft()
        return f"Calculated {direction} = {result:.8g} log10 units. Review this opt-in setting before starting."

    def remember_draft(self) -> None:
        raw = {}
        for field in self.experiment.fields:
            widget = self.query_one("#" + _field_widget_id(field))
            value = widget.value
            raw[field.key] = None if _is_blank_select_value(value) else value
        self.app.config_drafts[self.draft_key] = raw
        self.app.mapping_drafts[self.draft_key] = {
            "pending": bool(getattr(self, "_mapping_requires_confirmation", False)),
            "manual": bool(getattr(self, "_mapping_manual", False)),
            "identity": getattr(self, "_mapping_identity", None),
        }

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_contrast_help()
        self._refresh_constraints()
        if event.input.id in {'field-Background-Screen-intensity', 'field-Background-Luminance'}:
            self._refresh_mapping_choices()
        if hasattr(self, "draft_key"):
            self.remember_draft()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == 'background-mapping':
            if event.value != event.select.value:
                return  # Ignore queued events from a replaced option list.
            if _is_blank_select_value(event.value) or event.value == 'confirm':
                return
            self._mapping_requires_confirmation = False
            self._mapping_manual = event.value == 'manual'
            if event.value != 'manual':
                point = self._mapping_rows[int(str(event.value))]
                with self.prevent(Input.Changed):
                    self.query_one('#field-Background-Screen-intensity', Input).value = repr(point['screen_intensity'])
                    self.query_one('#field-Background-Luminance', Input).value = repr(point['luminance_cdm2'])
                    endpoint = next((p for p in self._all_mapping_rows if p['screen_intensity'] == 1), None)
                    if endpoint is not None:
                        self.query_one('#field-Max-monitor-Luminance', Input).value = repr(endpoint['luminance_cdm2'])
            self._refresh_mapping_choices()
            self._refresh_contrast_help()
        if hasattr(self, "draft_key"):
            self.remember_draft()
            self._refresh_unit_help()
            self._refresh_constraints()

    def _collect(self) -> dict[str, Any]:
        if getattr(self, '_mapping_requires_confirmation', False):
            raise ValueError("Display or mapping changed. Select a saved background pair or explicitly select Manual before Review.")
        values: dict[str, Any] = {}
        for field in self.experiment.fields:
            widget_id = _field_widget_id(field)
            if field.kind == "choice":
                raw = self.query_one(f"#{widget_id}", Select).value
                if _is_blank_select_value(raw):
                    raw = None
            else:
                raw = self.query_one(f"#{widget_id}", Input).value
            values[field.key] = field.coerce(raw)
        values = self.experiment.normalise_values(values)
        from .stimulus_parameters import StimulusParametersPanel
        self.stimulus_snapshots = {panel.slot: panel.current() for panel in self.query(StimulusParametersPanel)}

        profile = self.app.monitor_profiles[self.monitor_profile_id]
        request = SetupRequest(self.participant_id, self.session_mode, self.experiment.id,
            self.monitor_profile_id, values, stimulus_snapshots=self.stimulus_snapshots)
        return validate_setup(request, self.experiment, profile, mode="configuration").experiment_values

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "edit-background-calibration":
            event.stop()
            self.remember_draft()
            self._save_calibration_draft()
            profile = self.app.monitor_profiles[self.monitor_profile_id]
            try:
                from ..config.calibration_dataset import load_active
                load_active(self.app.local_config_root, profile)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                # Even an unreadable raw dataset must not trap the user here.
                self.app.display_guide_target_profile_id = profile.id
                self.app.display_draft["geometry-monitor"] = profile.id
                save_preferences(self.app.local_config_root, calibration_active_stage="luminance")
                self.app.push_screen(DisplayCheckScreen())
                self.query_one("#config-status", Static).update(
                    "Luminance data need repair in Calibrate → Luminance: " + str(exc)
                )
            else:
                from .luminance_data import open_luminance_editor
                error = open_luminance_editor(self.app, profile, experiment_id=self.experiment.id)
                if error:
                    self.query_one("#config-status", Static).update(error)
            return
        if event.button.id == "change-display":
            event.stop()
            self.remember_draft()
            self._save_calibration_draft()
            self.app.push_screen(ChangeDisplayScreen(self))
            return
        if event.button.id in {"calculate-up", "calculate-down"}:
            event.stop()
            try:
                message = self._calculate_step(event.button.id.removeprefix("calculate-"))
            except (ValueError, TypeError, KeyError) as exc:
                message = str(exc)
            self.query_one("#step-status", Static).update(message)
            self.query_one("#config-status", Static).update(message)
            return
        if event.button.id in {"save-preset", "load-preset", "update-preset"}:
            event.stop()
            operation = event.button.id
            verb = {"save-preset": "saved", "load-preset": "loaded",
                    "update-preset": "updated"}[operation]
            try:
                all_presets = load_presets(self.app.local_config_root, self.experiment.id)
                if operation == "save-preset":
                    name = self.query_one("#preset-name", Input).value
                    if name in all_presets:
                        raise ValueError(
                            f"Preset '{name}' already exists. Choose a new name or "
                            "select it and press Update selected preset."
                        )
                    snapshot = self._collect()
                    saved_path = save_preset(self.app.local_config_root, name, self.experiment.id, snapshot)
                    loaded = load_presets(self.app.local_config_root, self.experiment.id).get(name)
                    if loaded != snapshot:
                        raise RuntimeError(f"Preset save could not be verified: {saved_path}")
                    selector = self.query_one("#config-preset", Select)
                    selector.set_options([(item, item) for item in load_presets(
                        self.app.local_config_root, self.experiment.id
                    )])
                    selector.value = name
                elif operation == "update-preset":
                    raw = self.query_one("#config-preset", Select).value
                    if _is_blank_select_value(raw) or str(raw) not in all_presets:
                        raise ValueError("Select an existing preset before updating it.")
                    name = str(raw)
                    snapshot = self._collect()
                    from ..config.local import update_preset
                    saved_path = update_preset(self.app.local_config_root, name,
                                               self.experiment.id, snapshot)
                    if load_presets(self.app.local_config_root, self.experiment.id).get(name) != snapshot:
                        raise RuntimeError(f"Updated preset could not be verified: {saved_path}")
                else:
                    raw = self.query_one("#config-preset", Select).value
                    if _is_blank_select_value(raw):
                        raise ValueError("Select a saved preset first.")
                    name = str(raw)
                    if name not in all_presets:
                        raise ValueError("The selected preset no longer exists. Reload the screen.")
                    values = self.experiment.normalise_values(all_presets[name])
                    values = validate_setup(SetupRequest(self.participant_id, self.session_mode,
                        self.experiment.id, self.monitor_profile_id, values), self.experiment,
                        self.app.monitor_profiles[self.monitor_profile_id], mode="configuration").experiment_values
                    for field in self.experiment.fields:
                        self.query_one("#" + _field_widget_id(field)).value = (
                            values[field.key] if field.kind == "choice" else str(values[field.key])
                        )
                    self.remember_draft()
                    self._mapping_manual = False
                    self._refresh_mapping_choices()
                notice = f"Preset '{name}' {verb} successfully."
                self.query_one("#config-status", Static).update(f"[green]{notice}[/green]")
                self.app.notify(notice, title=f"Preset {verb}", timeout=6)
            except (ValueError, KeyError, OSError, RuntimeError, TypeError) as exc:
                message = f"Preset NOT {verb}: {exc}"
                self.query_one("#config-status", Static).update(f"[red]{message}[/red]")
                self.app.notify(message, severity="error", timeout=8)
            return
        button_id = event.button.id
        if button_id not in {"back", "review"}:
            return
        event.stop()
        if button_id == "back":
            self.app.pop_screen()
            return

        status = self.query_one("#config-status", Static)
        try:
            values = self._collect()
            request = SetupRequest(
                participant_id=self.participant_id,
                session_mode=self.session_mode,
                experiment_id=self.experiment.id,
                monitor_profile_id=self.monitor_profile_id,
                experiment_values=values,
                data_root=str(self.data_root),
                stimulus_snapshots=self.stimulus_snapshots,
            )
            request = validate_setup(request, self.experiment, self.app.monitor_profiles[self.monitor_profile_id], mode="configuration")
            self.remember_draft()
            if self.review_return is not None:
                for screen in self.app.screen_stack:
                    if isinstance(screen, ExperimentConfigScreen) and screen is not self and screen.draft_key == self.draft_key:
                        screen.applied_review_values = dict(values)
                self.review_return.request = request
                self.review_return.reviewed_profile_snapshot = self.app.monitor_profiles[request.monitor_profile_id].to_dict()
                self.app.pop_screen()
            else:
                self.app.push_screen(ReviewScreen(request=request))
        except Exception as exc:
            status.update(f"[red]{exc}[/red]")
            self.app.notify(str(exc), title="Review blocked: check inputs", severity="error", timeout=8)
            if not isinstance(exc, (ValueError, KeyError)):
                _report_ui_exception(self.app, exc, phase="tui_experiment_config_review")


class ChangeDisplayScreen(Screen):
    """A reversible display choice; calibration edits are explicitly saved revisions."""
    def __init__(self, configuration):
        super().__init__()
        self.configuration = configuration

    def compose(self):
        with Vertical(id="fixed-shell"):
            yield Header()
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="display-cancel")
                yield Button("Refresh profiles", id="display-refresh")
                yield Button("Calibrate", id="display-calibrate")
                yield Button("Apply display", id="display-apply", variant="primary")
            yield Static("", id="display-choice-status")
        with VerticalScroll(classes="page-body"):
            yield Label("Available display profiles (qualification does not hide a profile)")
            yield Select([(f"{p.display_name} [{p.id} · rev {p.revision}]", p.id)
                for p in self.app.monitor_profiles.values()], value=self.configuration.monitor_profile_id,
                allow_blank=False, id="display-choice")
            yield Static("", id="display-choice-summary")
            yield Static("Apply retains your experiment draft and requires a new Review. Cancel leaves the selected display unchanged. Profile revisions saved in Calibrate persist independently.")
        yield Footer()

    def on_mount(self):
        self._refresh()

    def _refresh(self):
        selected = self.query_one("#display-choice", Select).value
        if selected in self.app.monitor_profiles:
            p = self.app.monitor_profiles[selected]
            self.query_one("#display-choice-summary", Static).update(
                _monitor_summary(p) + "\n" + readiness_text(self.configuration.experiment, p, self.app.repo_root))

    def on_screen_resume(self):
        selected = preferences(self.app.local_config_root).get("active_monitor_profile_id")
        selector = self.query_one("#display-choice", Select)
        previous = selector.value
        selector.set_options([(f"{p.display_name} [{p.id} · rev {p.revision}]", p.id) for p in self.app.monitor_profiles.values()])
        selector.value = selected if selected in self.app.monitor_profiles else previous
        self._refresh()

    def on_select_changed(self, event):
        if self.is_mounted:
            self._refresh()

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == "display-cancel":
            self.app.pop_screen()
        elif event.button.id == "display-apply":
            self.configuration._apply_display(str(self.query_one("#display-choice", Select).value))
            self.app.pop_screen()
        elif event.button.id == "display-refresh":
            self.app.reload_profiles()
            self.on_screen_resume()
        elif event.button.id == "display-calibrate":
            page = DisplayCheckScreen()
            page.return_to_configuration = True
            self.app.push_screen(page)


class ReviewScreen(Screen):
    def __init__(self, *, request: SetupRequest) -> None:
        super().__init__()
        self.request = request
        self.reviewed_profile_snapshot = None

    def compose(self) -> ComposeResult:
        experiment = get_experiment(self.request.experiment_id)
        profile = self.app.monitor_profiles[self.request.monitor_profile_id]
        self.reviewed_profile_snapshot = profile.to_dict()
        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            yield Label("What would you like to run?")
            yield Select([
                ("Test experiment presentation on the real display", "test"),
                ("Human experiment — verified laboratory acquisition", "human"),
                ("Simulation — virtual observer", "simulation"),
            ], value=self.app.run_intent, allow_blank=False, id="review-run-intent")
            with Horizontal(classes="buttons"):
                yield Button("Back", id="back")
                yield Button("Start uncalibrated test presentation", id="run-presentation-test", variant="warning")
                yield Button("Run human experiment", id="run", variant="success")
                yield Button("Run simulation", id="run-simulation", variant="primary")
            yield Button("Resolve human acquisition requirements",
                         id="review-calibration-guide")
            yield Static("", id="review-status")
        with VerticalScroll(id="review-body"):
            yield Static("", id="selected-run-readiness", markup=False, classes="info-card")
            with Vertical(id="human-review-checks"):
                yield Static("[b]Human Experiment Readiness[/b]", classes="section-title")
                yield Static("", id="human-readiness-summary", markup=False, classes="info-card")
                yield Static("", id="human-next-action", markup=False, classes="info-card readiness-next")
                yield Button("Open the next required check", id="review-next-action", variant="warning")
                yield Static("", id="human-checklist", markup=False, classes="info-card")
                from ..config.human_readiness import experiment_readiness, human_readiness_checklist
                report = experiment_readiness(self.request, experiment, profile, repo_root=self.app.repo_root)
                ordered_rows = human_readiness_checklist(report) + [
                    row for row in report["requirements"] if not row.get("required")]
                for row in ordered_rows:
                    yield Static("", id="readiness-" + row["key"], classes="info-card")
                    if row.get("action"):
                        yield Button(row["action"], id="resolve-" + row["key"])
            with Collapsible(title="Advanced — run settings and technical preflight", collapsed=True):
                yield Static(self._summary_text(experiment, profile), id="review-text")
                yield Static("", id="readiness-technical", markup=False)
        yield Footer()

    def _summary_text(self, experiment, profile):
        prospective = _prospective_run_path(self.request, experiment, profile)
        lines = [
            "[b]Review experiment[/b]",
            "",
            f"External data workspace: {self.request.data_root}",
            f"Participant: {self.request.participant_id}",
            (
                "Setup: Reuse last settings (this still creates a new run)"
                if self.request.session_mode == "reuse"
                else "Setup: Start from experiment defaults / new settings"
            ),
            f"Experiment: {experiment.display_name}",
            f"Display: {profile.display_name} [{profile.id}]",
            _monitor_summary(profile),
            f"Calibration status: {profile.calibration_status}",
            f"Profile revision: {profile.revision} · SHA256: {content_hash(profile.to_dict())}",
            f"Display binding: {profile.display_binding or 'legacy primary display; verify before acquisition'}",
            f"Geometry: {profile.geometry_status}; timing: {profile.timing_status}",
            "",
            "[b]Expected run location[/b]",
            prospective,
            "(run_NNN is allocated safely when acquisition starts)",
            "",
            "[b]Experiment parameters[/b]",
        ]
        for field in experiment.fields:
            lines.append(f"{field.label}: {self.request.experiment_values[field.key]}")

        if self.request.experiment_id == "contrast_sensitivity":
            values = self.request.experiment_values
            down, up, reversals = values["n_down"], values["n_up"], values["reversal_termination"]
            count = values["number_conditions"] * values["staircases_per_condition"]
            from ..experiments.contrast_sensitivity import resolved_condition_frequencies
            frequencies = resolved_condition_frequencies(values["condition_values"], values["condition_unit"])
            lines.append(
                f"Entered conditions: {values['condition_values']} "
                f"({values['condition_unit']}); {count} independent staircases in total."
            )
            if values["condition_unit"] != "legacy_shader_radians":
                lines.append(f"Resolved spatial frequencies: {', '.join(f'{x:g}' for x in frequencies)} cycles/degree.")
                from ..stimuli.spatial_calibration import resolve_spatial_geometry, validate_requested_cpd
                if profile.expected_resolution_px:
                    calibration = resolve_spatial_geometry(profile, profile.expected_resolution_px)
                    lines.extend([
                        f"Local pixels/degree at gaze: X={calibration.pixels_per_degree_at_centre[0]:.3f}, Y={calibration.pixels_per_degree_at_centre[1]:.3f}",
                        f"Nyquist limit: X={calibration.nyquist_cpd_at_centre[0]:.3f}, Y={calibration.nyquist_cpd_at_centre[1]:.3f} cpd",
                        f"Display geometric verification: {profile.geometry_status}",
                    ])
                else:
                    lines.append("[yellow]The profile has no saved expected pixel resolution. "
                                 "Set it in Calibrate → Edit profile before relying on physical units. "
                                 "The renderer will check actual fullscreen resolution at launch.[/yellow]")
            lines.append(
                f"Introductory rule: 1-down until first incorrect response or "
                f"{values['initial_one_down_limit']} accepted responses per staircase "
                f"(0 disables)."
            )
            # A rough warning, NOT a mathematical lower bound once an
            # introductory 1-down phase is enabled. The response ceiling is
            # global; every staircase needs at least one response.
            if values["max_trials"] < count:
                lines.append(
                    f"[yellow]The shared maximum of {values['max_trials']} responses "
                    f"is below the {count} independent staircase count. At least "
                    f"one staircase cannot receive any response.[/yellow]"
                )
            elif values["initial_one_down_limit"] == 0:
                estimate = count * (min(down, up) + ((reversals+1)//2)*max(down, up) + (reversals//2)*min(down, up))
                if values["max_trials"] < estimate:
                    lines.append(
                        f"[yellow]The global response ceiling {values['max_trials']} "
                        f"is below an indicative {estimate}-response alternating-step "
                        f"budget for {count} staircases. Some may end unfinished.[/yellow]"
                    )
        lines.extend(
            [
                "",
                "A new self-contained run folder will be created. Canonical accepted responses "
                "are appended to trials.tsv; compatibility files and provenance snapshots are "
                "retained according to the existing acquisition contract.",
            ]
        )

        return "\n".join(lines)

    def on_mount(self):
        self._refresh_readiness()
        self._apply_run_intent()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "review-run-intent" and self.is_mounted:
            if event.value in ("test", "human", "simulation"):
                self.app.run_intent = str(event.value)
                self._apply_run_intent()

    def _apply_run_intent(self) -> None:
        if not self.is_mounted:
            return
        intent=self.app.run_intent
        self.query_one("#human-review-checks", Vertical).display = intent=="human"
        # Keep alternative actions reachable from existing saved Review screens
        # and keyboard workflows. Highlight the selected mode, but do not hide
        # or disable the other safe entry points; each still runs its own strict
        # preflight at invocation.
        for action, mode in (("run-presentation-test","test"),
                             ("run-simulation","simulation"),("run","human")):
            button=self.query_one("#" + action, Button)
            button.display=True
            button.variant=("warning" if mode=="test" else
                            "success" if mode=="human" else "primary") if mode==intent else "default"
        self.query_one("#review-calibration-guide", Button).display=True
        report=self.readiness_report
        if intent=="human":
            status=("READY for human acquisition — final hardware preflight still applies."
                    if report["human_ready"] else
                    f"Human acquisition requires {len(report['blockers'])} more item(s). "
                    "Use the actions below to resolve them.")
        elif intent=="simulation":
            status=("READY to simulate using the registered virtual observer."
                    if report["simulation_available"] else
                    "Simulation unavailable for these settings; revise the experiment configuration.")
        else:
            from ..config.preflight import human_requirements
            profile=self.app.monitor_profiles.get(self.request.monitor_profile_id)
            if profile is None:
                status="TEST BLOCKED — selected display is unavailable. Select a current monitor."
            else:
                needed=[row for row in human_requirements(
                    get_experiment(self.request.experiment_id),profile,
                    self.request.experiment_values)
                    if row["key"] in ("binding","sampling","contrast") and not row["passed"]]
                status=("READY FOR TEST PRESENTATION — physical photometry and human qualification "
                        "are not needed. Fullscreen mode and digital safety are checked at launch."
                        if not needed else
                        "TEST SETUP NEEDS ATTENTION: " + "; ".join(row["detail"] for row in needed))
        self.query_one("#selected-run-readiness", Static).update(status)

    def on_screen_resume(self):
        if not self.is_mounted:
            return
        from dataclasses import replace
        self.app.reload_profiles()
        profile = self.app.monitor_profiles.get(self.request.monitor_profile_id)
        if profile is not None and self.reviewed_profile_snapshot is not None:
            from ..config.readiness import _DIAGNOSTIC_PHYSICAL_FIELDS
            current = profile.to_dict()
            # An explicit return from review controls refreshes metadata-only
            # revisions. Changed physical arrangements require a new Review.
            same = all(current.get(key) == self.reviewed_profile_snapshot.get(key) for key in
                       (*_DIAGNOSTIC_PHYSICAL_FIELDS, "id", "profile_uuid"))
            if same:
                candidate = replace(self.request, monitor_profile_hash=None)
                try:
                    self.request = validate_setup(candidate, get_experiment(candidate.experiment_id), profile, mode="configuration")
                except (ValueError, TypeError):
                    pass
                else:
                    self.reviewed_profile_snapshot = current
        self._refresh_readiness()

    def _refresh_readiness(self):
        if not self.is_mounted:
            return
        from ..config.human_readiness import experiment_readiness
        profile = self.app.monitor_profiles.get(self.request.monitor_profile_id)
        if profile is None:
            self.query_one("#human-readiness-summary", Static).update("Human experiment: Blocked. Selected monitor unavailable; restore it in Display. No fallback selected.")
            return
        self.readiness_report = experiment_readiness(self.request, get_experiment(self.request.experiment_id), profile, repo_root=self.app.repo_root)
        report = self.readiness_report
        count = len(report["blockers"])
        self.query_one("#review-text", Static).update(self._summary_text(get_experiment(self.request.experiment_id), profile))
        self.query_one("#human-readiness-summary", Static).update(
            ("Human experiment: Ready (final launch checks still apply)" if report["human_ready"] else f"Human acquisition blocked — {count} requirements outstanding")
            + "\nSimulation: " + ("Available" if report["simulation_available"] else "Unavailable")
            + "\nGreen calibration pages record saved observations; physical verification is a separate laboratory declaration.")
        from ..config.human_readiness import next_human_requirement, human_readiness_checklist
        next_row = next_human_requirement(report)
        self.next_requirement_key = next_row["key"] if next_row else None
        button = self.query_one("#review-next-action", Button)
        button.disabled = next_row is None
        button.label = (next_row["action"] or "Open next check") if next_row else "All required checks complete"
        step_count = len(report["blockers"])
        self.query_one("#human-next-action", Static).update(
            ("NEXT REQUIRED ACTION — " + next_row["name"] + "\n"
             + (next_row.get("action") or "Review the corresponding requirement") + "\n"
             + next_row["detail"] if next_row else
             "All required checks are complete. Final launch checks still apply.")
        )
        checks = human_readiness_checklist(report)
        self.query_one("#human-checklist", Static).update(
            "HUMAN ACQUISITION CHECKLIST — in the order to complete it\n"
            + "\n".join(("☑ " if row["passed"] else "□ ") +
                        row["name"] + (" — complete" if row["passed"] else
                        " — NEXT" if next_row and row["key"] == next_row["key"] else " — outstanding")
                        for row in checks)
            + ("\n\n" + str(step_count) + " required check(s) remaining." if step_count else
               "\n\nAll required checklist items complete.")
        )
        for row in report["requirements"]:
            matches = self.query("#readiness-" + row["key"])
            if matches:
                widget = matches.first()
                for cls in ("readiness-blocked","readiness-done","readiness-next","readiness-optional"):
                    widget.remove_class(cls)
                widget.add_class("readiness-next" if next_row is not None and row["key"] == next_row["key"]
                                 else "readiness-blocked" if row["required"] and not row["passed"]
                                 else "readiness-done" if row["required"] else "readiness-optional")
                color = "green" if row["passed"] and row["required"] else "yellow" if not row["required"] else "red"
                widget.update(f"[{color}][b]{row['name']}: {row['status']}[/b][/] "
                    + ("Required for human acquisition" if row["required"] else "Recommended / informational") + "\n" + row["detail"])
            action = self.query("#resolve-" + row["key"])
            if action and row.get("action"):
                action.first().label = row["action"]
        self.query_one("#readiness-technical", Static).update(
            "\n\n".join(row["detail"] for row in report["blockers"]) + "\n\n" + report["simulation_detail"])
        self.query_one("#run-simulation", Button).disabled = not report["simulation_available"]
        self._apply_run_intent()

    def resolve_requirement(self, key):
        # Fullscreen diagnostics restart the app; preserve the exact experiment draft.
        self.app.config_drafts[(self.request.participant_id,self.request.experiment_id,self.request.monitor_profile_id)] = dict(self.request.experiment_values)
        save_preferences(self.app.local_config_root, active_monitor_profile_id=self.request.monitor_profile_id,
            calibration_experiment_draft={"participant":self.request.participant_id,"experiment":self.request.experiment_id,
                "profile":self.request.monitor_profile_id,"values":dict(self.request.experiment_values)})
        row = next(item for item in self.readiness_report["requirements"] if item["key"] == key)
        profile = self.app.monitor_profiles[self.request.monitor_profile_id]
        if key == "luminance" and row.get("destination") == "calibration":
            from .luminance_data import open_luminance_editor
            error = open_luminance_editor(self.app, profile, experiment_id=self.request.experiment_id)
            if error:
                self.query_one('#review-status', Static).update(error)
                self.app.notify(error, title="Luminance data need inspection", severity="warning", timeout=12)
            return
        if row["destination"] in {"verification", "qualification"}:
            from .calibration_review import PhysicalVerificationScreen, ExperimentQualificationScreen
            cls = PhysicalVerificationScreen if row["destination"] == "verification" else ExperimentQualificationScreen
            kwargs = {"experiment_id":self.request.experiment_id}
            if row["destination"] == "verification":
                kwargs["focus_category"] = "calibration_status" if key=="luminance" else key+"_status"
            else:
                kwargs["values"] = self.request.experiment_values
            self.app.push_screen(cls(profile, **kwargs))
        elif row["destination"] == "settings":
            self.app.push_screen(ExperimentConfigScreen(data_root=Path(self.request.data_root or self.app.data_root),
                participant_id=self.request.participant_id,session_mode=self.request.session_mode,
                experiment=get_experiment(self.request.experiment_id),monitor_profile_id=profile.id,
                defaults=self.request.experiment_values,review_return=self,focus_field=row.get("field")))
        elif row["destination"] == "calibration":
            if row.get("stage") == "bind":
                from .profiles import ProfileScreen
                self.app.push_screen(ProfileScreen(profile=profile,focus_field="profile-binding"))
                return
            self.app.display_guide_target_profile_id = profile.id
            self.app.display_draft["geometry-monitor"] = profile.id
            from dataclasses import asdict
            save_preferences(self.app.local_config_root, calibration_active_stage=row.get("stage") or "review",
                calibration_review_return={"request":asdict(self.request),"snapshot":self.reviewed_profile_snapshot})
            page = DisplayCheckScreen()
            page.return_to_configuration = True
            page.return_to_review = True
            self.app.push_screen(page)
        else:
            self.app.open_hub_page("setup")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        button_id = event.button.id
        if button_id and button_id.startswith("resolve-"):
            event.stop()
            self.resolve_requirement(button_id.removeprefix("resolve-"))
            return
        if button_id == "review-next-action":
            event.stop()
            if getattr(self, "next_requirement_key", None):
                self.resolve_requirement(self.next_requirement_key)
            return
        if button_id not in {"back", "run", "run-simulation", "run-presentation-test", "review-calibration-guide"}:
            return
        event.stop()
        try:
            if button_id == "review-calibration-guide":
                from .calibration_guide import CalibrationGuideScreen
                from ..config.human_readiness import next_human_requirement
                row = next_human_requirement(self.readiness_report)
                stage = {"binding":"display", "sampling":"display",
                         "geometry":"geometry", "luminance":"luminance",
                         "timing":"timing", "contrast":"contrast",
                         "qualification":"qualification",
                         "configuration":"contrast", "participant":"qualification"}.get(
                             row["key"] if row else "", "qualification")
                self.app.push_screen(CalibrationGuideScreen(
                    self.request, initial_stage=stage))
            elif button_id == "back":
                self.app.pop_screen()
            elif button_id == "run-presentation-test":
                from .presentation_testing import PresentationTestScreen
                self.app.push_screen(PresentationTestScreen(self.request))
            else:
                spec = get_experiment(self.request.experiment_id)
                current = load_monitor_profiles(self.app.repo_root)[self.request.monitor_profile_id]
                validate_setup(self.request, spec, current, mode="simulation" if button_id == "run-simulation" else "human")
                if button_id == "run-simulation":
                    from .unified_run import VirtualObserverOptionsScreen
                    from simulations.scenarios import list_scenarios
                    if not list_scenarios(self.request.experiment_id):
                        raise ValueError("This experiment has no registered virtual-observer scenarios.")
                    self.app.push_screen(VirtualObserverOptionsScreen(self.request))
                else:
                    if self.request.participant_id == "synthetic_preview":
                        raise ValueError("Provide a real pseudonymous participant ID in the previous screen before human acquisition.")
                    if current.origin == "local" and not current.display_binding:
                        raise ValueError(
                            "This saved local monitor profile is an UNBOUND DRAFT. "
                            "Open Calibrate → Edit / copy display profile, Detect connected displays, "
                            "select the physical monitor, save a new revision and verify its geometry "
                            "before launching a human experiment."
                        )
                    if (spec.id == "contrast_sensitivity"
                            and self.request.experiment_values.get("condition_unit") != "legacy_shader_radians"
                            and current.expected_resolution_px is None):
                        raise ValueError(
                            "Cannot run physically specified cpd gratings without an expected "
                            "fullscreen pixel resolution. In Calibrate, bind your display, "
                            "save a measured local profile with its pixel dimensions and "
                            "confirm the fullscreen geometry. The virtual simulation mode "
                            "remains available without hardware calibration."
                        )
                    from ..core.display import preflight_fullscreen_display
                    preflight_fullscreen_display(current)
                    self.app.exit(self.request)
        except Exception as exc:
            self._refresh_readiness()
            self.query_one("#review-status", Static).update("Run not started. " + (str(exc) if "\n" not in str(exc) else "See Human Experiment Readiness for the outstanding requirements."))
            self.query_one("#readiness-technical", Static).update(str(exc))
            if not isinstance(exc, (ValueError, KeyError)):
                _report_ui_exception(self.app, exc, phase=f"tui_review_{button_id}")


class PsyCoLabSetupApp(App):
    TITLE = "PsyCoLab"
    SUB_TITLE = "Psychophysics Collaborative Lab"

    CSS = """
    .invalid-input { border: tall $error; }
    Screen { align: center top; }
    #fixed-shell { dock: top; height: auto; width: 100%; }
    #fixed-shell Header { dock: none; height: 1; }
    #hub-nav { width: 100%; height: 3; }
    #hub-nav Button { width: 1fr; min-width: 0; margin: 0; padding: 0; }
    #setup-body, #review-body, .page-body, #code-body, #config-body {
        width: 100%; height: 1fr; border: round $accent; padding: 1 2;
    }
    Label { margin-top: 1; }
    Input, Select { width: 100%; }
    .field-row { height: 3; width: 100%; }
    .field-row Input { width: 1fr; }
    .field-row Button { width: 13; min-width: 0; margin: 0; }
    Collapsible { padding: 0; margin: 0 0 1 0; }
    .field-help { color: $text-muted; margin-bottom: 1; }
    .info-card { border: solid $surface-lighten-2; padding: 1; margin-top: 1; margin-bottom: 1; }
    /* Human acquisition checks use an obvious visible edge; the first
       unresolved prerequisite gets the strongest warning border. */
    .readiness-blocked { border: solid $warning; }
    .readiness-next { border: heavy $warning; }
    .readiness-done { border: solid $success; }
    .readiness-optional { border: solid $surface-lighten-2; }
    #human-next-action { margin-top: 1; }
    #review-next-action { width: auto; margin: 0 0 1 1; }
    .section-title { margin-top: 2; }
    .buttons { height: 3; margin: 0; align-horizontal: right; }
    .buttons Button { min-width: 0; max-width: 50%; margin: 0; }
    .wrap-buttons { align-horizontal: left; }
    Button { margin-left: 1; }
    #setup-status, #config-status, #review-status, #geometry-status, #data-status, #sim-status {
        min-height: 1;
        margin-top: 1;
    }
    #code-text { width: 100%; }
    #human-participant-panel, #human-review-checks { height: auto; width: 100%; }
    #calibration-stage-nav { height: 3; width: 100%; }
    #calibration-stage-nav Button { width: 1fr; min-width: 0; margin: 0; padding: 0; }
    #calibration-stage-nav Button.calibration-active {
        text-style: bold underline; border-bottom: heavy $accent;
    }
    #calibration-stage-summary {
        height: auto; min-height: 2; padding: 0 1; background: $surface;
    }
    #calibration-pages { width: 100%; height: 1fr; }
    #calibration-pages .calibration-panel {
        width: 100%; height: 1fr; overflow-y: auto;
    }
    .calibration-panel Button { margin: 1 0; min-width: 0; }
    """

    def __init__(self, *, repo_root: Path, data_root: Path,
                 simulation_summary: str | None = None,
                 geometry_summary: str | None = None) -> None:
        super().__init__()
        self.simulation_summary = simulation_summary
        self.geometry_summary = geometry_summary
        self.repo_root = repo_root.resolve()
        self.data_root = data_root.resolve()
        self.local_config_root = config_root(self.repo_root, self.data_root)
        self.monitor_profiles = load_monitor_profiles(repo_root)
        self.config_drafts = {}
        self.mapping_drafts = {}
        self.stimulus_drafts = {}
        saved_draft = preferences(self.local_config_root).get("calibration_experiment_draft")
        if isinstance(saved_draft, dict) and isinstance(saved_draft.get("values"), dict):
            keys = tuple(saved_draft.get(k) for k in ("participant", "experiment", "profile"))
            if all(isinstance(k, str) for k in keys):
                self.config_drafts[keys] = saved_draft["values"]
                self.mapping_drafts[keys] = saved_draft.get("background_selection", {})
        self.display_draft = {}
        self.display_guide_target_profile_id = None
        # Researcher intent is UI-only: it never downgrades acquisition preflight.
        self.run_intent = "test"

    def inspect_source(self, path: Path) -> None:
        try:
            open_source(self.repo_root, path, executable=preferences(self.local_config_root).get("editor_executable"))
            self.notify(f"Opened {path.name} in the PsyCoLab VS Code project.")
        except (ValueError, OSError) as exc:
            if path.resolve().is_relative_to(self.repo_root) and path.is_file():
                from .source_view import SourceView
                self.push_screen(SourceView(path))
                self.notify("External editor unavailable; opened a read-only source view.")
            else:
                self.notify(str(exc), severity="error", timeout=10)

    def reload_profiles(self) -> None:
        self.monitor_profiles = load_monitor_profiles(self.repo_root)
        self._refresh_experiment_context()
        preferred = preferences(self.local_config_root).get("active_monitor_profile_id")
        experiment = get_experiment(str(self.screen_stack[0].query_one("#experiment", Select).value))
        if preferred in self._compatible_profiles(experiment):
            self.screen_stack[0].query_one("#monitor-profile", Select).value = preferred

    def open_hub_page(self, page: str) -> None:
        if isinstance(self.screen, DisplayCheckScreen):
            self.display_draft = {
                w.id: w.value
                for w in self.screen.query("Input, Select")
                if _restorable_calibration_field(w.id)
                and not _is_blank_select_value(w.value)
            }
        for screen in self.screen_stack:
            if isinstance(screen, ExperimentConfigScreen):
                screen.remember_draft()
        if page == "setup":
            while len(self.screen_stack) > 1:
                self.pop_screen()
            return
        from .simulations import SimulationsScreen

        pages = {
            "simulations": SimulationsScreen,
            "experiments": ExperimentsScreen,
            "stimuli": StimuliScreen,
            "display": DisplayCheckScreen,
            "data": DataScreen,
            "help": HelpScreen,
        }
        cls = pages.get(page)
        if cls is None:
            return
        screen = cls()
        if len(self.screen_stack) > 1:
            self.switch_screen(screen)
        else:
            self.push_screen(screen)

    def _state_for(self, data_root: Path) -> tuple[dict[str, Any] | None, str | None]:
        try:
            return load_workspace_state(data_root), None
        except ValueError as exc:
            return None, str(exc)

    def _initial_values(self) -> tuple[SetupRequest | None, dict[str, Any] | None, str | None]:
        state, warning = self._state_for(self.data_root)
        return request_from_workspace_state(state), state, warning

    def compose(self) -> ComposeResult:
        experiments = list_experiments()
        experiment_options = [(spec.display_name, spec.id) for spec in experiments]

        last_request, state, warning = self._initial_values()
        saved_draft = preferences(self.local_config_root).get("calibration_experiment_draft", {})
        participant_default = last_request.participant_id if last_request else saved_draft.get("participant", "")
        if participant_default == "synthetic_preview":
            participant_default = ""
        session_default = "reuse" if last_request else "new"
        experiment_default = (
            last_request.experiment_id
            if last_request and any(spec.id == last_request.experiment_id for spec in experiments)
            else experiments[0].id
        )
        selected_spec = get_experiment(experiment_default)
        allowed_profiles = self._compatible_profiles(selected_spec)
        if allowed_profiles:
            monitor_default = (
                last_request.monitor_profile_id
                if last_request and last_request.monitor_profile_id in allowed_profiles
                else next(iter(allowed_profiles))
            )
            preferred = preferences(self.local_config_root).get("active_monitor_profile_id")
            if preferred in allowed_profiles:
                monitor_default = preferred
            monitor_options = [
                (f"{profile.display_name} [{profile.id} · rev {profile.revision}]", profile.id) for profile in allowed_profiles.values()
            ]
            if preferred and preferred not in allowed_profiles:
                monitor_options.append((f"Unavailable saved profile: {preferred} — restore in Calibrate", preferred))
                monitor_default = preferred
        else:
            monitor_default = "__none__"
            monitor_options = [("No compatible monitor profiles", "__none__")]

        participants = list_participants(self.data_root)
        participant_options = [(item, item) for item in participants] + [("+ New participant", "__new__")]
        participant_choice = participant_default if participant_default in participants else "__new__"

        last_run = (state or {}).get("last_run", {})
        last_summary = "No previous PsyCoLab run recorded in this data folder."
        if last_request:
            last_summary = (
                f"Last setup: {last_request.participant_id} / {last_request.experiment_id} / "
                f"{(state or {}).get('last_status', 'unknown')}"
            )
            if last_run.get("run_directory"):
                last_summary += f"\nLast run: {last_run['run_directory']}"
        if warning:
            last_summary = f"[red]{warning}[/red]"

        with Vertical(id="fixed-shell"):
            yield Header(show_clock=True)
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Exit", id="exit")
                yield Button("Configure Experiment", id="configure", variant="primary")
            yield Static("", id="setup-status")
        with VerticalScroll(id="setup-body"):
            yield Static("[b]What would you like to do?[/b]")
            yield Select([
                ("Test an experiment on this monitor (no photometer required)", "test"),
                ("Run a human experiment (physical verification required)", "human"),
                ("Run a simulation with a virtual observer", "simulation"),
            ], value=self.run_intent, allow_blank=False, id="run-intent")
            yield Static("", id="run-intent-help", markup=False)
            yield Static("Configure the experiment and its stimuli. The chosen run type "
                         "decides which final checks are shown.", markup=False)
            if self.simulation_summary:
                yield Static(self.simulation_summary, id="last-simulation", classes="info-card")

            yield Label("External data workspace")
            yield Input(value=str(self.data_root), id="data-root")
            yield Static(
                "Participant/acquisition data must remain outside the Git repository. An adjacent "
                "folder is recommended.",
                classes="field-help",
            )
            yield Button("Load Data Workspace", id="load-data-root")
            yield Static(last_summary, id="last-run-summary", classes="field-help")

            with Vertical(id="human-participant-panel"):
                yield Label("Existing participant")
                yield Select(participant_options, value=participant_choice, allow_blank=False, id="participant-select")
                yield Label("Participant ID (pseudonymous)")
                yield Input(value=participant_default, placeholder="e.g. S001", id="participant")
                yield Static("Only needed for real human acquisition.", classes="field-help")

            yield Label("Starting settings")
            yield Select(
                [
                    ("Start from experiment defaults / new settings", "new"),
                    ("Reuse last settings — starts a new run", "reuse"),
                ],
                value=session_default,
                allow_blank=False,
                id="session-mode",
            )

            yield Label("Experiment")
            yield Select(experiment_options, value=experiment_default, allow_blank=False, id="experiment")
            yield Static("", id="experiment-summary", classes="info-card")

            yield Label("Display profile")
            yield Select(
                monitor_options,
                value=monitor_default,
                allow_blank=False,
                id="monitor-profile",
            )
            yield Static("", id="monitor-summary", classes="info-card")

        yield Footer()

    def on_mount(self) -> None:
        self._refresh_experiment_context()
        self._refresh_run_intent()
        if self.geometry_summary:
            self.call_after_refresh(self._restore_diagnostic_review)

    async def _restore_diagnostic_review(self):
        local = preferences(self.local_config_root)
        navigation = local.get("calibration_navigation")
        saved = local.get("calibration_review_return")
        if not isinstance(navigation, dict) and not isinstance(saved, dict):
            return
        # Consume the one-shot navigation request. The Review return destination
        # remains represented by its restored screen until an explicit Return.
        save_preferences(self.local_config_root, calibration_navigation=None)
        try:
            from_review = navigation.get("return_to_review", False) if isinstance(navigation, dict) else True
            if from_review and isinstance(saved, dict):
                request = SetupRequest(**saved["request"])
                get_experiment(request.experiment_id)
                review = ReviewScreen(request=request)
                await self.push_screen(review)
                review.reviewed_profile_snapshot = saved.get("snapshot")
                review.on_screen_resume()
            profile_id = navigation["profile"] if isinstance(navigation, dict) else request.monitor_profile_id
            if profile_id not in self.monitor_profiles:
                raise ValueError("Selected display is unavailable; select it explicitly in Calibrate")
            if isinstance(navigation, dict):
                self.display_draft = dict(navigation.get("settings", {}))
            self.display_draft["geometry-monitor"] = profile_id
            self.display_guide_target_profile_id = profile_id
            page = DisplayCheckScreen()
            page.return_to_configuration = from_review and isinstance(saved, dict)
            page.return_to_review = page.return_to_configuration
            await self.push_screen(page)
            if isinstance(navigation, dict):
                page._go_to_stage(navigation.get("stage", "bind"), remember=False)
        except (KeyError, TypeError, ValueError) as exc:
            self.screen_stack[0].query_one("#setup-status", Static).update(
                f"Cannot restore calibration context: {exc}. Select current settings explicitly.")

    def _refresh_run_intent(self) -> None:
        if not self.screen_stack:
            return
        home=self.screen_stack[0]
        try:
            selected=home.query_one("#run-intent",Select).value
            explanation=home.query_one("#run-intent-help",Static)
            human_panel=home.query_one("#human-participant-panel",Vertical)
        except Exception:
            return  # Another hub screen is mounting, or startup is incomplete.
        intent=str(selected) if selected in ("test","human","simulation") else "test"
        self.run_intent=intent
        human_panel.display=intent=="human"
        if intent=="test":
            explanation.update("TEST MODE — draw real fullscreen stimuli using saved test settings. "
                               "No photometer or human qualification required. "
                               "Digital bounds and physical display safety still apply.")
        elif intent=="simulation":
            explanation.update("SIMULATION — use a virtual observer. No fullscreen stimulus "
                               "or physical laboratory certification required.")
        else:
            explanation.update("HUMAN ACQUISITION — use a participant ID. Physical geometry, "
                               "photometry and any experiment-specific timing requirements "
                               "must be genuinely reviewed and qualified.")

    def _compatible_profiles(self, experiment: ExperimentSpec) -> dict[str, Any]:
        # Availability is independent of human qualification.
        return dict(self.monitor_profiles)

    def _refresh_experiment_context(self) -> None:
        if not self.screen_stack:
            return
        experiment_id = self.screen_stack[0].query_one("#experiment", Select).value
        if _is_blank_select_value(experiment_id):
            return
        experiment = get_experiment(str(experiment_id))
        self.screen_stack[0].query_one("#experiment-summary", Static).update(
            f"[b]{experiment.display_name}[/b]\n{experiment.description}"
        )
        profiles = self._compatible_profiles(experiment)
        selector = self.screen_stack[0].query_one("#monitor-profile", Select)
        if not profiles:
            selector.set_options([("No compatible monitor profiles", "__none__")])
            selector.value = "__none__"
            self.screen_stack[0].query_one("#monitor-summary", Static).update(
                "[red]No registered monitor profile is compatible with this experiment.[/red]"
            )
            self.screen_stack[0].query_one("#setup-status", Static).update(
                "[red]Add/validate a monitor profile before running this experiment.[/red]"
            )
            return
        current = selector.value
        options = [(f"{item.display_name} [{item.id} · rev {item.revision}]", item.id) for item in profiles.values()]
        missing = not _is_blank_select_value(current) and current not in profiles and current != "__none__"
        if missing:
            options.append((f"Unavailable saved profile: {current} — restore in Calibrate", current))
        selector.set_options(options)
        # Preserve a requested missing profile visibly, never silently choose the reference.
        selector.value = current if current in profiles or missing else next(iter(profiles))
        self._refresh_monitor_context()

    def _refresh_monitor_context(self) -> None:
        if not self.screen_stack:
            return  # Ignore queued Select messages during shutdown.
        value = self.screen_stack[0].query_one("#monitor-profile", Select).value
        if _is_blank_select_value(value):
            return
        if str(value) not in self.monitor_profiles:
            self.screen_stack[0].query_one("#monitor-summary", Static).update(
                f"[red]Requested display '{value}' is unavailable. Restore/reload it in Calibrate or explicitly select another profile. No reference fallback was applied.[/red]")
            return
        self.screen_stack[0].query_one("#monitor-summary", Static).update(
            _monitor_summary(self.monitor_profiles[str(value)]) + "\n" + readiness_text(
                get_experiment(str(self.screen_stack[0].query_one("#experiment", Select).value)),
                self.monitor_profiles[str(value)], self.repo_root)
        )

    def _selected_data_root(self, *, create: bool) -> Path:
        value = self.screen_stack[0].query_one("#data-root", Input).value
        data_root = resolve_data_root(value, self.repo_root)
        config_root(self.repo_root, data_root)  # Validate separation before creating folders.
        if create:
            data_root.mkdir(parents=True, exist_ok=True)
        return data_root

    def _refresh_data_root(self) -> None:
        data_root = self._selected_data_root(create=True)
        self.local_config_root = config_root(self.repo_root, data_root)
        self.data_root = data_root
        state, warning = self._state_for(data_root)
        last_request = request_from_workspace_state(state)

        participants = list_participants(data_root)
        participant_select = self.screen_stack[0].query_one("#participant-select", Select)
        participant_select.set_options(
            [(item, item) for item in participants] + [("+ New participant", "__new__")]
        )

        summary = "No previous PsyCoLab run recorded in this data folder."
        if warning:
            summary = f"[red]{warning}[/red]"
        elif last_request:
            summary = (
                f"Last setup: {last_request.participant_id} / {last_request.experiment_id} / "
                f"{(state or {}).get('last_status', 'unknown')}"
            )
            last_run = (state or {}).get("last_run", {})
            if last_run.get("run_directory"):
                summary += f"\nLast run: {last_run['run_directory']}"
            self.screen_stack[0].query_one("#participant", Input).value = last_request.participant_id
            participant_select.value = (
                last_request.participant_id if last_request.participant_id in participants else "__new__"
            )
            self.screen_stack[0].query_one("#session-mode", Select).value = "reuse"
            if any(spec.id == last_request.experiment_id for spec in list_experiments()):
                self.screen_stack[0].query_one("#experiment", Select).value = last_request.experiment_id
            self._refresh_experiment_context()
            if last_request.monitor_profile_id in self.monitor_profiles:
                selected_experiment = str(self.screen_stack[0].query_one("#experiment", Select).value)
                compatible = self._compatible_profiles(get_experiment(selected_experiment))
                if last_request.monitor_profile_id in compatible:
                    self.screen_stack[0].query_one("#monitor-profile", Select).value = last_request.monitor_profile_id
        else:
            participant_select.value = "__new__"
        self.screen_stack[0].query_one("#last-run-summary", Static).update(summary)
        self.screen_stack[0].query_one("#data-root", Input).value = str(data_root)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "participant-select":
            if not _is_blank_select_value(event.value) and str(event.value) != "__new__":
                self.screen_stack[0].query_one("#participant", Input).value = str(event.value)
        elif event.select.id == "run-intent":
            self._refresh_run_intent()
        elif event.select.id == "experiment":
            self._refresh_experiment_context()
        elif event.select.id == "monitor-profile":
            self._refresh_monitor_context()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("nav-"):
            event.stop()
            self.open_hub_page(button_id.removeprefix("nav-"))
            return
        if button_id not in {"exit", "load-data-root", "configure"}:
            return

        event.stop()
        if button_id == "exit":
            self.exit(None)
            return

        status = self.screen_stack[0].query_one("#setup-status", Static)
        if button_id == "load-data-root":
            try:
                self._refresh_data_root()
                status.update(f"[green]Loaded external data workspace: {self.data_root}[/green]")
            except Exception as exc:
                status.update(f"[red]{exc}[/red]")
            return

        try:
            data_root = self._selected_data_root(create=True)
            self.local_config_root = config_root(self.repo_root, data_root)
            self.data_root = data_root
            entered_participant = self.screen_stack[0].query_one("#participant", Input).value.strip()
            # Keep an existing draft's identifier stable for backward
            # compatibility. Actual presentation tests override it with a new
            # synthetic-only ID at the isolated runtime boundary; simulations
            # never record it as a human participant.
            if self.run_intent == "human" and not entered_participant:
                raise ValueError("Enter a pseudonymous participant ID for human acquisition.")
            participant = validate_participant_id(
                entered_participant or "synthetic_preview"
            )
            session_mode = self.screen_stack[0].query_one("#session-mode", Select).value
            experiment_id = self.screen_stack[0].query_one("#experiment", Select).value
            monitor_id = self.screen_stack[0].query_one("#monitor-profile", Select).value

            if _is_blank_select_value(session_mode) or _is_blank_select_value(experiment_id) or _is_blank_select_value(monitor_id):
                raise ValueError("Starting settings, experiment and display profile must be selected.")

            experiment = get_experiment(str(experiment_id))
            monitor_id = str(monitor_id)
            if monitor_id not in self.monitor_profiles:
                raise ValueError("Requested display profile is unavailable. Restore it in Calibrate or explicitly choose another display; no fallback was applied.")

            defaults = experiment.field_defaults()
            if session_mode == "reuse":
                previous = request_from_workspace_state(load_workspace_state(data_root))
                if previous is None:
                    raise ValueError(
                        "No previous PsyCoLab setup exists in this data workspace. "
                        "Choose 'Start from experiment defaults / new settings'."
                    )
                if previous.experiment_id != experiment.id:
                    raise ValueError(
                        "The saved setup belongs to a different experiment. Choose that experiment "
                        "or start from new/default settings."
                    )
                defaults = dict(previous.experiment_values)

            self.push_screen(
                ExperimentConfigScreen(
                    data_root=data_root,
                    participant_id=participant,
                    session_mode=str(session_mode),
                    experiment=experiment,
                    monitor_profile_id=monitor_id,
                    defaults=defaults,
                )
            )
        except Exception as exc:
            status.update(f"[red]{exc}[/red]")
            self.notify(str(exc), title="Experiment setup blocked", severity="error", timeout=8)
            if not isinstance(exc, (ValueError, KeyError)):
                _report_ui_exception(self, exc, phase=f"tui_setup_{button_id}")


def run_setup_tui(*, repo_root: Path, data_root: Path,
                  simulation_summary: str | None = None,
                  geometry_summary: str | None = None) -> SetupRequest | GeometryCheckRequest | None:
    app = PsyCoLabSetupApp(repo_root=repo_root, data_root=data_root,
                           simulation_summary=simulation_summary,
                           geometry_summary=geometry_summary)
    return app.run()
