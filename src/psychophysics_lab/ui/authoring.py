"""Draft testing and Ready controls embedded in the normal authoring pages."""
import asyncio
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
                yield Button("Prepare official contribution", id="author-contribute")
                yield Button("What does Test check?", id="author-test-info")
                yield Button("Save Test as reference", id="author-save-reference")
                yield Button("Compare with reference", id="author-compare-reference")
                yield Button("Retire experiment", variant="warning", id="author-retire")
                yield Button("Restore retired", id="author-restore")
            yield Button("Refresh list", id="author-refresh")
        yield Static("", id="author-result", markup=False)

    def on_mount(self):
        self.refresh_inventory()

    def refresh_inventory(self):
        self._apply_inventory(*self._collect_inventory())

    async def _refresh_inventory(self):
        self._apply_inventory(*await asyncio.to_thread(self._collect_inventory))

    def _collect_inventory(self):
        records = [i for i in inventory(self.app.repo_root) if i.kind == self.kind]
        from .. import extensions
        from ..authoring import Component
        try:
            external = {row['id']: row for row in extensions.inventory(self.app.repo_root) if row['kind'] == self.kind}
        except (ValueError, OSError):
            external = {}
        records.extend(Component(self.kind, row['id'], row['status']) for row in external.values())
        options = []
        for item in records:
            try:
                tested = bool(item.tested_fingerprint and item.tested_fingerprint == fingerprint(self.app.repo_root, item))
            except (OSError, ValueError):
                tested = False
            if item.name in external:
                tested = external[item.name]["status"] in {"tested", "ready"}
            options.append((f"{item.name} — {item.status}, {'tested' if tested else 'needs testing'}", item.name))
        return external, records, options

    def _apply_inventory(self, external, records, options):
        self._external = external
        selected = self.query_one("#author-component", Select)
        previous = selected.value
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
        self.query_one("#author-contribute", Button).disabled = (
            status != "ready" or name not in getattr(self, "_external", {})
        )
        for action in ("author-save-reference", "author-compare-reference"):
            self.query_one("#" + action, Button).disabled = status is None or status == "retired"

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
        if identity == "author-test-info" and self.kind == "experiment":
            self.query_one("#author-result", Static).update(
                "SOFTWARE TEST (automatic; no custom test Python needed):\n"
                "1. Parse effective experiment settings and check scientific parameter validators.\n"
                "2. Check every declared stimulus ID/family and session-start event.\n"
                "3. Check the selected method and simulate its actual trial events/responses.\n"
                "4. Validate saved data and report pass/fail in USER_env_data.\n"
                "5. Mark Ready only after this exact source revision passes.\n\n"
                "RESEARCHER REVIEW (not automated): confirm intended stimulus geometry, "
                "overlap order, conditions, response mapping, thresholds and contrast units; "
                "then qualify the actual display, luminance, timing and input devices. "
                "Ready is software readiness, NOT scientific approval."
            )
            return
        if identity == "author-refresh":
            loading = getattr(self.app, "loading", None)
            if loading is None:
                self.refresh_inventory()
            else:
                loading.run(self.screen, self._refresh_inventory, label="Checking lab components")
            return
        name = self.query_one("#author-component", Select).value
        if name is Select.BLANK:
            self.query_one("#author-result", Static).update("Choose a component first.")
            return
        if identity == "author-contribute" and self.kind == "experiment":
            if name not in getattr(self, "_external", {}):
                self.query_one("#author-result", Static).update(
                    "This is already a published repository experiment; "
                    "only an external laboratory experiment needs official contribution."
                )
                return
            try:
                from ..laboratory_import import prepare_official_contribution
                folder = prepare_official_contribution(self.app.repo_root, str(name))
                self.query_one("#author-result", Static).update(
                    "OFFICIAL CONTRIBUTION PACKAGE PREPARED: " + str(folder) + "\n"
                    "The exact local experiment source, relevant laboratory stimuli and "
                    "source hashes are preserved for review. Nothing has been merged or "
                    "copied into PsyCoLab's official experiments. Ask a maintainer to "
                    "review the proposed IDs, science and source and submit a pull request."
                )
            except (ValueError, OSError, KeyError) as exc:
                self.query_one("#author-result", Static).update(
                    "Could not prepare contribution: " + str(exc)
                )
            return
        if identity == "author-save-reference" and self.kind == "experiment":
            try:
                from ..experiment_reference import save_reference
                path = save_reference(self.app.repo_root, str(name))
                self.query_one("#author-result", Static).update(
                    f"REFERENCE SAVED (software only): {path}\n"
                    "Use Compare with reference after changing Python or settings. "
                    "PsyCoLab compares synthetic events and records for you; "
                    "the researcher decides whether differences are intentional."
                )
            except (ValueError, OSError, KeyError) as exc:
                self.query_one("#author-result", Static).update(str(exc))
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
        worker = self.perform(identity, str(name))
        loading = getattr(self.app, "loading", None)
        if loading is not None and (identity == "author-ready" or self.kind == "stimulus"):
            # Experiment authoring tests run a virtual acquisition in the child
            # process. Keep the existing static status during that execution.
            label = "Checking tested revision" if identity == "author-ready" else "Preparing stimulus preview"
            loading.watch(worker, label)

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
            elif operation == "author-compare-reference":
                from ..experiment_reference import compare_latest_reference
                comparison = compare_latest_reference(self.app.repo_root, name)
                if comparison["same_scientific_behaviour"]:
                    message += "\nREFERENCE COMPARISON: No changes detected in the synthetic trial records/events."
                else:
                    message += "\nREFERENCE COMPARISON: Behaviour differences require researcher review:"
                    message += "".join("\n- " + item for item in comparison["differences"])
                if comparison["source_changed_since_reference"]:
                    message += "\nScientific source/dependencies changed since the stored reference."
                message += "\nReference: " + comparison["reference_path"]
                message += "\nThis is software evidence, not scientific or physical qualification."
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
