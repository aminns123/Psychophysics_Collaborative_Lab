"""Draft testing and Ready controls embedded in the normal authoring pages."""
from pathlib import Path
import subprocess
import os
import sys
from textual import work
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Select, Button, Static
from ..authoring import inventory, fingerprint


class RetireExperimentDialog(ModalScreen[bool]):
    """Confirm identity and consequences; no source or run data are deleted."""
    DEFAULT_CSS = """
    RetireExperimentDialog { align: center middle; }
    #retire-dialog { width: 78; max-width: 94%; height: auto;
                     padding: 2; border: solid $warning; background: $surface; }
    """

    BINDINGS = [("escape", "cancel", "Cancel retirement")]

    def __init__(self, name, origin, status, source):
        super().__init__()
        self.experiment_id, self.origin, self.current_status, self.source = name, origin, status, source

    def compose(self):
        with Vertical(id="retire-dialog"):
            yield Static("RETIRE EXPERIMENT", classes="section-title")
            yield Static(
                f"ID: {self.experiment_id}\nOrigin: {self.origin}\n"
                f"Current state: {self.current_status}\nSource: {self.source}\n\n"
                "Retiring removes this experiment from the runnable catalogue. "
                "Its Python source, presets, calibration and previously recorded "
                "scientific data are NOT deleted. To use it again, explicitly "
                "Restore to Draft, then Test and Mark Ready. "
                "If the source is missing unexpectedly, cancel and investigate.",
                markup=False,
            )
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="retire-cancel")
                yield Button("Retire experiment", variant="warning", id="retire-confirm")

    def action_cancel(self):
        self.dismiss(False)

    def on_button_pressed(self, event):
        if event.button.id in {"retire-cancel", "retire-confirm"}:
            event.stop()
            self.dismiss(event.button.id == "retire-confirm")


