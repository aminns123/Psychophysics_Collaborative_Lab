"""Fullscreen view of the existing Review table, not a second settings editor."""
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from .review_table import ReviewSettingsTable, copy_review_table


class ReviewTableFullscreen(Screen):
    """One focused, navigable table using the parent Review's existing targets.

    The parent Review owns the effective configuration, source-file mappings,
    validated reload and launch state; this screen only mirrors its rows.
    """

    BINDINGS = [("escape", "close_table", "Back to Review")]
    DEFAULT_CSS = """
    ReviewTableFullscreen {
        background: #080808;
        color: #eeeeee;
        layout: vertical;
    }
    #expanded-review-toolbar {
        layout: horizontal;
        height: 3;
        width: 100%;
        padding: 0 1;
        background: #111111;
    }
    #expanded-review-toolbar Button {
        width: auto;
        min-width: 15;
        max-width: 32;
        height: 3;
        margin-right: 2;
        background: #111111;
        color: #eeeeee;
        border: solid #555555;
    }
    #expanded-review-toolbar Button:focus,
    #expanded-review-toolbar Button:hover {
        background: #dddddd;
        color: #080808;
    }
    #expanded-review-note {
        width: 100%;
        height: 2;
        padding: 0 1;
        color: #cccccc;
    }
    #expanded-settings-table {
        width: 100%;
        height: 1fr;
        min-height: 3;
        scrollbar-size: 1 1;
        background: #080808;
        color: #eeeeee;
    }
    #expanded-review-location {
        width: 100%;
        height: 2;
        padding: 0 1;
        background: #111111;
        color: #eeeeee;
    }
    ReviewTableFullscreen Footer {
        height: 1;
        background: #181818;
        color: #eeeeee;
    }
    """

    def __init__(self, review):
        super().__init__()
        self.review = review

    def compose(self):
        with Vertical():
            with Horizontal(id="expanded-review-toolbar"):
                yield Button("Back to Review", id="expanded-review-back")
                yield Button("Open selected file", id="expanded-review-open")
                yield Button("Reload saved files", id="expanded-review-reload")
            yield Static(
                "Expanded Review table  ·  Select a row; Enter or double-click opens its source.  Esc returns.",
                id="expanded-review-note", markup=False,
            )
            yield ReviewSettingsTable(id="expanded-settings-table", cursor_type="cell")
            yield Static("", id="expanded-review-location", markup=False)
            yield Footer()

    def on_mount(self):
        self.refresh_table()
        self.query_one("#expanded-settings-table", ReviewSettingsTable).focus()

    def refresh_table(self):
        source = self.review.query_one("#resolved-settings-table", ReviewSettingsTable)
        destination = self.query_one("#expanded-settings-table", ReviewSettingsTable)
        previous = destination.cursor_coordinate
        copy_review_table(source, destination)
        if destination.row_count:
            destination.move_cursor(row=min(previous.row, destination.row_count - 1),
                                    column=min(previous.column, 4))
            self._show_location(destination.cursor_row)

    def _show_location(self, row):
        if not 0 <= row < len(getattr(self.review, "_file_targets", ())):
            return
        target = self.review._file_targets[row]
        path = target.get("path")
        self.query_one("#expanded-review-location", Static).update(
            f"{path or 'Unsaved values'} : {target.get('line', 1)}  ·  {target.get('note', '')}"
        )

    def on_data_table_cell_highlighted(self, event):
        if event.data_table.id == "expanded-settings-table":
            self._show_location(event.coordinate.row)

    def on_data_table_cell_selected(self, event):
        if event.data_table.id == "expanded-settings-table":
            event.stop()
            self._open(event.coordinate.row)

    def _open(self, row=None):
        table = self.query_one("#expanded-settings-table", ReviewSettingsTable)
        row = table.cursor_row if row is None else row
        if not 0 <= row < table.row_count:
            return
        self.review._open_review_file(row)
        # Opening a previously unsaved parameter exports an ordinary JSON,
        # changing the file link on the Review screen. Mirror that exact row.
        selected = table.cursor_coordinate
        self.refresh_table()
        table.move_cursor(row=min(selected.row, table.row_count - 1),
                          column=min(selected.column, 4))
        self._show_location(table.cursor_row)

    def on_button_pressed(self, event):
        identity = event.button.id
        if identity == "expanded-review-back":
            event.stop()
            self.action_close_table()
        elif identity == "expanded-review-open":
            event.stop()
            self._open()
        elif identity == "expanded-review-reload":
            event.stop()
            try:
                self.review._reload_review_files()
                self.refresh_table()
                self._show_location(self.query_one("#expanded-settings-table", ReviewSettingsTable).cursor_row)
            except (ValueError, OSError, TypeError, KeyError) as exc:
                self.query_one("#expanded-review-location", Static).update(str(exc))

    def action_close_table(self):
        table = self.query_one("#expanded-settings-table", ReviewSettingsTable)
        original = self.review.query_one("#resolved-settings-table", ReviewSettingsTable)
        if original.row_count:
            original.move_cursor(row=min(table.cursor_row, original.row_count - 1),
                                 column=min(table.cursor_column, 4))
        self.app.pop_screen()
