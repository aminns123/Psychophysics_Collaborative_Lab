"""File navigation on deliberate cell activation; normal clicks highlight."""
from textual.widgets import DataTable


REVIEW_TABLE_COLUMNS = (
    ("Group", 8),
    ("Parameter / units", 28),
    ("Effective value", 16),
    ("Status / authority", 24),
    ("Advanced source", 28),
)


def copy_review_table(source, destination):
    """Mirror the current Review rows into a wider, temporary table view.

    Values and source targets remain owned by ReviewScreen. A temporary view
    never computes or edits a second scientific configuration.
    """
    coordinate = source.cursor_coordinate
    destination.clear(columns=True)
    for label, width in REVIEW_TABLE_COLUMNS:
        destination.add_column(label, width=width)
    for index in range(source.row_count):
        destination.add_row(*source.get_row_at(index))
    if source.row_count:
        destination.move_cursor(row=min(coordinate.row, source.row_count - 1),
                                column=min(coordinate.column, len(REVIEW_TABLE_COLUMNS) - 1))


class ReviewSettingsTable(DataTable):
    async def _on_click(self, event):
        meta=event.style.meta
        row,column=meta.get("row",-1),meta.get("column",-1)
        if row>=0 and column>=0:
            event.prevent_default()
            event.stop()
            self.focus()
            self.move_cursor(row=row,column=column)
            # File addresses behave as links; values require a double click.
            # Enter continues to use DataTable's normal selection message.
            if column==4 or event.chain==2:
                self.action_select_cursor()
            return
        event.prevent_default()
        await super()._on_click(event)