class AuthoringPanel(Vertical):
    DEFAULT_CSS = "AuthoringPanel { height: auto; } AuthoringPanel Static { height: auto; }"

    def __init__(self, kind):
        super().__init__(id="authoring-panel")
        self.kind = kind

    def compose(self):
        yield Static("Your components: edit Python (optional JSON presets), preview or simulate, then mark the tested version Ready.")
        yield Select([], prompt="Choose your draft or Ready component", id="author-component")
        with Horizontal(classes="buttons"):
            yield Button("Edit Python", id="author-python")
            yield Button("Optional JSON preset", id="author-json")
            yield Button("Preview / validate" if self.kind == "stimulus" else "Simulate / validate", id="author-test")
            yield Button("Mark Ready", id="author-ready")
            if self.kind == "experiment":
                yield Button("Retire experiment", variant="warning", id="author-retire")
                yield Button("Restore retired", id="author-restore")
            yield Button("Refresh list", id="author-refresh")
        yield Static("", id="author-result", markup=False)

    def on_mount(self):
        self.refresh_inventory()

    def refresh_inventory(self):
        records = [i for i in inventory(self.app.repo_root) if i.kind == self.kind]
        from .. import extensions
        from ..authoring import Component
        try:
            self._external = {row['id']:row for row in extensions.inventory(self.app.repo_root) if row['kind'] == self.kind}
        except (ValueError, OSError):
            self._external = {}
        records.extend(Component(self.kind, row['id'], row['status']) for row in self._external.values())
        selected = self.query_one("#author-component", Select)
        previous = selected.value
        options = []
        for item in records:
            try:
                tested = bool(item.tested_fingerprint and item.tested_fingerprint == fingerprint(self.app.repo_root, item))
            except (OSError, ValueError):
                tested = False
            if item.name in self._external:
                tested = self._external[item.name]["status"] in {"tested", "ready"}
            options.append((f"{item.name} — {item.status}, {'tested' if tested else 'needs testing'}", item.name))
        self._status_by_name = {item.name: item.status for item in records}
        selected.set_options(options)
        if records:
            selected.value = previous if previous in self._status_by_name else records[-1].name
        self._sync_action_buttons()

    def _sync_action_buttons(self):
        if self.kind != "experiment":
            return
        name = self.query_one("#author-component", Select).value
        status = self._status_by_name.get(name)
        self.query_one("#author-retire", Button).disabled = status is None or status == "retired"
        self.query_one("#author-restore", Button).disabled = status != "retired"
        self.query_one("#author-test", Button).disabled = status is None or status == "retired"
        self.query_one("#author-ready", Button).disabled = status is None or status == "retired"

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "author-component":
            self._sync_action_buttons()

    def _finish_retirement(self, name, is_external, confirmed):
        if not confirmed:
            self.query_one("#author-result", Static).update("Retirement cancelled; nothing changed.")
            return
        try:
            if is_external:
                from .. import extensions
                extensions.retire(self.app.repo_root, "experiment", name)
            else:
                from ..authoring import retire
                retire(self.app.repo_root, "experiment", name)
                # Remove only this already-registered identity in the current
                # process. All other experiment/stimulus entries are unchanged.
                from ..experiments._internal import registry
                registry._REGISTRY.pop(name, None)
            self.refresh_inventory()
            self.query_one("#author-result", Static).update(
                f"{name} retired. Python source, presets and acquired runs preserved. "
                "Use Refresh (F5) to rebuild the catalogue. Restore → Test → Ready to reactivate."
            )
        except (ValueError, OSError) as exc:
            self.query_one("#author-result", Static).update(f"Could not retire {name}: {exc}")

    def _restore_retired(self, name, is_external):
        try:
            if is_external:
                from .. import extensions
                extensions.restore(self.app.repo_root, "experiment", name)
            else:
                from ..authoring import restore
                restore(self.app.repo_root, "experiment", name)
            self.refresh_inventory()
            self.query_one("#author-result", Static).update(
                f"{name} restored to Draft, NOT Ready. Run Test and Mark Ready, "
                "then Refresh (F5) before acquisition."
            )
        except (ValueError, OSError) as exc:
            self.query_one("#author-result", Static).update(f"Could not restore {name}: {exc}")

    def on_button_pressed(self, event):
        identity = event.button.id or ""
        if not identity.startswith("author-"):
            return
        event.stop()
        if identity == "author-refresh":
            self.refresh_inventory()
            return
        name = self.query_one("#author-component", Select).value
        if name is Select.BLANK:
            self.query_one("#author-result", Static).update("Choose a component first.")
            return
        if identity == "author-retire" and self.kind == "experiment":
            external = name in getattr(self, "_external", {})
            status = self._status_by_name.get(name)
            if status is None or status == "retired":
                self.query_one("#author-result", Static).update("Choose an active researcher-authored experiment.")
                return
            source = (self._external[name]["path"] if external else
                      self.app.repo_root / "src/psychophysics_lab/experiments" / (name + ".py"))
            self.app.push_screen(
                RetireExperimentDialog(str(name), "trusted laboratory extension" if external
                                       else "project-published researcher experiment", status, str(source)),
                callback=lambda confirmed: self._finish_retirement(str(name), external, confirmed),
            )
            return
        if identity == "author-restore" and self.kind == "experiment":
            self._restore_retired(str(name), name in getattr(self, "_external", {}))
            return
        if identity in {"author-python", "author-json"}:
            folder = "stimuli" if self.kind == "stimulus" else "experiments"
            relative = (f"src/psychophysics_lab/{folder}/{name}.py" if identity == "author-python"
                        else f"configs/{folder}/{name}.json")
            if name in self._external:
                if identity == "author-python":
                    path = self._external[name]["path"]
                else:
                    # The laboratory's optional JSON is not a framework
                    # configs/<kind>/<id>.json file. For Ready components,
                    # use the registered source root and declared path.
                    from ..extensions import source_path
                    from ..experiments._internal.registry import get_experiment
                    from ..stimuli.registry import get_stimulus
                    try:
                        spec = (get_experiment(name) if self.kind == "experiment"
                                else get_stimulus(name))
                        path = (source_path(self.app.repo_root, spec, spec.default_config)
                                if spec.default_config else None)
                    except (KeyError, ValueError, OSError):
                        path = None  # Draft has no registered SPEC yet.
            else:
                path = self.app.repo_root / relative
            if path is None or not path.is_file():
                self.query_one("#author-result", Static).update("No optional preset: defaults are declared in the Python file.")
                return
            self.app.inspect_source(path)
            return
        self.perform(identity, str(name))

    @work(thread=True, exclusive=True, group="authoring")
    def perform(self, operation, name):
        def update(message):
            self.query_one("#author-result", Static).update(message)
        def disable(disabled):
            for button in self.query(Button):
                button.disabled = disabled
        self.app.call_from_thread(disable, True)
        self.app.call_from_thread(update, "Running software validation…" if operation == "author-test" else "Checking tested revision…")
        args = (["--dev-ready", self.kind, name] if operation == "author-ready" else
                ["--dev-preview" if self.kind == "stimulus" else "--dev-test", name])
        try:
            result = subprocess.run([sys.executable, "-m", "psychophysics_lab", *args],
                                    cwd=self.app.repo_root, env=os.environ | {"PSYCOLAB_REPO_ROOT": str(self.app.repo_root)}, capture_output=True, text=True,
                                    timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            message = (result.stdout + result.stderr).strip()
            if result.returncode:
                message = "Validation failed. Edit the component and try again.\n" + message
            elif operation == "author-ready":
                # New modules enter the same registries. Existing imported
                # modules require a restart to avoid stale cross-module references.
                module_name = f"psychophysics_lab.{'stimuli' if self.kind == 'stimulus' else 'experiments'}.{name}"
                if name in getattr(self,"_external",{}) or module_name in sys.modules:
                    message += "\nUse Refresh (F5) to load the newly tested revision."
                else:
                    from ..authoring import load_authored
                    problems = load_authored(self.app.repo_root, tolerate_errors=True)
                    if problems:
                        message += "\nUse Refresh (F5) to load changed modules: " + str(problems)
            self.app.call_from_thread(update, message)
            self.app.call_from_thread(self.refresh_inventory)
        except Exception as exc:
            self.app.call_from_thread(update, f"Could not finish: {exc}")
        finally:
            self.app.call_from_thread(disable, False)
