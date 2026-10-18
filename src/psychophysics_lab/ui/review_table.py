"""File navigation on deliberate cell activation; normal clicks highlight."""
from textual.widgets import DataTable


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
