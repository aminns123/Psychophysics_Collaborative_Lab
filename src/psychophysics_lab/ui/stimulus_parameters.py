"""Compact, independent JSON selection for each experiment stimulus slot."""
from pathlib import Path
import json
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static, TextArea, Collapsible
from ..stimuli.registry import list_stimuli, get_stimulus
from ..config.stimulus_parameters import load_parameters, save_parameter_preset, snapshot, document_for


class JsonPresetEditor(Screen):
    DEFAULT_CSS = "JsonPresetEditor TextArea { height: 1fr; } JsonPresetEditor Static { height: auto; }"
    def __init__(self, panel):
        super().__init__()
        self.panel = panel

    def compose(self):
        yield Label("Edit stimulus JSON — save as a new named preset; shared defaults are preserved")
        yield TextArea(json.dumps(self.panel.current()["document"], indent=2), id="stimulus-json-editor")
        yield Input(placeholder="New preset name", id="stimulus-preset-name")
        with Horizontal(classes="buttons"):
            yield Button("Cancel", id="json-cancel")
            yield Button("Validate and save new preset", id="json-save", variant="primary")
        yield Static("", id="json-feedback", markup=False)

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == "json-cancel":
            self.app.pop_screen()
        elif event.button.id == "json-save":
            try:
                document = json.loads(self.query_one("#stimulus-json-editor", TextArea).text)
                path = save_parameter_preset(self.app.local_config_root,
                    self.query_one("#stimulus-preset-name", Input).value, self.panel.stimulus, document)
                self.panel.load(path)
                self.panel.refresh_presets()
                self.app.pop_screen()
            except (ValueError, OSError, TypeError) as exc:
                self.query_one("#json-feedback", Static).update(str(exc))


