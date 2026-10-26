"""Text states follow real keyboard/pointer input; checking is not saving."""
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Button, Static
from psychophysics_lab.ui.checkbox import ExplicitCheckbox


def test_checkbox_keyboard_mouse_saved_and_cancel_states():
    class Demo(App):
        def compose(self) -> ComposeResult:
            yield ExplicitCheckbox("Reviewed evidence", id="ack")
            yield Button("Save", id="save")
            yield Static("Not saved", id="status")
        def on_button_pressed(self, event):
            self.query_one("#status", Static).update(
                "Saved / verified: synthetic profile evidence" if self.query_one("#ack", ExplicitCheckbox).value
                else "Not saved: acknowledgement required")
    async def scenario():
        app = Demo()
        async with app.run_test() as pilot:
            checkbox = app.query_one("#ack", ExplicitCheckbox)
            assert "[ ] Not selected" in checkbox.label.plain
            checkbox.focus()
            await pilot.press("space")
            assert checkbox.value and "[X] Selected — not yet saved" in checkbox.label.plain
            assert "Not saved" in str(app.query_one("#status", Static).render())
            await pilot.click("#ack")
            assert not checkbox.value and "[ ] Not selected" in checkbox.label.plain
            checkbox.focus()
            await pilot.press("enter")
            assert checkbox.value
            await pilot.click("#save")
            assert "Saved / verified" in str(app.query_one("#status", Static).render())
            checkbox.value = False  # same reset used after actual verification save
            await pilot.pause()
            assert "[ ] Not selected" in checkbox.label.plain
            assert "Saved / verified" in str(app.query_one("#status", Static).render())
    asyncio.run(scenario())


def test_run_guidance_is_explicitly_current_run_selection():
    checkbox = ExplicitCheckbox("Guidance", value=True,
                                selected_status="Selected — applies to this run")
    assert "applies to this run" in checkbox.label.plain
    assert "saved" not in checkbox.label.plain
