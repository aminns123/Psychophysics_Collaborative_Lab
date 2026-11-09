"""Exercise the shared researcher status and its presentation boundary."""

import asyncio
from pathlib import Path

import pytest
from textual.worker import WorkerCancelled, WorkerFailed

from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.presentation_testing import PresentationTestRequest
from psychophysics_lab.ui.setup import PsyCoLabSetupApp


ROOT = Path(__file__).resolve().parents[1]


async def wait_until(predicate):
    async def poll():
        while not predicate():
            await asyncio.sleep(.01)
    await asyncio.wait_for(poll(), timeout=3)


@pytest.mark.parametrize("outcome", ["success", "failure", "cancel"])
def test_feedback_waits_for_slow_work_and_clears_when_worker_ends(tmp_path, monkeypatch, outcome):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        loading = app.loading
        monkeypatch.setattr(loading, "DELAY", .12)
        monkeypatch.setattr(loading, "POLL_INTERVAL", .01)

        async def quick():
            assert loading.status is None

        release = asyncio.Event()

        async def slow():
            await release.wait()
            if outcome == "failure":
                raise ValueError("fixture could not finish")

        async with app.run_test(size=(80, 24)):
            assert loading.timer is None
            await loading.run(app.screen, quick, label="Quick check").wait()
            await wait_until(lambda: loading.timer is None)
            assert not app.query("#operation-loading")

            worker = app.screen.run_worker(slow, exit_on_error=False)
            loading.watch(worker, "Checking saved files")
            assert loading.status is None
            await wait_until(lambda: loading.status is not None and loading.status.is_mounted)
            badge = loading.status
            assert str(badge.renderable).startswith("Checking saved files.")
            await wait_until(lambda: badge.region.y == 0 and badge.region.right == 79)

            if outcome == "cancel":
                worker.cancel()
                with pytest.raises(WorkerCancelled):
                    await worker.wait()
            else:
                release.set()
                if outcome == "failure":
                    with pytest.raises(WorkerFailed):
                        await worker.wait()
                else:
                    await worker.wait()
            await wait_until(lambda: not app.query("#operation-loading"))
            assert loading.status is None
            assert loading.timer is None

    asyncio.run(scenario())


def test_presentation_handoff_stops_active_badge_and_timer(tmp_path, monkeypatch):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        loading = app.loading
        monkeypatch.setattr(loading, "DELAY", 0)
        monkeypatch.setattr(loading, "POLL_INTERVAL", .01)
        request = PresentationTestRequest(
            SetupRequest("fixture", "new", "example_experiment", "legacy_reference_display", {}), 1
        )
        ready = asyncio.Event()

        async def prepare():
            await ready.wait()
            app.exit(request)

        async with app.run_test(size=(80, 24)):
            worker = loading.run(app.screen, prepare, label="Checking test settings")
            await wait_until(lambda: loading.status is not None)
            badge = loading.status
            ready.set()
            await worker.wait()
            assert loading.closed and loading.timer is None
            assert loading.status is None and not badge.display
            assert not loading.operations
        assert app.return_value is request

    asyncio.run(scenario())
