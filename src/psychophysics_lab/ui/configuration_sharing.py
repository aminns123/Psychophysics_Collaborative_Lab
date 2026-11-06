"""Review-adjacent file sharing; scientific controls remain in existing editors."""
from pathlib import Path

from rich.text import Text
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Input, Label, Static, DataTable

from ..config.sharing import (CALIBRATION_NOTICE, digest, make_document, read_document,
                              save_local, validate_portable, write_export)


class JSONTree(DirectoryTree):
    def __init__(self, path, *, saved_only=False, **kwargs):
        self.saved_only = saved_only
        super().__init__(path, **kwargs)

    def filter_paths(self, paths):
        return [p for p in paths if not p.name.startswith(".") and
                (p.is_dir() or (p.suffix.lower() == ".json" and
                               (not self.saved_only or p.name == "configuration.json")))]


class ConfigurationFilePicker(Screen):
    BINDINGS = [("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    ConfigurationFilePicker > Vertical { height: 100%; padding: 0 1; }
    ConfigurationFilePicker DirectoryTree { height: 1fr; }
    ConfigurationFilePicker .buttons { height: auto; }
    """

    def __init__(self, start, *, folders=False, saved_only=False):
        super().__init__()
        self.start, self.folders = Path(start), folders
        self.saved_only = saved_only

    def compose(self):
        with Vertical():
            yield Label("Choose export folder" if self.folders else "Choose configuration JSON")
            yield Input(str(self.start), id="configuration-picker-location")
            with Horizontal(classes="buttons"):
                yield Button("Open folder", id="configuration-picker-open")
                yield Button("Use folder", id="configuration-picker-use", disabled=not self.folders)
                yield Button("Cancel", id="configuration-picker-cancel")
            yield JSONTree(self.start, saved_only=self.saved_only, id="configuration-picker-tree")
            yield Static("", id="configuration-picker-status", markup=False)
            yield Footer()

    def on_directory_tree_file_selected(self, event):
        event.stop()
        if not self.folders:
            self.dismiss(event.path)

    def on_directory_tree_directory_selected(self, event):
        event.stop()
        self.query_one("#configuration-picker-location", Input).value = str(event.path)

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == "configuration-picker-cancel":
            self.action_cancel()
            return
        path = Path(self.query_one("#configuration-picker-location", Input).value).expanduser()
        if not path.is_absolute() or not path.is_dir():
            self.query_one("#configuration-picker-status", Static).update("Choose an existing absolute folder path.")
            return
        if event.button.id == "configuration-picker-use":
            self.dismiss(path)
        else:
            self.query_one(JSONTree).path = path

    def action_cancel(self):
        self.dismiss(None)


class ConfigurationSharingScreen(Screen):
    BINDINGS = [("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    ConfigurationSharingScreen { layout: vertical; }
    ConfigurationSharingScreen > VerticalScroll { height: 1fr; padding: 0 1; }
    ConfigurationSharingScreen .buttons { height: auto; }
    #configuration-differences { height: 16; min-height: 8; }
    #configuration-feedback { height: auto; }
    """

    def __init__(self, review, *, importing):
        super().__init__()
        self.review, self.importing = review, importing
        self.preview = None
        self.original = review.request

    def compose(self):
        home = Path.home()/"Downloads"
        if not home.is_dir():
            home = Path.home()
        with VerticalScroll():
            yield Static("IMPORT EXPERIMENT CONFIGURATION" if self.importing else "EXPORT EXPERIMENT CONFIGURATION", classes="section-title")
            yield Static(CALIBRATION_NOTICE, markup=False)
            yield Label("Configuration JSON file")
            yield Input("" if self.importing else str(home/(self.original.experiment_id + "_configuration.json")),
                        placeholder="Select or paste a JSON file path", id="configuration-path")
            with Horizontal(classes="buttons"):
                yield Button("Browse files…" if self.importing else "Choose folder…", id="configuration-browse")
                if self.importing:
                    yield Button("Saved configurations…", id="configuration-saved")
                    yield Button("Preview import", id="configuration-preview", variant="primary")
                else:
                    yield Button("Export JSON", id="configuration-export", variant="primary")
            yield Static("Preview the complete scientific settings and differences before approving. Nothing is applied during preview."
                         if self.importing else "Exports all selected experiment values and complete stimulus documents. Existing files are never overwritten.",
                         id="configuration-feedback", markup=False)
            if self.importing:
                yield DataTable(id="configuration-differences", cursor_type="row", zebra_stripes=True)
                yield Button("Approve import", id="configuration-approve", disabled=True, variant="success")
            yield Button("Cancel", id="configuration-cancel")
        yield Footer()

    def on_input_changed(self, event):
        if event.input.id == "configuration-path" and self.importing:
            self.preview = None
            self.query_one("#configuration-approve", Button).disabled = True

    def _chosen(self, path):
        if path is not None:
            if not self.importing:
                path = Path(path)/(self.original.experiment_id + "_configuration.json")
            self.query_one("#configuration-path", Input).value = str(path)

    def _preview(self, document, profile):
        candidate, warnings = validate_portable(document, self.app.repo_root, self.original, profile)
        from ..experiments._internal.registry import get_experiment
        from ..stimuli.registry import get_stimulus
        spec = get_experiment(candidate.experiment_id)
        self.app.verify_loaded_sources(spec, candidate.stimulus_snapshots)
        rows = [("Experiment", self.original.experiment_id, candidate.experiment_id)]
        for field in spec.fields:
            rows.append((field.display_label, self.original.experiment_values.get(field.key, "—"), candidate.experiment_values[field.key]))
        for slot, selected in candidate.stimulus_snapshots.items():
            old = self.original.stimulus_snapshots.get(slot, {}).get("document", {})
            data = selected["document"]
            rows.append((slot + " stimulus", old.get("stimulus_id", "—"), data["stimulus_id"]))
            for field in get_stimulus(data["stimulus_id"]).parameters:
                rows.append((slot + ": " + field.display_label, old.get("parameters", {}).get(field.key, "—"), data["parameters"][field.key]))
        rows.append(("Show response-key guidance", self.original.show_response_instructions, candidate.show_response_instructions))
        table = self.query_one("#configuration-differences", DataTable)
        table.clear(columns=True)
        for label, width in (("Setting", 26), ("Current", 16), ("Imported", 16), ("Difference", 10)):
            table.add_column(label, width=width)
        for label, old, new in rows:
            table.add_row(Text(str(label)), Text(str(old)), Text(str(new)), "Changed" if old != new else "Same", height=None)
        changed = sum(old != new for _, old, new in rows)
        self.query_one("#configuration-feedback", Static).update(
            f"{spec.display_name} [{spec.id}]: {len(rows)} settings; {changed} differences. "
            "Approve saves a new local copy and opens Review. Cancel keeps your current configuration.\n"
            + "\n".join(warnings) + "\n" + CALIBRATION_NOTICE)
        self.preview = (document, digest(document))
        self.query_one("#configuration-approve", Button).disabled = False

    def on_button_pressed(self, event):
        event.stop()
        name = event.button.id
        if name == "configuration-cancel":
            self.action_cancel()
            return
        if name in {"configuration-browse", "configuration-saved"}:
            start = self.app.local_config_root/"parameter_files" if name == "configuration-saved" else Path.home()/"Downloads"
            if not start.is_dir():
                start = Path.home()
            self.app.push_screen(ConfigurationFilePicker(start, folders=not self.importing,
                                                         saved_only=name == "configuration-saved"), self._chosen)
            return
        try:
            self.app.verify_settings_current(self.original)
            if self.review.request != self.original:
                raise ValueError("Current settings changed; cancel and preview again.")
            profile = self.app.monitor_profiles[self.original.monitor_profile_id]
            path = Path(self.query_one("#configuration-path", Input).value).expanduser()
            if name == "configuration-export":
                document = make_document(self.app.repo_root, self.original, profile)
                write_export(path, document)
                self.query_one("#configuration-feedback", Static).update(f"Exported {path}. Share this JSON file; local calibration is not included.")
            elif name == "configuration-preview":
                self.preview = None
                self.query_one("#configuration-approve", Button).disabled = True
                self._preview(read_document(path), profile)
            elif name == "configuration-approve":
                if self.preview is None or digest(read_document(path)) != self.preview[1]:
                    raise ValueError("Import file changed or no preview is available. Preview it again; nothing was applied.")
                candidate, _ = validate_portable(self.preview[0], self.app.repo_root, self.original, profile)
                from ..experiments._internal.registry import get_experiment
                self.app.verify_loaded_sources(get_experiment(candidate.experiment_id), candidate.stimulus_snapshots)
                saved = save_local(self.app.local_config_root, self.app.repo_root, self.preview[0], self.original, profile)
                self.app.pop_screen()
                self.review.apply_shared_configuration(saved, imported=True)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            if self.importing:
                self.preview = None
                self.query_one("#configuration-approve", Button).disabled = True
            self.query_one("#configuration-feedback", Static).update(str(exc) + " Previous configuration was not changed.")

    def action_cancel(self):
        self.app.pop_screen()
