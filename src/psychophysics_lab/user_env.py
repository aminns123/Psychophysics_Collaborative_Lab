"""Authoring-only workspace: preview and virtual responses before publication.

USER_env is a dependency virtual environment, NOT an OS security sandbox. Its
Python can access the user's files; only run scientific modules you trust.
Never create human data or certify physical hardware from this workbench.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.widgets import Button, Header, Footer, Input, Label, Select, Static, TextArea

from .authoring import inventory, scaffold_draft, mark_tested, publish, load_authored
from .experiments.registry import get_experiment, list_experiments
from .stimuli.registry import get_stimulus, list_stimuli
from .ui.editor import open_source
from .ui.source_view import SourceView
from .paths import find_repo_root


@dataclass(frozen=True)
class UserEnvRequest:
    """Launch the independent researcher test workspace after Textual closes."""


@dataclass(frozen=True)
class DeveloperAction:
    operation: str
    identifier: str
    values: dict


def user_data_root(repo_root: Path) -> Path:
    # Never save synthetic development records under the human experiment root.
    import hashlib
    suffix = hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:12]
    return Path.home() / "PsyCoLab_USER_env_data" / suffix


def _source_files(repo_root: Path, kind: str, identity: str) -> tuple[Path, ...]:
    from .authoring import KINDS
    paths = [repo_root / "src" / "psychophysics_lab" / KINDS[kind] / (identity + ".py")]
    if kind in {"stimulus", "experiment"}:
        paths.append(repo_root / "configs" / KINDS[kind] / (identity + ".json"))
    return tuple(p for p in paths if p.is_file())


def _registered(repo_root: Path, kind: str):
    authored = tuple(i.name for i in inventory(repo_root) if i.kind == kind)
    try:
        present = [item.id for item in (list_experiments() if kind == "experiment" else list_stimuli())]
    except (ValueError, ImportError):
        present = []
    return tuple(sorted(set(authored) | set(present)))


def _validate_selected_values(identity: str, text: str) -> dict:
    values = json.loads(text)
    if not isinstance(values, dict):
        raise ValueError("Experiment configuration must be a JSON object.")
    # The same public schema is used in Configure Experiment and human preflight.
    return get_experiment(identity).normalise_values(values)


class UserEnvApp(App):
    TITLE = "PsyCoLab | USER_env"
    SUB_TITLE = "Draft → Preview → Simulate → Ready (never human acquisition)"
    CSS = """
    Screen { layout: vertical; }
    #dev-body { height: 1fr; border: round $accent; padding: 1 2; }
    Input, Select { width: 100%; }
    TextArea { height: 13; border: round $panel; }
    .dev-buttons { height: auto; }
    .dev-buttons Button { min-width: 17; }
    .dev-status { margin: 1 0; border: solid $warning; padding: 1; }
    """

    def __init__(self, repo_root: Path, message: str = ""):
        super().__init__()
        self.repo_root = repo_root.resolve()
        self.message = message
        self.config_drafts = {}

    def compose(self) -> ComposeResult:
        experiments = _registered(self.repo_root, "experiment")
        stimuli = _registered(self.repo_root, "stimulus")
        with Vertical():
            yield Header(show_clock=True)
            with VerticalScroll(id="dev-body"):
                yield Static("[b]USER_env DEVELOPMENT WORKBENCH[/b]\nIndependent software testing: NO physical calibration, NO human data. Edit trusted local Python modules and JSON presets.")
                yield Static(self.message or "Create a draft or choose a registered example, then simulate.", id="dev-status", classes="dev-status")
                yield Label("Build a stimulus (new Python + parameter JSON)")
                yield Input(placeholder="e.g. student_ellipse", id="dev-new-stimulus")
                with Horizontal(classes="dev-buttons"):
                    yield Button("Create stimulus draft", id="dev-create-stimulus")
                yield Label("Build an experiment (new Python + timeline JSON)")
                yield Input(placeholder="e.g. student_flanker", id="dev-new-experiment")
                with Horizontal(classes="dev-buttons"):
                    yield Button("Create experiment draft", id="dev-create-experiment")
                    yield Button("Refresh components", id="dev-refresh")
                yield Label("Experiment to edit / simulate")
                yield Select([(name, name) for name in experiments], value=experiments[0] if experiments else Select.BLANK,
                             allow_blank=not experiments, id="dev-experiment")
                with Horizontal(classes="dev-buttons"):
                    yield Button("Open experiment.py", id="dev-source-experiment")
                    yield Button("Open timeline JSON", id="dev-json-experiment")
                yield Label("Experiment configuration (same field names as normal Configure Experiment)")
                yield TextArea("{}", language="json", id="dev-values")
                with Horizontal(classes="dev-buttons"):
                    yield Button("Test experiment (virtual)", id="dev-test", variant="primary")
                    yield Button("Mark experiment Ready", id="dev-publish-experiment")
                yield Label("Stimulus to edit / preview")
                yield Select([(name, name) for name in stimuli], value=stimuli[0] if stimuli else Select.BLANK,
                             allow_blank=not stimuli, id="dev-stimulus")
                with Horizontal(classes="dev-buttons"):
                    yield Button("Open stimulus.py", id="dev-source-stimulus")
                    yield Button("Open parameter JSON", id="dev-json-stimulus")
                with Horizontal(classes="dev-buttons"):
                    yield Button("Preview stimulus", id="dev-preview")
                    yield Button("Mark stimulus Ready", id="dev-publish-stimulus")
                yield Static("[b]Authoring state[/b] — Draft files stay out of the normal experiment run catalogue. After successful software tests, Mark Ready and return to the normal TUI. This does not qualify a monitor or experiment for human acquisition.", id="dev-inventory")
                yield Button("Exit USER_env", id="dev-exit")
            yield Footer()

    def on_mount(self):
        self._show_inventory()
        self._config_for_selected()

    def _show_inventory(self):
        rows = inventory(self.repo_root)
        text = "\n".join(f"{x.kind}: {x.name} — {x.status}" for x in rows) or "No researcher-authored components yet."
        self.query_one("#dev-inventory", Static).update("[b]Authoring inventory[/b]\n" + text)

    def _config_for_selected(self):
        value = self.query_one("#dev-experiment", Select).value
        if not isinstance(value, str):
            return
        previous = self.config_drafts.get(value)
        try:
            spec = get_experiment(value)
            self.query_one("#dev-values", TextArea).text = previous or json.dumps(spec.field_defaults(), indent=2)
        except Exception as exc:
            self.query_one("#dev-status", Static).update(f"Draft not yet loaded: {exc}. Click Refresh components or test in a fresh interpreter.")

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "dev-experiment":
            self._config_for_selected()

    def _notice(self, message: str, error: bool = False):
        self.query_one("#dev-status", Static).update(("[red]" if error else "[green]") + message + ("[/red]" if error else "[/green]"))

    def _open(self, kind: str, identity: str, json_file: bool):
        files = _source_files(self.repo_root, kind, identity)
        if not files or (json_file and len(files) < 2):
            self._notice("No source/JSON file available for this component.", True)
            return
        path = files[1] if json_file else files[0]
        try:
            open_source(self.repo_root, path)
            self._notice(f"Opened {path.relative_to(self.repo_root)}")
        except (OSError, ValueError):
            self.push_screen(SourceView(path))
            self._notice("No external editor found; opened read-only source. Install VS Code to edit.")

    def on_button_pressed(self, event: Button.Pressed):
        key = event.button.id
        event.stop()
        try:
            if key == "dev-exit":
                self.exit()
                return
            if key in {"dev-create-stimulus", "dev-create-experiment"}:
                kind = "stimulus" if key == "dev-create-stimulus" else "experiment"
                name = self.query_one("#dev-new-" + kind, Input).value.strip()
                paths = scaffold_draft(self.repo_root, name, kind)
                self._notice(f"Created DRAFT {name}. Edit the code and JSON, preview/test, then mark Ready.")
                self._open(kind, name, False)
                self._update_choices(kind, name)
                self._show_inventory()
                return
            if key == "dev-refresh":
                failures = load_authored(self.repo_root, include_drafts=True, tolerate_errors=True)
                if failures:
                    self._notice("Some drafts could not load: " + "; ".join(f"{key} {value}" for key, value in failures.items()), True)
                self._update_choices("experiment")
                self._update_choices("stimulus")
                self._config_for_selected()
                self._show_inventory()
                self._notice("Component list refreshed. Edited Python code is always freshly imported by the test subprocess.")
                return
            if key in {"dev-source-experiment", "dev-json-experiment", "dev-source-stimulus", "dev-json-stimulus"}:
                kind = "experiment" if "experiment" in key else "stimulus"
                identity = self.query_one("#dev-" + kind, Select).value
                if isinstance(identity, str):
                    self._open(kind, identity, "json" in key)
                return
            if key in {"dev-test", "dev-preview"}:
                kind = "experiment" if key == "dev-test" else "stimulus"
                identity = self.query_one("#dev-" + kind, Select).value
                if not isinstance(identity, str):
                    raise ValueError("Choose a component first.")
                values = json.loads(self.query_one("#dev-values", TextArea).text) if kind == "experiment" else {}
                if not isinstance(values, dict):
                    raise ValueError("Experiment configuration must be a JSON object.")
                self.exit(DeveloperAction("test" if kind == "experiment" else "preview", identity, values))
                return
            if key in {"dev-publish-experiment", "dev-publish-stimulus"}:
                kind = "experiment" if "experiment" in key else "stimulus"
                identity = self.query_one("#dev-" + kind, Select).value
                if not isinstance(identity, str):
                    raise ValueError("Select a component first.")
                publish(self.repo_root, kind, identity)
                self._show_inventory()
                self._notice(f"{identity} marked READY after tested source hash matched. Return to normal TUI to run; physical qualifications are still required for humans.")
                return
        except Exception as exc:
            self._notice(f"{type(exc).__name__}: {exc}", True)

    def _update_choices(self, kind: str, select_value=None):
        names = _registered(self.repo_root, kind)
        widget = self.query_one("#dev-" + kind, Select)
        widget.set_options([(name, name) for name in names])
        if select_value in names:
            widget.value = select_value
        elif names and not isinstance(widget.value, str):
            widget.value = names[0]


def _workbench_action(repo_root: Path, action: DeveloperAction) -> str:
    """Run in a fresh Python subprocess, so file edits cannot use stale modules."""
    command = [sys.executable, "-m", "psychophysics_lab", "--user-env-action", action.operation,
               "--user-env-identity", action.identifier, "--user-env-values", json.dumps(action.values)]
    try:
        completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, timeout=120,
                                   check=False)
    except subprocess.TimeoutExpired:
        return "[red]Developer test timed out after 120 seconds; no human data created.[/red]"
    tail = "\n".join((completed.stdout + "\n" + completed.stderr).strip().splitlines()[-12:])
    return ("[green]Developer test PASS[/green]\n" if completed.returncode == 0 else "[red]Developer test FAILED[/red]\n") + tail.replace("[", "\\[")


def run_user_env(repo_root: Path) -> None:
    message = ""
    while True:
        try:
            failures = load_authored(repo_root, include_drafts=True, tolerate_errors=True)
            if failures:
                message = "[yellow]Incomplete drafts: " + "; ".join(f"{key} {value}" for key, value in failures.items()) + "[/yellow]"
        except Exception as exc:
            message = f"[red]Draft import error: {exc}. Edit the broken source or JSON, then use Test again.[/red]"
        action = UserEnvApp(repo_root, message).run()
        if not isinstance(action, DeveloperAction):
            return
        message = _workbench_action(repo_root, action)


def preview_trial_storyboard(repo_root: Path, spec, values: dict, destination: Path) -> Path | None:
    """Illustrate the default *static* phase order; no real display or measured timing.

    Actual per-trial parameter overrides and dynamic shaders cannot be inferred
    solely from a timeline, so this file is explicitly an illustration.
    """
    from .core.timeline import load_timeline
    from .config.stimulus_parameters import load_parameters
    from .core.presentation import render_pixels
    import matplotlib.pyplot as plt
    import numpy as np

    path = repo_root / "configs" / "experiments" / (spec.id + ".json")
    if not path.is_file():
        return None
    timeline = load_timeline(path, timings=values, slots=spec.stimulus_slots)
    count = len(timeline.phases)
    fig, axes = plt.subplots(1, count, figsize=(max(6, 2.4 * count), 3))
    axes = np.atleast_1d(axes)
    try:
        for ax, phase in zip(axes, timeline.phases):
            pixels = np.full((128, 128), 128, dtype=np.uint8)
            if phase.slot in spec.stimulus_defaults:
                stimulus = get_stimulus(spec.stimulus_defaults[phase.slot])
                if stimulus.render is not None and stimulus.default_config:
                    selection = load_parameters(repo_root / stimulus.default_config, stimulus)
                    pixels = render_pixels(stimulus, selection["document"]["parameters"], pixels=(128,128))
            ax.imshow(pixels, cmap="gray", vmin=0, vmax=255)
            ax.set_title(f"{phase.name}\n{phase.duration_ms} ms" if phase.kind == "show" else f"{phase.name}\nwait/key", fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle("Illustrative default sequence — NOT measured photon timing", fontsize=10)
        fig.tight_layout()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destination, dpi=120)
    finally:
        plt.close(fig)
    return destination


def execute_user_action(repo_root: Path, operation: str, identity: str, values: dict) -> int:
    """CLI subprocess: software-only and synthetic, never real participant acquisition."""
    problems = load_authored(repo_root, include_drafts=True, tolerate_errors=True)
    if any(key.endswith(":" + identity) for key in problems):
        raise ValueError("Draft failed to import: " + "; ".join(f"{k} {v}" for k,v in problems.items() if k.endswith(":" + identity)))
    root = user_data_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    marker = root / ".psycolab_user_env.json"
    if not marker.exists():
        marker.write_text(json.dumps({"schema_version": 1, "purpose": "development_only",
                                      "human_acquisition_allowed": False}) + "\n", encoding="utf-8")
    else:
        expected = {"schema_version": 1, "purpose": "development_only", "human_acquisition_allowed": False}
        if marker.is_symlink() or json.loads(marker.read_text(encoding="utf-8")) != expected:
            raise ValueError("USER_env marker invalid; refusing to reuse development output directory.")
    if operation == "preview":
        from .config.stimulus_parameters import load_parameters
        from .core.presentation import preview_stimulus
        stimulus = get_stimulus(identity)
        if not stimulus.default_config:
            raise ValueError("This stimulus has no JSON-based preview; use its existing calibration page.")
        selected = load_parameters(repo_root / stimulus.default_config, stimulus)
        preview_folder = root / "previews"
        preview_folder.mkdir(parents=True, exist_ok=True)
        path = preview_folder / (identity + ".png")
        preview_stimulus(identity, selected["document"]["parameters"], path)
        if any(item.name == identity and item.kind == "stimulus" for item in inventory(repo_root)):
            mark_tested(repo_root, "stimulus", identity)
        print("Preview saved:", path)
        print("This is a digital illustration, NOT physically calibrated luminance or timing.")
        return 0
    if operation == "test":
        from simulations.run import simulate
        from scripts.validate_run import validate_run
        spec = get_experiment(identity)
        if not spec.supports_simulation:
            raise ValueError("This experiment does not declare virtual observer support.")
        selected = spec.normalise_values(values)
        artifacts, _ = simulate(repo_root=repo_root, data_root=root, experiment_id=identity,
                                values=selected, analyse=False)
        failures = [check for check in validate_run(artifacts.run_directory) if not check.passed]
        if artifacts.status != "completed" or failures:
            raise ValueError(f"Simulation status: {artifacts.status}; validation failures: {failures}")
        try:
            storyboard = preview_trial_storyboard(repo_root, spec, selected,
                root / "previews" / (identity + "_timeline.png"))
            if storyboard is not None:
                print("Static phase storyboard:", storyboard)
        except (ValueError, KeyError, ImportError) as exc:
            print("Storyboard unavailable (virtual run remains validated):", exc)
        if any(item.name == identity and item.kind == "experiment" for item in inventory(repo_root)):
            mark_tested(repo_root, "experiment", identity)
        print("VALID virtual run:", artifacts.run_directory)
        print("NO human participant / physical display / verified calibration was used.")
        return 0
    raise ValueError("Unknown developer action; use 'preview' or 'test'.")
