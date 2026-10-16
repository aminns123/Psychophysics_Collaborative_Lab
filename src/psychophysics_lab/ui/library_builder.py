"""Library-first experiment builder inside the normal PsyCoLab TUI.

No new Python file is created for simple two-choice spatial tasks. Stimulus
choices come from the shared Ready library; JSON defines the scientific task.
"""
import os
from pathlib import Path
import subprocess
import sys

from textual import work
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Select, Static

from ..stimuli.registry import list_stimuli
from ..experiments.library_builder import create_design, inventory, DESIGNS


class LibraryExperimentBuilder(Vertical):
    DEFAULT_CSS = "LibraryExperimentBuilder { height: auto; } LibraryExperimentBuilder Static { height: auto; }"

    def compose(self):
        yield Static(
            "[b]No-Python experiment builder — spatial two-choice[/b]\n"
            "1. Build/validate a stimulus in Build Stimuli.\n"
            "2. Select registered fixation and probe stimuli below.\n"
            "3. Create an editable JSON experiment, simulate it, then Mark Ready.\n"
            "The same TrialTimeline handles stimulus presentation, recording and response."
        )
        with Horizontal(classes="buttons"):
            yield Select([], prompt="Fixation stimulus", id="lib-fixation")
            yield Select([], prompt="Probe stimulus", id="lib-probe")
        with Horizontal(classes="buttons"):
            yield Input(placeholder="experiment_name", id="lib-name")
            yield Input("2.0", placeholder="Probe distance in degrees", id="lib-distance")
            yield Button("Create JSON experiment", id="lib-create", variant="primary")
        yield Static("After creation: edit its JSON to change keys, timings, conditions or action order.")
        yield Select([], prompt="Choose JSON experiment", id="lib-existing")
        with Horizontal(classes="buttons"):
            yield Button("Inspect / edit JSON", id="lib-edit")
            yield Button("Simulate / validate", id="lib-test")
            yield Button("Mark Ready", id="lib-ready")
            yield Button("Refresh", id="lib-refresh")
        yield Static("", id="lib-message", markup=False)

    def on_mount(self):
        self.refresh_catalog()

    def refresh_catalog(self):
        stimuli = [s for s in list_stimuli() if s.render is not None and s.default_config]
        options = [(f"{s.display_name} ({s.id})", s.id) for s in stimuli]
        for widget, default in [("lib-fixation", "fixation_cross"), ("lib-probe", "vertical_line_probe")]:
            selected = self.query_one("#" + widget, Select)
            old = selected.value
            selected.set_options(options)
            ids = [s.id for s in stimuli]
            if ids:
                selected.value = old if old in ids else (default if default in ids else ids[0])
        catalog = inventory(self.app.repo_root)
        selector = self.query_one("#lib-existing", Select)
        old = selector.value
        selector.set_options([(f"{x['id']} — {x['status']}", x["id"]) for x in catalog])
        ids = [row["id"] for row in catalog]
        if ids:
            selector.value = old if old in ids else ids[-1]

    def refresh_experiment_choices(self, preferred):
        """Show newly published experiments in the normal Build Experiments list."""
        from ..experiments.registry import list_experiments
        from .setup import experiment_choice_label
        experiments = list_experiments()
        selector = self.screen.query_one("#inspect-experiment", Select)
        old = selector.value
        selector.set_options([(experiment_choice_label(spec, self.app.repo_root), spec.id)
                              for spec in experiments])
        ids = {spec.id for spec in experiments}
        selector.value = preferred if preferred in ids else (old if old in ids else experiments[0].id)
        self.screen._refresh()

    def on_button_pressed(self, event):
        control = event.button.id or ""
        if not control.startswith("lib-"):
            return
        event.stop()
        if control == "lib-refresh":
            self.refresh_catalog()
            return
        message = self.query_one("#lib-message", Static)
        try:
            if control == "lib-create":
                fixation = self.query_one("#lib-fixation", Select).value
                probe = self.query_one("#lib-probe", Select).value
                if fixation is Select.BLANK or probe is Select.BLANK:
                    raise ValueError("Choose existing Ready fixation and probe stimuli.")
                name = self.query_one("#lib-name", Input).value.strip()
                distance = float(self.query_one("#lib-distance", Input).value)
                path = create_design(self.app.repo_root, name, str(probe), str(fixation), distance)
                message.update(f"Created DRAFT: {path.relative_to(self.app.repo_root)}. Edit, simulate, then Mark Ready.")
                self.refresh_catalog()
                self.query_one("#lib-existing", Select).value = name
                self.app.inspect_source(path)
                return
            selected = self.query_one("#lib-existing", Select).value
            if selected is Select.BLANK:
                raise ValueError("Create or select an experiment.")
            name = str(selected)
            if control == "lib-edit":
                self.app.inspect_source(self.app.repo_root / DESIGNS / (name + ".json"))
                return
            if name == "probe_above_below":
                raise ValueError("The built-in demonstration is already tested. Create your own editable draft.")
            if control in ("lib-test", "lib-ready"):
                self.verify_async(control, name)
        except (ValueError, OSError) as exc:
            message.update(str(exc))

    @work(thread=True, exclusive=True, group="library-experiment")
    def verify_async(self, operation, name):
        def update(text):
            self.query_one("#lib-message", Static).update(text)
        def buttons(disabled):
            for button in self.query(Button):
                button.disabled = disabled
        self.app.call_from_thread(buttons, True)
        self.app.call_from_thread(update, "Testing virtual experiment…" if operation == "lib-test" else "Checking tested source versions…")
        cmd = ["--library-test" if operation == "lib-test" else "--library-ready", name]
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "psychophysics_lab", *cmd],
                cwd=self.app.repo_root,
                env=os.environ | {"PSYCOLAB_REPO_ROOT": str(self.app.repo_root)},
                capture_output=True, text=True, timeout=300,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            output = (proc.stdout + proc.stderr).strip()
            if proc.returncode:
                output = "Validation failed (nothing published):\n" + output
            elif operation == "lib-ready":
                from ..experiments.library_builder import load_library
                problems = load_library(self.app.repo_root, tolerate_errors=True)
                if problems:
                    output += "\nSome library modules need restart: " + str(problems)
                else:
                    output += "\nNew Ready experiments appear in the normal catalogue."
                    self.app.call_from_thread(self.refresh_experiment_choices, name)
            self.app.call_from_thread(update, output)
            self.app.call_from_thread(self.refresh_catalog)
        except Exception as exc:
            self.app.call_from_thread(update, f"Development validation failed: {exc}")
        finally:
            self.app.call_from_thread(buttons, False)
