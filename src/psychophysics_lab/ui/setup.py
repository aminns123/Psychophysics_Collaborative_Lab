from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from ..config.models import SetupRequest
from ..config.monitor import load_monitor_profiles
from ..data.participants import list_participants, participant_directory, validate_participant_id
from ..experiments.registry import get_experiment, list_experiments
from ..experiments.spec import ConfigField, ExperimentSpec


def _field_widget_id(field: ConfigField) -> str:
    safe = field.key.replace("_", "-")
    return f"field-{safe}"


class ExperimentConfigScreen(Screen):
    def __init__(
        self,
        *,
        participant_id: str,
        session_mode: str,
        experiment: ExperimentSpec,
        monitor_profile_id: str,
        defaults: dict[str, Any],
    ) -> None:
        super().__init__()
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
                    yield Input(
                        value="" if value is None else str(value),
                        id=widget_id,
                    )
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
        return self.experiment.normalise_values(values)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        if event.button.id != "review":
            return

        status = self.query_one("#config-status", Static)
        try:
            values = self._collect()
        except Exception as exc:
            status.update(f"[red]{exc}[/red]")
            return

        request = SetupRequest(
            participant_id=self.participant_id,
            session_mode=self.session_mode,
            experiment_id=self.experiment.id,
            monitor_profile_id=self.monitor_profile_id,
            experiment_values=values,
        )
        self.app.push_screen(ReviewScreen(request=request))


class ReviewScreen(Screen):
    def __init__(self, *, request: SetupRequest) -> None:
        super().__init__()
        self.request = request

    def compose(self) -> ComposeResult:
        experiment = get_experiment(self.request.experiment_id)
        profiles = self.app.monitor_profiles
        profile = profiles[self.request.monitor_profile_id]

        lines = [
            "[b]Review experiment[/b]",
            "",
            f"Participant: {self.request.participant_id}",
            f"Session: {'Reuse previous setup (new run)' if self.request.session_mode == 'reuse' else 'New session'}",
            f"Experiment: {experiment.display_name}",
            f"Display: {profile.display_name}",
            "",
            "[b]Experiment parameters[/b]",
        ]
        for field in experiment.fields:
            lines.append(f"{field.label}: {self.request.experiment_values[field.key]}")

        lines.extend(
            [
                "",
                f"Data root: {self.app.data_root}",
                "",
                "[yellow]The current CSF shader mathematics are preserved unchanged in public-v1.[/yellow]",
            ]
        )

        yield Header(show_clock=True)
        with Vertical(id="review-body"):
            yield Static("\n".join(lines), id="review-text")
            with Horizontal(classes="buttons"):
                yield Button("Back", id="back")
                yield Button("Run Experiment", id="run", variant="success")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "run":
            self.app.exit(self.request)


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

    #setup-status, #config-status {
        min-height: 1;
        margin-top: 1;
    }
    """

    def __init__(self, *, repo_root: Path, data_root: Path) -> None:
        super().__init__()
        self.repo_root = repo_root
        self.data_root = data_root
        self.monitor_profiles = load_monitor_profiles(repo_root)

    def compose(self) -> ComposeResult:
        experiments = list_experiments()
        experiment_options = [(spec.display_name, spec.id) for spec in experiments]

        profile_options = [
            (profile.display_name, profile.id)
            for profile in self.monitor_profiles.values()
        ]

        participants = list_participants(self.data_root)
        participant_text = ", ".join(participants) if participants else "None yet"

        yield Header(show_clock=True)
        with Vertical(id="setup-body"):
            yield Static("[b]PsyCoLab[/b]\nPsychophysics Collaborative Lab")
            yield Static(
                "Configure a session here. The Textual interface closes completely "
                "before the Pyglet/OpenGL experiment starts."
            )
            yield Label("Participant ID")
            yield Input(placeholder="e.g. S001 or subject_1", id="participant")
            yield Static(f"Existing participant folders: {participant_text}", classes="field-help")

            yield Label("Session")
            yield Select(
                [
                    ("New session", "new"),
                    ("Reuse previous setup (starts a new run)", "reuse"),
                ],
                value="new",
                allow_blank=False,
                id="session-mode",
            )

            yield Label("Experiment")
            yield Select(
                experiment_options,
                value=experiments[0].id,
                allow_blank=False,
                id="experiment",
            )

            yield Label("Display profile")
            yield Select(
                profile_options,
                value=next(iter(self.monitor_profiles)),
                allow_blank=False,
                id="monitor-profile",
            )

            yield Static("", id="setup-status")
            with Horizontal(classes="buttons"):
                yield Button("Exit", id="exit")
                yield Button("Configure Experiment", id="configure", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exit":
            self.exit(None)
            return
        if event.button.id != "configure":
            return

        status = self.query_one("#setup-status", Static)
        try:
            participant = validate_participant_id(self.query_one("#participant", Input).value)
            session_mode = self.query_one("#session-mode", Select).value
            experiment_id = self.query_one("#experiment", Select).value
            monitor_id = self.query_one("#monitor-profile", Select).value

            if session_mode is Select.BLANK or experiment_id is Select.BLANK or monitor_id is Select.BLANK:
                raise ValueError("Session, experiment and display profile must be selected.")

            experiment = get_experiment(str(experiment_id))
            monitor_id = str(monitor_id)

            if (
                experiment.compatible_monitor_profiles
                and monitor_id not in experiment.compatible_monitor_profiles
            ):
                raise ValueError(
                    "The selected experiment is not yet validated for that display profile."
                )

            defaults = experiment.field_defaults()
            if session_mode == "reuse":
                previous_path = participant_directory(self.data_root, participant) / "experiment_defined.json"
                if not previous_path.exists():
                    raise ValueError(
                        "No previous setup exists for this participant. "
                        "Choose 'New session' instead."
                    )
                previous = json.loads(previous_path.read_text(encoding="utf-8"))
                if previous.get("Experiment_Type") != experiment.legacy_experiment_type:
                    raise ValueError(
                        "The saved setup belongs to a different experiment. "
                        "Choose that experiment or start a new session."
                    )
                defaults = experiment.values_from_legacy_setup(previous)

            self.push_screen(
                ExperimentConfigScreen(
                    participant_id=participant,
                    session_mode=str(session_mode),
                    experiment=experiment,
                    monitor_profile_id=monitor_id,
                    defaults=defaults,
                )
            )
        except Exception as exc:
            status.update(f"[red]{exc}[/red]")


def run_setup_tui(*, repo_root: Path, data_root: Path) -> SetupRequest | None:
    app = PsyCoLabSetupApp(repo_root=repo_root, data_root=data_root)
    return app.run()
