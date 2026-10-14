"""Simple researcher-facing luminance editor, preserving evidence and test provenance."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

from textual.widgets import Button, Input, Select, Static, Checkbox

from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import LuminanceCalibrationPoint
from psychophysics_lab.config.calibration_dataset import load_active, summary
from psychophysics_lab.ui.setup import PsyCoLabSetupApp
from psychophysics_lab.ui.luminance_data import LuminanceDataScreen

ROOT = Path(__file__).resolve().parents[1]


def test_blank_reading_is_neutral_and_test_add_keeps_existing_values(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "local_config"))
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile = save_profile(
        config_root(ROOT),
        replace(reference, id="simple_luminance", origin="local",
                calibration_method="photometer fake",
                luminance_calibration=(LuminanceCalibrationPoint(0.0, 0.5),
                                        LuminanceCalibrationPoint(0.5, 50.0),
                                        LuminanceCalibrationPoint(1.0, 500.0))),
    )
    initial = load_active(config_root(ROOT), profile)
    assert len(summary(initial)) == 3

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(120, 44)) as pilot:
            await app.push_screen(LuminanceDataScreen(profile))
            await pilot.pause()
            screen = app.screen
            assert screen.query_one("#dataset-add", Button).disabled
            assert screen.query_one("#dataset-readings", Input).value == ""
            assert "could not convert" not in str(screen.query_one("#dataset-feedback", Static).render()).lower()

            # Optional notes or export paths should not be parsed as floating point readings.
            screen.query_one("#dataset-notes", Input).value = "pilot configuration"
            await pilot.pause()
            assert "could not convert" not in str(screen.query_one("#dataset-feedback", Static).render()).lower()

            screen.query_one("#dataset-command", Input).value = "0.6"
            screen.query_one("#dataset-readings", Input).value = "60, 62"
            screen.query_one("#dataset-kind", Select).value = "synthetic"
            await pilot.pause()
            assert not screen.query_one("#dataset-add", Button).disabled
            screen.query_one("#dataset-add", Button).press()
            await pilot.pause()
            assert len(summary(screen.draft)) == 4
            assert len(summary(load_active(config_root(ROOT), profile))) == 3  # Draft != saved.
            row = next(p for p in summary(screen.draft) if p["screen_intensity"] == .6)
            assert row["n"] == 2 and row["luminance_cdm2"] == 61
            assert screen.query_one("#dataset-readings", Input).value == ""
            assert screen.query_one("#dataset-add", Button).disabled

            screen.query_one("#dataset-save", Button).press()
            await pilot.pause()
            assert len(summary(screen.saved)) == 4
            assert screen.profile.calibration_status == "manual_unverified"
            assert screen.profile.luminance_data_kind == "synthetic"
            assert screen.query_one("#dataset-task", Select).value == "add"
            assert "0.6" in [str(v) for _,v in screen.query_one("#dataset-selected", Select)._options]

    asyncio.run(scenario())


def test_replacement_requires_yes_and_leaves_saved_file_intact(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile = save_profile(
        config_root(ROOT),
        replace(reference, id="safe_replacement", origin="local",
                luminance_calibration=(LuminanceCalibrationPoint(0.0, .5),
                                        LuminanceCalibrationPoint(.5, 50.0),
                                        LuminanceCalibrationPoint(1.0, 500.0))),
    )
    saved = load_active(config_root(ROOT), profile)

    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"data")
        async with app.run_test(size=(120, 44)) as pilot:
            await app.push_screen(LuminanceDataScreen(profile))
            await pilot.pause()
            screen=app.screen
            screen.query_one("#dataset-task", Select).value="correct"
            screen.query_one("#dataset-selected", Select).value="0.5"
            screen.query_one("#dataset-readings", Input).value="49,51"
            await pilot.pause()
            assert screen.query_one("#dataset-confirm", Checkbox).display
            screen.query_one("#dataset-add", Button).press()
            await pilot.pause()
            assert "Confirm replacement" in str(screen.query_one("#dataset-feedback", Static).render())
            assert screen.draft == saved
            screen.query_one("#dataset-confirm", Checkbox).value=True
            screen.query_one("#dataset-add", Button).press()
            await pilot.pause()
            assert screen.draft != saved
            assert load_active(config_root(ROOT), profile) == saved
            screen.query_one("#dataset-back", Button).press()
            await pilot.pause()
            assert load_active(config_root(ROOT), profile) == saved
    asyncio.run(scenario())
