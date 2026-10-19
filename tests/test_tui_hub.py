import asyncio
from pathlib import Path

from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.ui.setup import (
    ExperimentConfigScreen,
    ExperimentsScreen,
    PsyCoLabSetupApp,
    ReviewScreen,
)


ROOT = Path(__file__).resolve().parents[1]


def _plain(static: Static) -> str:
    rendered = static.render()
    return getattr(getattr(rendered, "_renderable", rendered), "plain", str(rendered))


def test_hub_navigation_and_reactive_experiment_summary(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "external_data")
        async with app.run_test(size=(140, 48)) as pilot:
            summary = app.query_one("#experiment-summary", Static)
            assert "historical csf" in _plain(summary).lower()

            await pilot.click(app.screen.query_one("#nav-experiments", Button))
            await pilot.pause()
            assert isinstance(app.screen, ExperimentsScreen)

            await pilot.click(app.screen.query_one("#nav-setup", Button))
            await pilot.pause()
            assert not isinstance(app.screen, ExperimentsScreen)

    asyncio.run(scenario())


def test_monitor_selector_contains_only_experiment_compatible_profiles(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "external_data")
        async with app.run_test(size=(140, 48)):
            experiment = app.query_one("#experiment", Select).value
            assert experiment == "legacy_contrast_sensitivity"
            assert app.query_one("#monitor-profile", Select).value == "legacy_reference_display"

    asyncio.run(scenario())


def test_setup_configuration_reaches_review_with_external_path(tmp_path):
    async def scenario():
        data_root = tmp_path / "external_data"
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=data_root)
        async with app.run_test(size=(150, 55)) as pilot:
            app.query_one("#participant", Input).value = "S001"
            app.query_one("#configure", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ExperimentConfigScreen)

            screen = app.screen
            screen.query_one("#field-Max-monitor-Luminance", Input).value = "500.0"
            screen.query_one("#field-Background-Luminance", Input).value = "49.0"
            screen.query_one("#field-Background-Screen-intensity", Input).value = "0.374"
            screen.query_one("#review", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            text = _plain(app.screen.query_one("#review-text", Static))
            assert "S001/contrast_sensitivity/legacy_reference_display" in text
            assert str(data_root) in text

    asyncio.run(scenario())
