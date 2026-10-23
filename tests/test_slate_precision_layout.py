"""Slate Precision presentation regressions; scientific execution is unchanged."""

import asyncio
from pathlib import Path

import pytest
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.ui.setup import PsyCoLabSetupApp

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("size", [(60, 24), (80, 24), (120, 40), (160, 55)])
def test_setup_context_adapts_without_losing_editable_controls(tmp_path, monkeypatch, size):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            group = app.query_one("#setup-columns", Horizontal)
            editor = group.query_one("#setup-body", VerticalScroll)
            context = group.query_one("#setup-side", VerticalScroll)
            assert group.region.width > 0 and group.region.height > 0
            assert editor.region.width > 0 and editor.region.height > 0
            assert context.region.width > 0 and context.region.height > 0

            # Preserve the original form widget IDs, visibility, and read-only summary.
            participant = editor.query_one("#participant", Input)
            assert editor.query_one("#experiment", Select)
            assert editor.query_one("#monitor-profile", Select)
            assert context.query_one("#last-run-summary", Static)
            assert context.query_one("#experiment-summary", Static)
            assert context.query_one("#monitor-summary", Static)
            assert app.screen.query_one("#configure", Button)

            if size[0] >= 100:
                assert editor.region.y == context.region.y
                assert editor.region.right <= context.region.x
            else:
                assert context.region.y >= editor.region.bottom

            participant.value = "LOCAL_DRAFT"
            await pilot.click(app.screen.query_one("#nav-data", Button))
            await pilot.pause()
            assert app.screen.query_one("#data-run", Select)
            await pilot.click(app.screen.query_one("#nav-setup", Button))
            await pilot.pause()
            assert app.query_one("#participant", Input).value == "LOCAL_DRAFT"

    asyncio.run(scenario())


def test_slate_sections_keep_review_guidance_and_calibration_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(120, 40)) as pilot:
            app.query_one("#participant", Input).value = "S001"
            app.screen.query_one("#configure", Button).press()
            await pilot.pause()
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            # The checkbox from PR 76 must stay present and researcher-controlled.
            assert app.screen.query_one("#review-show-response-instructions")
            assert app.screen.query_one("#run-presentation-test", Button)
            assert app.screen.query_one("#run", Button)
            assert app.screen.query_one("#run-researcher-override", Button)
            await pilot.click(app.screen.query_one("#nav-display", Button))
            await pilot.pause()
            assert app.screen.query_one("#calibration-stage-nav")
            assert app.screen.query_one("#calibration-finish", Button)
            assert app.screen.query_one("#hub-nav")

    asyncio.run(scenario())
