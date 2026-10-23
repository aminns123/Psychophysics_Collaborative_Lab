"""Researcher-only coffee / forest layout checks; no renderer is opened."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Select

from psychophysics_lab.ui.setup import PsyCoLabSetupApp

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("size", [(60, 24), (80, 24), (120, 40), (160, 55)])
def test_visual_control_widths_and_page_navigation(tmp_path, monkeypatch, size):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            # The edit controls remain present but no longer span huge terminals.
            controls = app.query_one("#setup-body")
            for identity in ("run-intent", "experiment", "monitor-profile"):
                select = controls.query_one("#" + identity, Select)
                assert 0 < select.region.width <= 76
            assert controls.query_one("#data-root", Input)
            assert app.screen.query_one("#hub-nav")
            await pilot.click(app.screen.query_one("#nav-stimuli", Button))
            await pilot.pause()
            preview = app.screen.query_one("#library-preview-stimulus", Select)
            open_library = app.screen.query_one("#view-shared-stimulus-library", Button)
            assert 0 < preview.region.width <= 76
            assert 0 < open_library.region.width <= 38
            assert app.screen.query_one("#library-show-preview", Button)
            await pilot.click(app.screen.query_one("#nav-experiments", Button))
            await pilot.pause()
            first = app.screen.query_one("#view-exp-definition", Button)
            second = app.screen.query_one("#view-exp-runtime", Button)
            assert first.region.width <= 38
            assert second.region.width <= 38
            assert second.region.y >= first.region.bottom
            await pilot.click(app.screen.query_one("#nav-data", Button))
            await pilot.pause()
            assert app.screen.query_one("#data-run", Select)
            assert app.screen.query_one("#inspect-manifest", Button)
            assert app.screen.query_one("#inspect-trials", Button)
            await pilot.click(app.screen.query_one("#nav-help", Button))
            await pilot.pause()
            assert app.screen.query_one("#learn-guide", Button)

    asyncio.run(scenario())


def test_review_parameter_table_and_response_guidance_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(120, 40)) as pilot:
            app.query_one("#participant", Input).value = "S001"
            app.screen.query_one("#configure", Button).press()
            await pilot.pause()
            # The currently-hidden legacy condition group is not a reason to
            # discard its scientific inputs or source-controlled values.
            from textual.widgets import Collapsible
            hidden = [group for group in app.screen.query(Collapsible)
                      if group.title == "Stimulus conditions"]
            assert all(not group.display for group in hidden)
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            assert app.screen.query_one("#resolved-settings-table")
            assert app.screen.query_one("#review-show-response-instructions")
            assert app.screen.query_one("#run-presentation-test", Button)
            assert app.screen.query_one("#run", Button)
            assert app.screen.query_one("#run-researcher-override", Button)

    asyncio.run(scenario())
