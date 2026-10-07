from __future__ import annotations

import csv
from datetime import datetime
import json
from pathlib import Path
import traceback
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from ..analysis.thresholds import analyse_thresholds
from ..config.models import SetupRequest
from ..config.monitor import load_monitor_profiles
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


NAV_PAGES = (
    ("setup", "Run / Setup"),
    ("experiments", "Experiments"),
    ("stimuli", "Stimuli"),
    ("display", "Display Check"),
    ("data", "Data"),
    ("help", "Help / Developer"),
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
        f"{width_mm:.0f} × {height_mm:.0f} mm · {profile.refresh_rate_hz} Hz · "
        f"viewing distance {profile.viewing_distance_m:.3f} m",
        f"Resolution: {resolution}",
        f"Calibration: {calibration}",
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
    candidates = [
        repo_root / "src" / "psychophysics_lab" / "experiments" / f"{experiment.id}.py",
        repo_root.joinpath(*experiment.legacy_module.split(".")).with_suffix(".py"),
    ]
    unique: list[Path] = []
    for path in candidates:
        if path.exists() and path not in unique:
            unique.append(path)
    return tuple(unique)


def _stimulus_sources(repo_root: Path) -> tuple[Path, ...]:
    directory = repo_root / "src" / "psychophysics_lab" / "stimuli"
    paths = []
    if directory.exists():
        paths.extend(
            path for path in sorted(directory.glob("*.py"))
            if path.name != "__init__.py"
        )
    # The current working CSF renderer remains in the compatibility layer.
    # Expose it for inspection without pretending it has already been migrated.
    legacy = repo_root / "Events" / "stimuliC.py"
    if legacy.exists():
        paths.append(legacy)
    return tuple(paths)


def _nav_bar() -> Horizontal:
    return Horizontal(
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
        yield Header(show_clock=True)
        with VerticalScroll(id="code-body"):
            yield Static(f"[b]{self.title_text}[/b]\n{self.path}")
            try:
                text = self.path.read_text(encoding="utf-8")
            except Exception as exc:
                text = f"Could not read file: {exc}"
            yield Static(text, id="code-text", markup=False)
            yield Button("Back", id="back", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            event.stop()
            self.app.pop_screen()


class HubPage(Screen):
    page_title = "PsyCoLab"

    def header(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield _nav_bar()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        _handle_nav(self, event)


class ExperimentsScreen(HubPage):
    page_title = "Experiments"

    def compose(self) -> ComposeResult:
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
            with Horizontal(classes="buttons"):
                yield Button("View experiment definition", id="view-exp-definition")
                yield Button("View runtime implementation", id="view-exp-runtime")
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
        spec = self._selected()
        sources = _source_candidates(self.app.repo_root, spec)
        if event.button.id == "view-exp-definition" and sources:
            event.stop()
            self.app.push_screen(CodeViewScreen(title=f"{spec.display_name} — definition", path=sources[0]))
        elif event.button.id == "view-exp-runtime":
            event.stop()
            if len(sources) >= 2:
                path = sources[-1]
            elif sources:
                path = sources[0]
            else:
                return
            self.app.push_screen(CodeViewScreen(title=f"{spec.display_name} — runtime", path=path))


class StimuliScreen(HubPage):
    page_title = "Stimuli"

    def compose(self) -> ComposeResult:
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
                yield Button("View stimulus source", id="view-stimulus-source", variant="primary")
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
        if event.button.id == "view-stimulus-source":
            event.stop()
            path = self._selected_path()
            self.app.push_screen(CodeViewScreen(title=path.name, path=path))


class DisplayCheckScreen(HubPage):
    page_title = "Display Geometry Check"

    def compose(self) -> ComposeResult:
        profiles = list(self.app.monitor_profiles.values())
        profile_options = [(item.display_name, item.id) for item in profiles]
        last_profile = next(iter(self.app.monitor_profiles))
        state = _workspace_request(self.app.data_root)
        if state and state.monitor_profile_id in self.app.monitor_profiles:
            last_profile = state.monitor_profile_id

        yield Header(show_clock=True)
        yield _nav_bar()
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]Display Geometry Check[/b]\n"
                "This is a laboratory diagnostic, not a participant experiment. A white bar is "
                "rendered fullscreen so its physical length can be checked with a ruler."
            )
            yield Label("Display profile")
            yield Select(profile_options, value=last_profile, allow_blank=False, id="geometry-monitor")
            yield Label("Check mode")
            yield Select(
                [("Visual angle (degrees)", "visual_angle_deg"), ("Physical length (mm)", "physical_mm")],
                value="visual_angle_deg",
                allow_blank=False,
                id="geometry-mode",
            )
            yield Label("Requested value")
            yield Input(value="5", id="geometry-value")
            yield Label("Orientation")
            yield Select(
                [("Horizontal", "horizontal"), ("Vertical", "vertical")],
                value="horizontal",
                allow_blank=False,
                id="geometry-orientation",
            )
            yield Label("Bar thickness (mm)")
            yield Input(value="5", id="geometry-thickness")
            yield Static("", id="geometry-preview", classes="info-card")
            yield Button("Launch Fullscreen Ruler Check", id="launch-geometry", variant="success")
            yield Static(
                "Automated tests verify the geometry calculation only. The ruler measurement, "
                "viewing distance, fullscreen behaviour and timing are laboratory checks.",
                classes="field-help",
            )
            yield Static("[b]Latest ruler result[/b]", classes="section-title")
            yield Static("", id="latest-geometry")
            yield Label("Measured bar length (mm, optional after the fullscreen check)")
            yield Input(value="", placeholder="e.g. 87.4", id="geometry-measured")
            yield Button("Record Measurement in Latest Diagnostic", id="record-geometry-measurement")
            yield Static("", id="geometry-status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_preview()
        self._refresh_latest()

    def _profile(self):
        value = self.query_one("#geometry-monitor", Select).value
        return self.app.monitor_profiles[str(value)]

    def _refresh_preview(self) -> None:
        try:
            profile = self._profile()
            mode = str(self.query_one("#geometry-mode", Select).value)
            value = float(self.query_one("#geometry-value", Input).value)
            if mode == "visual_angle_deg":
                length_mm = physical_length_for_visual_angle(value, profile.viewing_distance_m) * 1000.0
                requested = f"{value:g}° at {profile.viewing_distance_m:.3f} m"
            else:
                if value <= 0:
                    raise ValueError("Physical length must be positive.")
                length_mm = value
                requested = f"{value:g} mm physical length"
            resolution_note = (
                f"Expected profile resolution: {profile.expected_resolution_px[0]} × "
                f"{profile.expected_resolution_px[1]} px."
                if profile.expected_resolution_px
                else "Pixel length will be resolved from the actual fullscreen resolution at launch."
            )
            self.query_one("#geometry-preview", Static).update(
                _monitor_summary(profile)
                + f"\n\nRequested: {requested}\nExpected ruler length: [b]{length_mm:.2f} mm[/b]\n"
                + resolution_note
            )
        except Exception as exc:
            self.query_one("#geometry-preview", Static).update(f"[red]{exc}[/red]")

    def _refresh_latest(self) -> None:
        profile_id = str(self.query_one("#geometry-monitor", Select).value)
        report = latest_geometry_report(self.app.data_root, profile_id)
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
                    f"{report.relative_to(self.app.data_root)}\n"
                    f"Status: {payload.get('status', 'unknown')}\n"
                    f"Expected: {bar.get('intended_length_mm', 'n/a')} mm\n"
                    f"Rendered: {bar.get('length_px', 'n/a')} px\n"
                    f"Ruler measurement: {measured_text}"
                )
            except Exception as exc:
                text = f"Could not read latest diagnostic: {exc}"
        self.query_one("#latest-geometry", Static).update(text)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in {"geometry-monitor", "geometry-mode", "geometry-orientation"}:
            self._refresh_preview()
            if event.select.id == "geometry-monitor":
                self._refresh_latest()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in {"geometry-value", "geometry-thickness"}:
            self._refresh_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        status = self.query_one("#geometry-status", Static)
        if event.button.id == "launch-geometry":
            event.stop()
            try:
                request = GeometryCheckRequest(
                    monitor_profile_id=str(self.query_one("#geometry-monitor", Select).value),
                    mode=str(self.query_one("#geometry-mode", Select).value),
                    value=float(self.query_one("#geometry-value", Input).value),
                    orientation=str(self.query_one("#geometry-orientation", Select).value),
                    thickness_mm=float(self.query_one("#geometry-thickness", Input).value),
                    data_root=str(self.app.data_root),
                )
                if request.value <= 0 or request.thickness_mm <= 0:
                    raise ValueError("Requested value and bar thickness must be positive.")
                self.app.exit(request)
            except Exception as exc:
                status.update(f"[red]{exc}[/red]")
        elif event.button.id == "record-geometry-measurement":
            event.stop()
            try:
                profile_id = str(self.query_one("#geometry-monitor", Select).value)
                report = latest_geometry_report(self.app.data_root, profile_id)
                if report is None:
                    raise ValueError("Run a fullscreen geometry check first.")
                measured = float(self.query_one("#geometry-measured", Input).value)
                payload = record_geometry_measurement(
                    data_root=self.app.data_root,
                    report_file=report,
                    measured_length_mm=measured,
                )
                error = payload["measurement"]["error_percent"]
                status.update(f"[green]Measurement recorded. Error: {error:+.2f}%[/green]")
                self._refresh_latest()
            except Exception as exc:
                status.update(f"[red]{exc}[/red]")


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

        yield Header(show_clock=True)
        yield _nav_bar()
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]Acquisition data[/b]\n"
                f"Active external workspace: {self.app.data_root}\n"
                "Run folders are treated as read-only scientific records. Derived threshold "
                "outputs are written separately under analysis/."
            )
            yield Select(options, value=options[0][1], allow_blank=False, id="data-run")
            yield Static("", id="data-details", classes="info-card")
            with Horizontal(classes="buttons wrap-buttons"):
                yield Button("Manifest", id="inspect-manifest")
                yield Button("Trials", id="inspect-trials")
                yield Button("Staircase state", id="inspect-adaptive")
            yield Static("[b]Derived staircase threshold[/b]", classes="section-title")
            yield Label("Fraction of final reversal observations to retain")
            yield Input(value="0.80", id="threshold-fraction")
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
            yield Static(
                "Default convention: retain the final 80% of reversal values within each "
                "staircase, average those values to get a staircase threshold, then average "
                "staircase thresholds that share a condition. This is derived analysis only.",
                classes="field-help",
            )
            yield Static("", id="data-status")
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
                f"Display: {manifest.get('monitor_profile_id', 'n/a')}\n"
                f"Status: {manifest.get('status', 'n/a')}\n"
                f"Accepted responses: {manifest.get('accepted_trials', 'n/a')}\n"
                f"Run UUID: {manifest.get('run_uuid', 'n/a')}"
            )
        except Exception as exc:
            text = str(exc)
        self.query_one("#data-details", Static).update(text)

    def on_mount(self) -> None:
        self._refresh()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "data-run":
            self._refresh()

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
            if event.button.id == "inspect-manifest":
                event.stop(); self._inspect("manifest.json", "Run manifest")
            elif event.button.id == "inspect-trials":
                event.stop(); self._inspect("trials.tsv", "Canonical accepted-response table")
            elif event.button.id == "inspect-adaptive":
                event.stop(); self._inspect("adaptive_session.json", "Saved staircase/adaptive state")
            elif event.button.id == "analyse-threshold":
                event.stop()
                fraction = float(self.query_one("#threshold-fraction", Input).value)
                column = str(self.query_one("#threshold-column", Select).value)
                result = analyse_thresholds(
                    data_root=self.app.data_root,
                    run_directory=self._run_dir(),
                    retain_fraction=fraction,
                    reversal_value_column=column,
                    create_plot=True,
                )
                plot_text = str(result.plot_file) if result.plot_file else (
                    "plot not produced (matplotlib unavailable); tables were still saved"
                )
                status.update(
                    "[green]Derived analysis created.[/green]\n"
                    f"Folder: {result.output_directory}\n"
                    f"Condition table: {result.condition_table}\nPlot: {plot_text}"
                )
        except Exception as exc:
            status.update(f"[red]{exc}[/red]")


