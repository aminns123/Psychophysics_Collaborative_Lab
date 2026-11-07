"""Textual startup and status feedback use the existing screen and worker loop."""

import asyncio
from pathlib import Path
from threading import Event

import pytest
from textual.widgets import Button, Input, Static
from textual.worker import WorkerState

from psychophysics_lab.ui import configuration_sharing, startup
from psychophysics_lab.ui.setup import PsyCoLabSetupApp
from test_parameter_accessibility import enter_review, selected_values
from psychophysics_lab.experiments._internal.registry import get_experiment

ROOT = Path(__file__).resolve().parents[1]


async def wait_until(check, timeout=4):
    async def wait():
        while not check():
            await asyncio.sleep(0.02)
    await asyncio.wait_for(wait(), timeout)


@pytest.mark.parametrize("skip", [True, False])
def test_reveal_restores_normal_layout(tmp_path, monkeypatch, skip):
    elapsed = 0.0
    monkeypatch.setattr(startup, "monotonic", lambda: elapsed)

    async def scenario():
        nonlocal elapsed
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path, reveal_startup=True)
        async with app.run_test(size=(96, 28)) as pilot:
            reveal = app._startup_reveal
            await wait_until(lambda: reveal.timer is not None and reveal.brand.region.width > 0)
            assert reveal.brand.region.x == 1 and reveal.brand.region.y == 0
            heading = app.screen.query_one("#console-heading", Static)
            original_region = heading.region
            if skip:
                await pilot.press("space")
                assert not reveal.active
            else:
                elapsed = reveal.DURATION / 2
                await wait_until(lambda: 0.05 < heading.styles.opacity < 0.95)
                elapsed = reveal.DURATION
                await wait_until(lambda: not reveal.active)
            await pilot.pause()
            assert not app.query("#startup-brand")
            assert heading.styles.opacity == 1
            assert heading.region == original_region

    asyncio.run(scenario())


def test_loading_animates_during_json_io_and_clears_after_failure(tmp_path, monkeypatch):
    released = Event()

    def slow_invalid_json(path):
        assert released.wait(5)
        raise ValueError("Invalid JSON for this test")

    monkeypatch.setattr(configuration_sharing, "read_document", slow_invalid_json)

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path)
        async with app.run_test(size=(96, 28)) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            review.query_one("#review-import-configuration", Button).press()
            await pilot.pause()
            importer = app.screen
            importer.query_one("#configuration-path", Input).value = str(tmp_path / "invalid.json")
            importer.query_one("#configuration-preview", Button).press()
            loading = app.loading
            try:
                await wait_until(lambda: loading.status is not None and loading.status.region.width > 0)
                assert loading.status.region.right == 95
                assert loading.status.region.y == 0
                label = loading.status.renderable
                await wait_until(lambda: loading.status.renderable != label)
                assert loading.busy
            finally:
                released.set()
            await wait_until(lambda: loading.status is None and not loading.busy)
            assert "Invalid JSON" in str(importer.query_one("#configuration-feedback", Static).renderable)
            assert importer.preview is None

    asyncio.run(scenario())


@pytest.mark.parametrize("cancel", [False, True])
def test_loading_stays_hidden_for_fast_work_and_clears_after_slow_work(tmp_path, cancel):
    async def fast():
        return 1

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path)
        async with app.run_test(size=(96, 28)) as pilot:
            await pilot.pause()
            loading = app.loading
            assert await loading.run(app.screen, fast).wait() == 1
            assert not app.screen.query("#operation-loading")
            stopped = asyncio.Event()
            worker = loading.run(app.screen, stopped.wait)
            await wait_until(lambda: loading.status is not None and loading.status.region.width > 0)
            assert loading.status.region.right == 95
            if cancel:
                worker.cancel()
            else:
                stopped.set()
            await wait_until(lambda: not loading.busy and loading.status is None)
            assert worker.state is (WorkerState.CANCELLED if cancel else WorkerState.SUCCESS)
            assert not app.screen.query("#operation-loading")

    asyncio.run(scenario())
