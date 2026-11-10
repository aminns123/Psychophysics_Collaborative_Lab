"""A recovery-only Review table with no Test, Run or Export actions."""

import asyncio
import json

from rich.text import Text
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Checkbox, DataTable, Footer, Select, Static, TextArea

from .full_text import FullTextScreen, field_description
from .parameter_editor import parameter_value_widget
from .review_table import ReviewSettingsTable


def show_value(value, limit=120):
    if value is None:
        return "—"
    encoded = json.dumps(value, ensure_ascii=True)
    return encoded if len(encoded) <= limit else encoded[:limit - 1] + "…"


class RecoveryValueEditor(ModalScreen):
    BINDINGS = [("escape", "close", "Back")]
    DEFAULT_CSS = """
    RecoveryValueEditor { align: center middle; }
    RecoveryValueEditor > VerticalScroll { width: 92%; height: 90%; padding: 1 2; background: $surface; border: solid $primary; }
    RecoveryValueEditor .actions { height: auto; }
    RecoveryValueEditor Static { height: auto; }
    """

    def __init__(self, row):
        super().__init__()
        self.row = row

    def compose(self):
        row = self.row
        with VerticalScroll():
            yield Static(field_description(row.field), markup=False)
            yield Static(f"\n{row.status}. {row.explanation}\nHistorical: "
                         + "\n".join(f"{show_value(path, 160)} = {show_value(value, 240)}"
                                     for path, value in row.historical.items())
                         + f"\nSuggested: {show_value(row.suggestion, 240)}"
                         + f" · Declared default: {show_value(row.default, 240)}", markup=False)
            yield parameter_value_widget(row.field, row.value, widget_id="recovery-value", allow_blank=True)
            with Horizontal(classes="actions"):
                yield Button("Accept suggestion", id="recovery-accept", disabled=row.suggestion is None)
                yield Button("Use declared default", id="recovery-default", disabled=row.default is None)
            with Horizontal(classes="actions"):
                yield Button("Replace", id="recovery-replace", disabled=not row.field.editable)
                yield Button("Reject value", id="recovery-reject")
                yield Button("Back", id="recovery-editor-back")
            yield Static("", id="recovery-editor-error", markup=False)

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == "recovery-editor-back":
            self.action_close()
            return
        action = event.button.id.removeprefix("recovery-")
        try:
            value = self.query_one("#recovery-value").value
            self.row.decide(action, None if value is Select.BLANK else value)
        except (ValueError, TypeError, OverflowError) as exc:
            self.query_one("#recovery-editor-error", Static).update(str(exc))
            return
        self.dismiss(True)

    def action_close(self):
        self.dismiss(False)


class ConfirmHistoricalValues(FullTextScreen):
    def compose(self):
        with Vertical():
            yield Static(self.title_text, id="full-text-title", markup=False)
            yield TextArea(self.content_text, read_only=True, id="full-text-content")
            yield Button("Accept all listed values I have checked", id="recovery-confirm-checked")
            yield Button("Back / Esc", id="full-text-back")
            yield Footer()

    def on_button_pressed(self, event):
        event.stop()
        self.dismiss(event.button.id == "recovery-confirm-checked")

    def action_close(self):
        self.dismiss(False)