class HelpScreen(HubPage):
    page_title = "Help / Developer"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield _nav_bar()
        with VerticalScroll(classes="page-body"):
            yield Static(
                "[b]PsyCoLab development map[/b]\n\n"
                "[b]Stimuli[/b] — what is presented. Reusable stimulus code belongs under "
                "src/psychophysics_lab/stimuli/.\n\n"
                "[b]Experiment procedures[/b] — how stimuli, timing, conditions and responses "
                "are combined. Add an ExperimentSpec and register it explicitly in "
                "src/psychophysics_lab/experiments/registry.py.\n\n"
                "[b]Adaptive methods[/b] — how parameters change from accepted responses. "
                "Current CSF staircase mechanics remain in the compatibility layer while that "
                "boundary is migrated deliberately.\n\n"
                "[b]Framework infrastructure[/b] — configuration, display profiles, lifecycle, "
                "recording and provenance.\n\n"
                "[b]Data rule[/b] — participant/acquisition data must stay outside this Git "
                "repository. The active workspace is validated by PsyCoLab before use.\n\n"
                "[b]Scientific rule[/b] — do not silently change stimulus mathematics, timings, "
                "response mappings, staircase rules, calibration semantics, contrast definitions "
                "or the retained 31.5 scaling. Such changes require explicit scientific review.\n\n"
                "The Experiments and Stimuli pages can inspect source code directly. This build "
                "also includes an extension guide/template, while intentionally avoiding an "
                "unrestricted source-code editor inside the acquisition TUI."
            )
            yield Button("Open Extension Guide", id="view-extension-guide", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if _handle_nav(self, event):
            return
        if event.button.id == "view-extension-guide":
            event.stop()
            path = self.app.repo_root / "docs" / "EXTENDING_PSYCOLAB.md"
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
    ) -> None:
        super().__init__()
        self.data_root = data_root
        self.participant_id = participant_id
        self.session_mode = session_mode
        self.experiment = experiment
        self.monitor_profile_id = monitor_profile_id
        self.defaults = defaults

    def compose(self) -> ComposeResult:
        profile = self.app.monitor_profiles[self.monitor_profile_id]
        yield Header(show_clock=True)
        with VerticalScroll(id="config-body"):
            yield Static(
                f"[b]{self.experiment.display_name}[/b]\n{self.experiment.description}\n\n"
                + _monitor_summary(profile),
                id="experiment-description",
            )
            for field in self.experiment.fields:
                yield Label(field.label)
                value = self.defaults.get(field.key, field.default)
                widget_id = _field_widget_id(field)
                if field.kind == "choice":
                    options = [(str(choice), choice) for choice in field.choices]
                    kwargs: dict[str, Any] = {"id": widget_id, "allow_blank": field.default is None}
                    if value is not None:
                        kwargs["value"] = value
                    yield Select(options, **kwargs)
                else:
                    yield Input(value="" if value is None else str(value), id=widget_id)
                if field.help_text:
                    yield Static(field.help_text, classes="field-help")

            yield Static("", id="config-status")
            with Horizontal(classes="buttons"):
                yield Button("Back", id="back")
                yield Button("Review", id="review", variant="primary")
        yield Footer()

    def _collect(self) -> dict[str, Any]:
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

        # Monitor-aware validation currently applies to the CSF luminance pair.
        # The scientific semantics are unchanged; the UI simply surfaces the
        # selected profile's existing validation before launch.
        profile = self.app.monitor_profiles[self.monitor_profile_id]
        if {"Background_Luminance", "Background_Screen_intensity"}.issubset(values):
            profile.validate_luminance_pair(
                luminance_cdm2=float(values["Background_Luminance"]),
                screen_intensity=float(values["Background_Screen_intensity"]),
            )
        return values

    def on_button_pressed(self, event: Button.Pressed) -> None:
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
            )
            self.app.push_screen(ReviewScreen(request=request))
        except Exception as exc:
            status.update(f"[red]{exc}[/red]")
            _report_ui_exception(self.app, exc, phase="tui_experiment_config_review")


