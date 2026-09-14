from __future__ import annotations

from pathlib import Path
import traceback
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from ..config.models import SetupRequest
from ..config.monitor import load_monitor_profiles
from ..data.participants import list_participants, validate_participant_id
from ..data.workspace import load_workspace_state, request_from_workspace_state
from ..experiments.registry import get_experiment, list_experiments
from ..experiments.spec import ConfigField, ExperimentSpec
from ..paths import resolve_data_root




def _report_ui_exception(app: App, exc: BaseException, *, phase: str) -> None:
    """Best-effort logging for exceptions raised inside Textual message handlers.

    Textual handles message-callback exceptions internally, so they do not always
    propagate to the outer application crash boundary. Log them here as well.
    """
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
        # Diagnostics must never create a second UI failure.
        pass

def _field_widget_id(field: ConfigField) -> str:
    safe = field.key.replace("_", "-")
    return f"field-{safe}"


def _workspace_request(data_root: Path) -> SetupRequest | None:
    try:
        return request_from_workspace_state(load_workspace_state(data_root))
    except ValueError:
        return None


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
        yield Header(show_clock=True)
        with VerticalScroll(id="config-body"):
            yield Static(
                f"[b]{self.experiment.display_name}[/b]\n{self.experiment.description}",
                id="experiment-description",
            )
            for field in self.experiment.fields:
                yield Label(field.label)
                value = self.defaults.get(field.key, field.default)
                widget_id = _field_widget_id(field)
                if field.kind == "choice":
                    options = [(str(choice), choice) for choice in field.choices]
                    kwargs = {"id": widget_id, "allow_blank": field.default is None}
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
                if raw is Select.BLANK:
                    raw = None
            else:
                raw = self.query_one(f"#{widget_id}", Input).value
            values[field.key] = field.coerce(raw)
        values = self.experiment.normalise_values(values)

        profile = self.app.monitor_profiles[self.monitor_profile_id]
        if {
            "Background_Luminance",
            "Background_Screen_intensity",
        }.issubset(values):
            profile.validate_luminance_pair(
                luminance_cdm2=float(values["Background_Luminance"]),
                screen_intensity=float(values["Background_Screen_intensity"]),
            )
        return values

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id not in {"back", "review"}:
            return

        # Screen-owned buttons must not bubble to PsyCoLabSetupApp's handler.
        event.stop()

        if button_id == "back":
            try:
                self.app.pop_screen()
            except Exception as exc:
                _report_ui_exception(self.app, exc, phase="tui_experiment_config_back")
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

        lines = [
            "[b]Review experiment[/b]",
            "",
            f"Data folder: {self.request.data_root}",
            f"Participant: {self.request.participant_id}",
            f"Session: {'Reuse previous setup (new run)' if self.request.session_mode == 'reuse' else 'New session'}",
            f"Experiment: {experiment.display_name}",
            f"Display: {profile.display_name}",
            f"Calibration status: {profile.calibration_status}",
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
                    "[yellow]This monitor profile does not yet contain a trusted luminance "
                    "command mapping. The selected physical luminance and digital intensity "
                    "will both be saved, but their pairing is marked manual/unverified.[/yellow]",
                ]
            )

        lines.extend(
            [
                "",
                "A new self-contained run folder will be created. Trial data are appended "
                "to trials.tsv, while the legacy response file is retained for compatibility.",
                "",
                "[yellow]The current CSF shader mathematics remain unchanged.[/yellow]",
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

        # Prevent the same button event from reaching the root setup handler.
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
    Screen {
        align: center middle;
    }

    #setup-body, #review-body {
        width: 90%;
        max-width: 110;
        height: auto;
        max-height: 95%;
        border: round $accent;
        padding: 1 2;
    }

    #config-body {
        width: 90%;
        max-width: 110;
        height: 95%;
        border: round $accent;
        padding: 1 2;
    }

    Label {
        margin-top: 1;
    }

    Input, Select {
        width: 100%;
    }

    .field-help {
        color: $text-muted;
        margin-bottom: 1;
    }

    .buttons {
        height: auto;
        margin-top: 2;
        align-horizontal: right;
    }

    Button {
        margin-left: 1;
    }

    #setup-status, #config-status, #review-status {
        min-height: 1;
        margin-top: 1;
    }
    """

    def __init__(self, *, repo_root: Path, data_root: Path) -> None:
        super().__init__()
        self.repo_root = repo_root.resolve()
        self.data_root = data_root.resolve()
        self.monitor_profiles = load_monitor_profiles(repo_root)

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
        profile_options = [
            (profile.display_name, profile.id) for profile in self.monitor_profiles.values()
        ]

        last_request, state, warning = self._initial_values()
        participant_default = last_request.participant_id if last_request else ""
        session_default = "reuse" if last_request else "new"
        experiment_default = (
            last_request.experiment_id
            if last_request and any(spec.id == last_request.experiment_id for spec in experiments)
            else experiments[0].id
        )
        monitor_default = (
            last_request.monitor_profile_id
            if last_request and last_request.monitor_profile_id in self.monitor_profiles
            else next(iter(self.monitor_profiles))
        )

        participants = list_participants(self.data_root)
        participant_text = ", ".join(participants) if participants else "None yet"
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
        with VerticalScroll(id="setup-body"):
            yield Static("[b]PsyCoLab[/b]\nPsychophysics Collaborative Lab")
            yield Static(
                "Choose where data should be stored, then configure the session. "
                "Experimental data must stay outside the Git repository."
            )

            yield Label("Data folder")
            yield Input(value=str(self.data_root), id="data-root")
            yield Static(
                "An adjacent folder is recommended. PsyCoLab writes psycolab_data_config.json "
                "at the top so the previous subject/experiment/settings can be reused.",
                classes="field-help",
            )
            yield Button("Load Data Folder", id="load-data-root")
            yield Static(last_summary, id="last-run-summary", classes="field-help")

            yield Label("Participant ID")
            yield Input(value=participant_default, placeholder="e.g. S001 or subject_1", id="participant")
            yield Static(
                f"Existing participant folders: {participant_text}",
                id="participants-summary",
                classes="field-help",
            )

            yield Label("Session")
            yield Select(
                [
                    ("New session", "new"),
                    ("Reuse previous setup (starts a new run)", "reuse"),
                ],
                value=session_default,
                allow_blank=False,
                id="session-mode",
            )

            yield Label("Experiment")
            yield Select(
                experiment_options,
                value=experiment_default,
                allow_blank=False,
                id="experiment",
            )

            yield Label("Display profile")
            yield Select(
                profile_options,
                value=monitor_default,
                allow_blank=False,
                id="monitor-profile",
            )

            yield Static("", id="setup-status")
            with Horizontal(classes="buttons"):
                yield Button("Exit", id="exit")
                yield Button("Configure Experiment", id="configure", variant="primary")
        yield Footer()

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
        self.query_one("#participants-summary", Static).update(
            "Existing participant folders: " + (", ".join(participants) if participants else "None yet")
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
            self.query_one("#session-mode", Select).value = "reuse"
            if any(spec.id == last_request.experiment_id for spec in list_experiments()):
                self.query_one("#experiment", Select).value = last_request.experiment_id
            if last_request.monitor_profile_id in self.monitor_profiles:
                self.query_one("#monitor-profile", Select).value = last_request.monitor_profile_id
        self.query_one("#last-run-summary", Static).update(summary)
        self.query_one("#data-root", Input).value = str(data_root)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        # Button.Pressed bubbles through Textual. Child screens own back/review/run
        # buttons; ignore them here before querying widgets that only exist on the
        # root setup screen. This prevents NoMatches on the final review page.
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
                status.update(f"[green]Loaded data folder: {self.data_root}[/green]")
            except Exception as exc:
                status.update(f"[red]{exc}[/red]")
            return

        if button_id != "configure":
            return

        try:
            data_root = self._selected_data_root(create=True)
            self.data_root = data_root
            participant = validate_participant_id(self.query_one("#participant", Input).value)
            session_mode = self.query_one("#session-mode", Select).value
            experiment_id = self.query_one("#experiment", Select).value
            monitor_id = self.query_one("#monitor-profile", Select).value

            if session_mode is Select.BLANK or experiment_id is Select.BLANK or monitor_id is Select.BLANK:
                raise ValueError("Session, experiment and display profile must be selected.")

            experiment = get_experiment(str(experiment_id))
            monitor_id = str(monitor_id)
            if experiment.compatible_monitor_profiles and monitor_id not in experiment.compatible_monitor_profiles:
                raise ValueError("The selected experiment is not yet validated for that display profile.")

            defaults = experiment.field_defaults()
            if session_mode == "reuse":
                state = load_workspace_state(data_root)
                previous = request_from_workspace_state(state)
                if previous is None:
                    raise ValueError(
                        "No previous PsyCoLab setup exists in this data folder. "
                        "Choose 'New session' instead."
                    )
                if previous.experiment_id != experiment.id:
                    raise ValueError(
                        "The saved setup belongs to a different experiment. "
                        "Choose that experiment or start a new session."
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


def run_setup_tui(*, repo_root: Path, data_root: Path) -> SetupRequest | None:
    app = PsyCoLabSetupApp(repo_root=repo_root, data_root=data_root)
    return app.run()
