"""All tests keep machine preferences/calibration outside the real workspace."""
import pytest

@pytest.fixture(autouse=True)
def isolated_local_configuration(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path_factory.mktemp("local_configuration")))


@pytest.fixture(autouse=True)
def wait_for_textual_mounts(monkeypatch):
    """Pilot idle can precede mounting a newly pushed large scenario screen.

    Wait on real widget state, not a forced value or a fixed machine-speed
    assumption. This changes only the test driver, never application timing.
    """
    from textual.pilot import Pilot
    original_pause = Pilot.pause

    async def mounted_pause(pilot, delay=None):
        await original_pause(pilot, delay)
        for _ in range(100):
            if not pilot.app.screen_stack:
                return
            screen = pilot.app.screen
            widgets = list(screen.query("*"))
            if screen.is_mounted and all(widget.is_mounted for widget in widgets):
                await original_pause(pilot, .05)
                return
            await original_pause(pilot, .02)
        raise AssertionError("Textual screen did not finish mounting before the test assertion.")

    monkeypatch.setattr(Pilot, "pause", mounted_pause)