class ConfigurationRecoveryScreen(Screen):
    BINDINGS = [("escape", "cancel", "Cancel draft")]
    DEFAULT_CSS = """
    ConfigurationRecoveryScreen > Vertical { height: 1fr; padding: 0 1; }
    ConfigurationRecoveryScreen .actions { height: auto; }
    ConfigurationRecoveryScreen ReviewSettingsTable { height: 1fr; min-height: 4; }
    #recovery-status { height: auto; max-height: 4; overflow-y: auto; }
    #recovery-message { height: auto; }
    #recovery-reviewed { height: auto; }
    """

    def __init__(self, importer, draft):
        super().__init__()
        self.importer = importer
        self.draft = draft
        self.saving = False

    def compose(self):
        with Vertical():
            yield Static(f"RECOVERY DRAFT · {self.draft.spec.display_name}", classes="section-title", markup=False)
            yield Static("Select a row and press Enter to review the meaning, accept a value or enter a replacement.",
                         id="recovery-message", markup=False)
            if self.draft.scope_note:
                yield Static(self.draft.scope_note, markup=False)
            yield ReviewSettingsTable(id="recovery-settings", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="actions"):
                yield Button("Accept compatible", id="recovery-accept-compatible")
                yield Button("Unmapped & source", id="recovery-details")
                yield Button("Cancel draft", id="recovery-cancel")
            yield Checkbox("I reviewed the original meanings and the installed scientific protocol.", id="recovery-reviewed")
            yield Button("Validate and save new configuration", id="recovery-save", variant="primary", disabled=True)
            yield Static("", id="recovery-status", markup=False)
        yield Footer()

    def on_mount(self):
        table = self.query_one("#recovery-settings", ReviewSettingsTable)
        for label, width in (("Setting", 30), ("Historical / suggested", 20), ("Status", 17), ("Draft value", 16)):
            table.add_column(label, width=width)
        self.refresh_rows()
        table.focus()

    def refresh_rows(self, *_):
        table = self.query_one("#recovery-settings", ReviewSettingsTable)
        index = table.cursor_row
        table.clear()
        details = []
        for row in self.draft.review_rows:
            historical = show_value(next(iter(row.historical.values()), None))
            suggested = show_value(row.suggestion)
            table.add_row(Text(row.label), Text(historical if historical == suggested else f"{historical} → {suggested}"),
                          "Resolved" if row.resolved and not row.locked else
                          "Rejected" if not row.resolved and row.decisions else row.status,
                          Text(show_value(row.value)), height=None)
            details.append(row.explanation)
        table.row_details = details
        if table.row_count:
            table.move_cursor(row=min(index, table.row_count - 1))
        self.query_one("#recovery-status", Static).update(
            f"{self.draft.unresolved} incomplete settings · {len(self.draft.unmapped)} unmapped historical entries. "
            "Cancel discards this draft.")
        batch = self.query_one("#recovery-accept-compatible", Button)
        compatible = any(row.status == "Compatible" and not row.decisions for row in self.draft.rows)
        same_key = self.historical_suggestions()
        batch.label = "Accept compatible" if compatible else "Review same-key values"
        batch.disabled = not compatible and not same_key
        self.query_one("#recovery-reviewed", Checkbox).value = False
        self.update_save()

    def historical_suggestions(self):
        return [row for row in self.draft.rows if row.status == "Check meaning" and not row.decisions]

    def review_historical_suggestions(self, rows):
        details = "\n\n".join(f"{row.label} = {show_value(row.suggestion, 240)}\n{field_description(row.field)}"
                              for row in rows)

        def decided(accepted):
            if accepted:
                for row in rows:
                    row.decide("accept")
                self.refresh_rows()

        self.app.push_screen(ConfirmHistoricalValues(
            "Confirm historical settings against the original protocol",
            "These keys and values fit the installed declarations. The file does not verify matching scientific "
            "meaning. Compare each value and its original units, response mapping and method meaning before "
            "accepting. Return to the table to replace or reject individual values.\n\n" + details), decided)

    def update_save(self):
        self.query_one("#recovery-save", Button).disabled = (
            self.saving or bool(self.draft.unresolved) or not self.query_one("#recovery-reviewed", Checkbox).value)

    def on_checkbox_changed(self, event):
        self.update_save()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if not self.saving:
            row = self.draft.review_rows[event.cursor_row]
            if row.locked:
                self.app.push_screen(FullTextScreen(row.label, row.explanation))
            else:
                self.app.push_screen(RecoveryValueEditor(row), lambda changed: self.refresh_rows() if changed else None)

    def on_button_pressed(self, event):
        event.stop()
        if self.saving:
            return
        button = event.button.id
        if button == "recovery-cancel":
            self.action_cancel()
        elif button == "recovery-accept-compatible":
            if any(row.status == "Compatible" and not row.decisions for row in self.draft.rows):
                self.draft.accept_compatible()
                self.refresh_rows()
            else:
                self.review_historical_suggestions(self.historical_suggestions())
        elif button == "recovery-details":
            data = {"original_kind": self.draft.source_kind,
                    "original_schema": self.draft.schema, "original_software": self.draft.software,
                    "installed_software": self.draft.local_software,
                    "unmapped": self.draft.unmapped_entries()}
            self.app.push_screen(FullTextScreen("Source identities and unmapped historical values",
                                                json.dumps(data, indent=2, ensure_ascii=True)))
        elif button == "recovery-save":
            self.app.loading.run(self, self.save, label="Validating recovery")

    async def save(self):
        reviewed = self.query_one("#recovery-reviewed", Checkbox)
        approved = reviewed.value
        reviewed.disabled = True
        self.saving = True
        self.update_save()
        self.query_one("#recovery-status", Static).update("Validating and saving a new local configuration…")
        try:
            app = self.app
            importer = self.importer
            if importer.review.request != importer.original:
                raise ValueError("Current Review changed. Cancel and preview the original file again.")
            profile = app.monitor_profiles[importer.original.monitor_profile_id]

            def publish():
                app.verify_settings_current(importer.original)
                return self.draft.save(app.local_config_root, app.repo_root, importer.original, profile,
                                       reviewed=approved, verify_sources=app.verify_loaded_sources)

            result = await asyncio.to_thread(publish)
        except (ValueError, OSError, KeyError, TypeError, OverflowError, RecursionError) as exc:
            self.query_one("#recovery-status", Static).update(str(exc) + " Current configuration was not changed.")
            return
        finally:
            self.saving = False
            reviewed.disabled = False
            self.update_save()
        app.pop_screen()
        app.pop_screen()
        importer.review.apply_shared_configuration(result, imported=True)

    def action_cancel(self):
        if not self.saving:
            self.app.pop_screen()
