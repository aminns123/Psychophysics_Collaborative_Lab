"""Edit declared stimulus values; JSON remains an advanced preset format."""

from .console import ConsoleScreen as Screen
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.widgets import Label, Input, Select, Button, Static


class StimulusValueEditor(Screen):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.document = panel.current()["document"]
        from .settings_review import parameter_sources
        try:
            description = panel.configuration.describe_current_settings()
            self.controlled = parameter_sources(description, panel.slot)
            self.effective = description["stimuli"].get(panel.slot, {})
        except (ValueError, KeyError, TypeError):
            self.controlled, self.effective = set(), {}

    def compose_content(self):
        with Vertical(id="fixed-shell"):
            yield Label(self.panel.stimulus.display_name)
            with Horizontal(classes="buttons"):
                yield Button("Preview", id="stimulus-values-preview")
                yield Button(
                    "Save preset", id="stimulus-values-save", variant="primary"
                )
                yield Button("Back", id="stimulus-values-back")
            yield Static("", id="stimulus-values-status", markup=False)
        with VerticalScroll():
            yield Static(
                "Edit appearance here. The experiment may set position, strength or other values for each trial; use Try the experiment to see those changes."
            )
            for index, field in enumerate(self.panel.stimulus.parameters):
                yield Label(field.display_label)
                value = (self.effective.get(field.key, self.document["parameters"][field.key])
                         if field.key in self.controlled else self.document["parameters"][field.key])
                if field.key in self.controlled:
                    yield Static("Set by the experiment each trial. Change its settings or Python; this is a sample value.")
                if field.kind == "choice":
                    yield Select(
                        [(str(v), v) for v in field.choices],
                        value=value,
                        allow_blank=False,
                        id=f"stimulus-value-{index}",
                        disabled=not field.editable or field.key in self.controlled,
                    )
                else:
                    yield Input(
                        value=str(value),
                        id=f"stimulus-value-{index}",
                        disabled=not field.editable or field.key in self.controlled,
                    )
                if field.help_text:
                    yield Static(field.help_text)
            yield Label("Save as a new preset")
            yield Input(placeholder="Preset name", id="stimulus-value-name")

    def values(self):
        values = {}
        for index, field in enumerate(self.panel.stimulus.parameters):
            if field.key in self.controlled:
                values[field.key] = self.document["parameters"][field.key]
                continue
            widget = self.query_one(f"#stimulus-value-{index}")
            values[field.key] = field.coerce(widget.value)
        return self.panel.stimulus.validate_parameters(values)

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == "stimulus-values-back":
            self.app.pop_screen()
            return
        try:
            values = self.values()
            if event.button.id == "stimulus-values-preview":
                from .preview import show_stimulus_preview

                show_stimulus_preview(
                    self.panel.stimulus.id,
                    values,
                    self.app.local_config_root / "previews",
                )
                self.query_one("#stimulus-values-status", Static).update(
                    "Preview opened. Appearance only; physical contrast and timing are unverified."
                )
            elif event.button.id == "stimulus-values-save":
                from ..config.stimulus_parameters import save_parameter_preset

                name = self.query_one("#stimulus-value-name", Input).value.strip()
                if not name:
                    raise ValueError("Enter a preset name before saving.")
                path = save_parameter_preset(
                    self.app.local_config_root,
                    name,
                    self.panel.stimulus,
                    dict(self.document) | {"parameters": values},
                )
                self.panel.load(path)
                self.panel.refresh_presets()
                self.app.pop_screen()
        except (ValueError, OSError, TypeError) as exc:
            self.query_one("#stimulus-values-status", Static).update(str(exc))