class StimulusParametersPanel(Vertical):
    def __init__(self, configuration, slot):
        super().__init__(id="stimulus-slot-" + slot)
        self.configuration, self.slot = configuration, slot
        self.stimulus = get_stimulus(configuration.experiment.stimulus_defaults[slot])
        self.loaded = None
        self.path = None
        self.error = None

    def compose(self):
        compatible = [item for item in list_stimuli() if item.family == self.configuration.experiment.stimulus_slots[self.slot]]
        yield Label(f"Stimulus slot: {self.slot}")
        yield Select([(item.display_name, item.id) for item in compatible], value=self.stimulus.id,
                     allow_blank=False, id="stimulus-select-" + self.slot)
        yield Select([], id="stimulus-preset-" + self.slot, prompt="Choose default or named preset")
        with Horizontal(classes="buttons"):
            yield Button("Edit in TUI", id="stimulus-values-" + self.slot)
            yield Button("Edit JSON in editor", id="stimulus-file-" + self.slot)
            yield Button("Reload saved JSON", id="stimulus-file-reload-" + self.slot)
            yield Button("Preview", id="stimulus-preview-" + self.slot)
        with Collapsible(title="Advanced presets / JSON", collapsed=True):
            yield Input(placeholder="Preset JSON path", id="stimulus-path-" + self.slot)
            yield Button("Edit JSON inside terminal (legacy)", id="stimulus-edit-" + self.slot)
            yield Button("Reload and validate", id="stimulus-reload-" + self.slot)
        yield Static("", id="stimulus-summary-" + self.slot, markup=False)

    def on_mount(self):
        self.cache_key = (*self.configuration.draft_key, self.slot)
        cached = self.app.stimulus_drafts.get(self.cache_key)
        if cached is None and self.configuration.review_return is not None:
            saved = self.configuration.review_return.request.stimulus_snapshots.get(self.slot)
            if saved:
                cached = (saved, None)
        if cached is not None:
            self.loaded, self.path = cached
            self.stimulus = get_stimulus(self.loaded['document']['stimulus_id'])
            with self.prevent(Select.Changed):
                self.query_one('#stimulus-select-' + self.slot, Select).value = self.stimulus.id
        self.refresh_presets()
        if cached is not None:
            if self.path:
                with self.prevent(Input.Changed):
                    self.query_one('#stimulus-path-' + self.slot, Input).value = str(self.path)
            self.refresh_summary()
        elif not self.configuration.experiment.stimulus_field_bindings.get(self.slot):
            self.load_default()
        else:
            self.refresh_summary()

    def refresh_presets(self):
        paths = [self.app.repo_root / self.stimulus.default_config] if self.stimulus.default_config else []
        paths += sorted((self.app.local_config_root / "stimulus_presets" / self.stimulus.id).glob("*.json"))
        selector = self.query_one("#stimulus-preset-" + self.slot, Select)
        with self.prevent(Select.Changed):
            options = [(p.name, str(p)) for p in paths]
            if not self.stimulus.default_config:
                options.insert(0, ("Stimulus class defaults", "library_defaults"))
            selector.set_options(options)
            selector.value = str(self.path) if self.path in paths else (
                "library_defaults" if self.loaded and self.loaded["file_identity"] == "library_defaults" else Select.BLANK)

    def current(self):
        if getattr(self, "external_json_pending", False):
            raise ValueError(f"{self.slot}: Reload saved JSON after editing, before Review.")
        if self.error:
            raise ValueError(self.error)
        if self.loaded is not None:
            if self.path:
                latest = load_parameters(self.path, self.stimulus)
                if latest["file_sha256"] != self.loaded["file_sha256"]:
                    raise ValueError(f"{self.slot}: JSON changed; choose Reload and validate.")
            return self.loaded
        fields = self.configuration.experiment.stimulus_field_bindings[self.slot]
        values = {}
        for parameter, key in fields.items():
            value = self.configuration.query_one("#field-" + key.replace("_", "-")).value
            field = next(item for item in self.stimulus.parameters if item.key == parameter)
            values[parameter] = field.coerce(value)
        return snapshot(document_for(self.stimulus, values), file_identity="experiment_values")

    def load_default(self):
        if self.stimulus.default_config:
            self.load(self.app.repo_root / self.stimulus.default_config)
            return
        self.loaded = snapshot(document_for(self.stimulus), file_identity="library_defaults")
        self.path, self.error = None, None
        self.app.stimulus_drafts[self.cache_key] = (self.loaded, None)
        with self.prevent(Input.Changed):
            self.query_one("#stimulus-path-" + self.slot, Input).value = ""
        self.refresh_summary()

    def load(self, path):
        try:
            self.loaded = load_parameters(path, self.stimulus)
            self.path, self.error = Path(path), None
            self.app.stimulus_drafts[self.cache_key] = (self.loaded, self.path)
            with self.prevent(Input.Changed):
                self.query_one("#stimulus-path-" + self.slot, Input).value = str(self.path)
            for key, field in self.configuration.experiment.stimulus_field_bindings.get(self.slot, {}).items():
                widget = self.configuration.query_one("#field-" + field.replace("_", "-"))
                value = self.loaded["document"]["parameters"][key]
                widget.value = value if isinstance(widget, Select) else str(value)
            self.refresh_summary()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.error = str(exc)
            self.query_one("#stimulus-summary-" + self.slot, Static).update("BLOCKED: " + self.error)

    def refresh_summary(self):
        try:
            current = self.current()
            units = {item.key: item.units for item in self.stimulus.parameters}
            values = current["document"]["parameters"]
            controlled = set()
            try:
                from .settings_review import parameter_sources
                description = self.configuration.describe_current_settings()
                values = description["stimuli"].get(self.slot, values)
                controlled = parameter_sources(description, self.slot)
            except (ValueError, KeyError, TypeError):
                pass  # Required experiment inputs may still be blank while editing.
            summary = "\n".join(f"{key}: {value} {units[key]}" +
                (" — set by experiment (sample)" if key in controlled else "") for key, value in values.items())
            self.query_one("#stimulus-summary-" + self.slot, Static).update(
                f"{self.stimulus.id} · {current['file_identity']}\n{summary}\nSnapshot: {current['resolved_sha256'][:12]}")
        except (ValueError, KeyError, TypeError) as exc:
            self.query_one("#stimulus-summary-" + self.slot, Static).update("BLOCKED: " + str(exc))

    def on_input_changed(self, event):
        if event.input.id == "stimulus-path-" + self.slot:
            event.stop()
            if self.is_mounted and event.value != str(self.path or ""):
                self.error = f"{self.slot}: choose Reload and validate for the selected JSON path."
                self.refresh_summary()

    def on_select_changed(self, event):
        event.stop()
        if not self.is_mounted or event.value is Select.BLANK:
            return
        if event.select.id == "stimulus-select-" + self.slot:
            if event.value == self.stimulus.id:
                return
            self.stimulus = get_stimulus(str(event.value))
            self.load_default()
            self.refresh_presets()
        elif event.select.id == "stimulus-preset-" + self.slot:
            if event.value == "library_defaults":
                self.load_default()
            else:
                self.load(Path(str(event.value)))

    def _external_json(self):
        from .parameter_files import working_path, ensure_json, parameter_info
        from .editor import open_parameter_file
        from ..config.local import preferences
        from .settings_review import parameter_sources
        try:
            description = self.configuration.describe_current_settings()
            controlled = parameter_sources(description, self.slot)
        except (ValueError, KeyError, TypeError):
            controlled = set()
        if getattr(self,"external_json_pending",False):
            open_parameter_file(self.app.repo_root,self.external_json_path,self.app.local_config_root,
                executable=preferences(self.app.local_config_root).get("editor_executable"))
            return
        document = dict(self.current()["document"])
        document["parameter_info"] = parameter_info(self.stimulus.parameters, controlled)
        path = self.path if self.path and self.path.resolve().is_relative_to(self.app.local_config_root.resolve()) else working_path(
            self.app.local_config_root, self.configuration.experiment.id, self.slot)
        ensure_json(path, document)
        self.external_json_path = path
        self.external_json_pending = True
        open_parameter_file(self.app.repo_root, path, self.app.local_config_root,
            executable=preferences(self.app.local_config_root).get("editor_executable"))
        self.query_one("#stimulus-summary-"+self.slot, Static).update(
            f"Editing {self.stimulus.id}: {path}\nSave in the editor, then Reload saved JSON. Experiment-controlled parameters are identified in parameter_info.")

    def on_button_pressed(self, event):
        event.stop()
        try:
            if event.button.id == "stimulus-file-" + self.slot:
                self._external_json()
            elif event.button.id == "stimulus-file-reload-" + self.slot:
                path = getattr(self, "external_json_path", None) or self.path
                if not path:
                    raise ValueError("Open a parameter JSON first.")
                self.load(path)
                if not self.error:
                    self.external_json_pending = False
                    self.refresh_summary()
            elif event.button.id == "stimulus-values-" + self.slot:
                from .stimulus_editor import StimulusValueEditor
                self.app.push_screen(StimulusValueEditor(self))
            elif event.button.id == "stimulus-reload-" + self.slot:
                self.load(Path(self.query_one("#stimulus-path-" + self.slot, Input).value))
            elif event.button.id == "stimulus-edit-" + self.slot:
                self.app.push_screen(JsonPresetEditor(self))
            elif event.button.id == "stimulus-preview-" + self.slot:
                from .preview import show_stimulus_preview
                values = self.current()["document"]["parameters"]
                message = "Preset appearance only; complete required experiment settings for a trial preview."
                try:
                    description = self.configuration.describe_current_settings()
                    values = description["stimuli"].get(self.slot, values)
                    message = "Representative experiment appearance. Random/adaptive values vary; physical size, contrast and timing are unverified."
                except (ValueError, KeyError, TypeError):
                    pass
                show_stimulus_preview(self.stimulus.id, values, self.app.local_config_root / "previews")
                self.app.notify(message, timeout=8)
        except (ValueError, OSError, KeyError) as exc:
            self.query_one("#stimulus-summary-" + self.slot, Static).update(str(exc))