class ReviewScreen(Screen):
    def __init__(self, *, request: SetupRequest) -> None:
        super().__init__()
        self.request = request

    def compose(self) -> ComposeResult:
        experiment = get_experiment(self.request.experiment_id)
        profile = self.app.monitor_profiles[self.request.monitor_profile_id]
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
            f"Display: {profile.display_name}",
            f"Calibration status: {profile.calibration_status}",
            "",
            "[b]Expected run location[/b]",
            prospective,
            "(run_NNN is allocated safely when acquisition starts)",
            "",
            "[b]Experiment parameters[/b]",
        ]
        for field in experiment.fields:
            lines.append(f"{field.label}: {self.request.experiment_values[field.key]}")

        if not profile.has_verified_luminance_mapping and {
            "Background_Luminance",
            "Background_Screen_intensity",
        }.issubset(self.request.experiment_values):
            lines.extend(
                [
                    "",
                    "[yellow]This monitor profile does not contain a trusted luminance-command "
                    "mapping. Physical luminance and digital intensity are saved, but the pair "
                    "remains explicitly manual/unverified.[/yellow]",
                ]
            )

        lines.extend(
            [
                "",
                "A new self-contained run folder will be created. Canonical accepted responses "
                "are appended to trials.tsv; compatibility files and provenance snapshots are "
                "retained according to the existing acquisition contract.",
            ]
        )

        yield Header(show_clock=True)
        with VerticalScroll(id="review-body"):
            yield Static("\n".join(lines), id="review-text")
            yield Static("", id="review-status")
            with Horizontal(classes="buttons"):
                yield Button("Back", id="back")
                yield Button("Run Experiment", id="run", variant="success")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id not in {"back", "run"}:
            return
        event.stop()
        try:
            if button_id == "back":
                self.app.pop_screen()
            else:
                self.app.exit(self.request)
        except Exception as exc:
            self.query_one("#review-status", Static).update(f"[red]{exc}[/red]")
            _report_ui_exception(self.app, exc, phase=f"tui_review_{button_id}")


class PsyCoLabSetupApp(App):
    TITLE = "PsyCoLab"
    SUB_TITLE = "Psychophysics Collaborative Lab"

    CSS = """
    Screen { align: center middle; }

    #hub-nav {
        width: 96%;
        height: auto;
        align-horizontal: center;
        margin-bottom: 1;
    }
    #hub-nav Button { margin-right: 1; }

    #setup-body, #review-body, .page-body, #code-body {
        width: 92%;
        max-width: 120;
        height: auto;
        max-height: 92%;
        border: round $accent;
        padding: 1 2;
    }
    #config-body {
        width: 92%;
        max-width: 120;
        height: 92%;
        border: round $accent;
        padding: 1 2;
    }
    Label { margin-top: 1; }
    Input, Select { width: 100%; }
    .field-help { color: $text-muted; margin-bottom: 1; }
    .info-card { border: solid $surface-lighten-2; padding: 1; margin-top: 1; margin-bottom: 1; }
    .section-title { margin-top: 2; }
    .buttons { height: auto; margin-top: 2; align-horizontal: right; }
    .wrap-buttons { align-horizontal: left; }
    Button { margin-left: 1; }
    #setup-status, #config-status, #review-status, #geometry-status, #data-status {
        min-height: 1;
        margin-top: 1;
    }
    #code-text { width: 100%; }
    """

    def __init__(self, *, repo_root: Path, data_root: Path) -> None:
        super().__init__()
        self.repo_root = repo_root.resolve()
        self.data_root = data_root.resolve()
        self.monitor_profiles = load_monitor_profiles(repo_root)

    def open_hub_page(self, page: str) -> None:
        if page == "setup":
            while len(self.screen_stack) > 1:
                self.pop_screen()
            return
        pages = {
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
        participant_default = last_request.participant_id if last_request else ""
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
            monitor_options = [
                (profile.display_name, profile.id) for profile in allowed_profiles.values()
            ]
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

        yield Header(show_clock=True)
        yield _nav_bar()
        with VerticalScroll(id="setup-body"):
            yield Static(
                "[b]Run an experiment[/b]\n"
                "Configure the external data workspace, participant, experiment and display. "
                "The Textual hub closes before Pyglet/OpenGL acquisition begins."
            )

            yield Label("External data workspace")
            yield Input(value=str(self.data_root), id="data-root")
            yield Static(
                "Participant/acquisition data must remain outside the Git repository. An adjacent "
                "folder is recommended.",
                classes="field-help",
            )
            yield Button("Load Data Workspace", id="load-data-root")
            yield Static(last_summary, id="last-run-summary", classes="field-help")

            yield Label("Existing participant")
            yield Select(participant_options, value=participant_choice, allow_blank=False, id="participant-select")
            yield Label("Participant ID")
            yield Input(
                value=participant_default,
                placeholder="e.g. S001 or subject_1",
                id="participant",
            )
            yield Static(
                "Use a pseudonymous laboratory identifier. Selecting an existing participant "
                "fills this field; choose '+ New participant' to enter another ID.",
                classes="field-help",
            )

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

            yield Static("", id="setup-status")
            with Horizontal(classes="buttons"):
                yield Button("Exit", id="exit")
                yield Button("Configure Experiment", id="configure", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_experiment_context()

    def _compatible_profiles(self, experiment: ExperimentSpec) -> dict[str, Any]:
        if not experiment.compatible_monitor_profiles:
            return dict(self.monitor_profiles)
        return {
            key: profile for key, profile in self.monitor_profiles.items()
            if key in experiment.compatible_monitor_profiles
        }

    def _refresh_experiment_context(self) -> None:
        experiment_id = self.query_one("#experiment", Select).value
        if _is_blank_select_value(experiment_id):
            return
        experiment = get_experiment(str(experiment_id))
        self.query_one("#experiment-summary", Static).update(
            f"[b]{experiment.display_name}[/b]\n{experiment.description}"
        )
        profiles = self._compatible_profiles(experiment)
        selector = self.query_one("#monitor-profile", Select)
        if not profiles:
            selector.set_options([("No compatible monitor profiles", "__none__")])
            selector.value = "__none__"
            self.query_one("#monitor-summary", Static).update(
                "[red]No registered monitor profile is compatible with this experiment.[/red]"
            )
            self.query_one("#setup-status", Static).update(
                "[red]Add/validate a monitor profile before running this experiment.[/red]"
            )
            return
        current = selector.value
        selector.set_options([(item.display_name, item.id) for item in profiles.values()])
        if _is_blank_select_value(current) or str(current) not in profiles:
            selector.value = next(iter(profiles))
        self._refresh_monitor_context()

    def _refresh_monitor_context(self) -> None:
        value = self.query_one("#monitor-profile", Select).value
        if _is_blank_select_value(value) or str(value) not in self.monitor_profiles:
            return
        self.query_one("#monitor-summary", Static).update(
            _monitor_summary(self.monitor_profiles[str(value)])
        )

    def _selected_data_root(self, *, create: bool) -> Path:
        value = self.query_one("#data-root", Input).value
        data_root = resolve_data_root(value, self.repo_root)
        if create:
            data_root.mkdir(parents=True, exist_ok=True)
        return data_root

    def _refresh_data_root(self) -> None:
        data_root = self._selected_data_root(create=True)
        self.data_root = data_root
        state, warning = self._state_for(data_root)
        last_request = request_from_workspace_state(state)

        participants = list_participants(data_root)
        participant_select = self.query_one("#participant-select", Select)
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
            self.query_one("#participant", Input).value = last_request.participant_id
            participant_select.value = (
                last_request.participant_id if last_request.participant_id in participants else "__new__"
            )
            self.query_one("#session-mode", Select).value = "reuse"
            if any(spec.id == last_request.experiment_id for spec in list_experiments()):
                self.query_one("#experiment", Select).value = last_request.experiment_id
            self._refresh_experiment_context()
            if last_request.monitor_profile_id in self.monitor_profiles:
                compatible = self._compatible_profiles(get_experiment(last_request.experiment_id))
                if last_request.monitor_profile_id in compatible:
                    self.query_one("#monitor-profile", Select).value = last_request.monitor_profile_id
        else:
            participant_select.value = "__new__"
        self.query_one("#last-run-summary", Static).update(summary)
        self.query_one("#data-root", Input).value = str(data_root)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "participant-select":
            if not _is_blank_select_value(event.value) and str(event.value) != "__new__":
                self.query_one("#participant", Input).value = str(event.value)
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

        status = self.query_one("#setup-status", Static)
        if button_id == "load-data-root":
            try:
                self._refresh_data_root()
                status.update(f"[green]Loaded external data workspace: {self.data_root}[/green]")
            except Exception as exc:
                status.update(f"[red]{exc}[/red]")
            return

        try:
            data_root = self._selected_data_root(create=True)
            self.data_root = data_root
            participant = validate_participant_id(self.query_one("#participant", Input).value)
            session_mode = self.query_one("#session-mode", Select).value
            experiment_id = self.query_one("#experiment", Select).value
            monitor_id = self.query_one("#monitor-profile", Select).value

            if _is_blank_select_value(session_mode) or _is_blank_select_value(experiment_id) or _is_blank_select_value(monitor_id):
                raise ValueError("Starting settings, experiment and display profile must be selected.")

            experiment = get_experiment(str(experiment_id))
            monitor_id = str(monitor_id)
            if experiment.compatible_monitor_profiles and monitor_id not in experiment.compatible_monitor_profiles:
                raise ValueError("The selected experiment is not validated for that display profile.")

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
            _report_ui_exception(self, exc, phase=f"tui_setup_{button_id}")


def run_setup_tui(*, repo_root: Path, data_root: Path) -> SetupRequest | GeometryCheckRequest | None:
    app = PsyCoLabSetupApp(repo_root=repo_root, data_root=data_root)
    return app.run()
