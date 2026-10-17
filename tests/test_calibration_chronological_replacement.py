"""Chronological calibration UX: safe replacement, honest test provenance and clear next actions."""
import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from textual.widgets import Button, Checkbox, Input, Select, Static

from psychophysics_lab.config.calibration_dataset import (
    active_directory, load_active, save_active, observation, physical_snapshot,
    physical_snapshot_differences, replacement_draft_for_current_display, summary,
)
from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import LuminanceCalibrationPoint
from psychophysics_lab.ui.calibration_stages import stage_next_action
from psychophysics_lab.ui.luminance_data import LuminanceDataScreen
from psychophysics_lab.ui.setup import DisplayCheckScreen, PsyCoLabSetupApp

ROOT = Path(__file__).resolve().parents[1]


def _saved_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "calibration"))
    root = config_root(ROOT)
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile = save_profile(root, replace(
        reference, id="chronological_test_monitor", origin="local",
        calibration_method="photometer fake",
        luminance_calibration=(
            LuminanceCalibrationPoint(0.0, 0.1),
            LuminanceCalibrationPoint(0.3, 25.0),
            LuminanceCalibrationPoint(1.0, 500.0),
        ),
    ))
    profile, previous = save_active(root, profile, load_active(root, profile), expected_version=0)
    changed = save_profile(root, replace(profile, viewing_distance_m=profile.viewing_distance_m + 0.25),
                           expected_revision=profile.revision)
    assert physical_snapshot_differences(changed, previous)
    return root, profile, changed, previous


def test_prepare_current_display_draft_requires_yes_and_never_modifies_old_data(tmp_path, monkeypatch):
    root, old_profile, changed, previous = _saved_profile(monkeypatch, tmp_path)
    before = deepcopy(previous)
    with pytest.raises(ValueError, match="Choose Yes"):
        replacement_draft_for_current_display(changed, previous)
    draft = replacement_draft_for_current_display(changed, previous, confirmed=True)
    assert draft["observations"] == []
    assert draft["physical_snapshot"] == physical_snapshot(changed)
    assert draft["version"] == previous["version"]
    assert draft["method"] == ""
    assert previous == before
    assert load_active(root, changed) == previous


def test_explicit_replacement_ui_preserves_prior_readings_until_save(tmp_path, monkeypatch):
    root, old_profile, changed, previous = _saved_profile(monkeypatch, tmp_path)
    active = active_directory(root, changed) / "luminance.json"
    original = active.read_bytes()

    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path/"participants")
        async with app.run_test(size=(125, 45)) as pilot:
            await app.push_screen(LuminanceDataScreen(changed))
            await pilot.pause()
            page = app.screen
            assert page.query_one("#dataset-start-current", Button).display
            assert "viewing distance" in str(
                page.query_one("#dataset-replacement-guidance", Static).render()
            )
            page.query_one("#dataset-save", Button).press()
            await pilot.pause()
            assert "Tick Yes" in str(page.query_one("#dataset-feedback", Static).render())
            assert active.read_bytes() == original

            page.query_one("#dataset-start-current", Button).press()
            await pilot.pause()
            assert "Choose Yes" in str(page.query_one("#dataset-feedback", Static).render())
            assert page.draft == page.saved

            page.query_one("#dataset-start-confirm", Checkbox).value = True
            page.query_one("#dataset-start-current", Button).press()
            await pilot.pause()
            assert page._replacement_started
            assert page.draft["observations"] == []
            assert page.draft["physical_snapshot"] == physical_snapshot(changed)
            assert page.query_one("#dataset-kind", Select).value == "synthetic"
            assert not page.query_one("#dataset-start-current", Button).display
            assert active.read_bytes() == original

            page.query_one("#dataset-save", Button).press()
            await pilot.pause()
            assert "no readings" in str(page.query_one("#dataset-feedback", Static).render())
            assert active.read_bytes() == original

            page.query_one("#dataset-command", Input).value = "0.3"
            page.query_one("#dataset-readings", Input).value = "24.5, 25.5"
            page.query_one("#dataset-add", Button).press()
            await pilot.pause()
            assert len(page.draft["observations"]) == 2
            assert len(page.saved["observations"]) == len(previous["observations"])

            page.query_one("#dataset-save", Button).press()
            await pilot.pause()
            assert page.profile.calibration_status == "manual_unverified"
            assert page.profile.luminance_data_kind == "synthetic"
            assert len(summary(page.saved)) == 1
            assert not page._replacement_started
            assert not page.query_one("#dataset-start-current", Button).display

    asyncio.run(scenario())
    assert active.read_bytes() != original
    history = active.parent / ".history"
    assert any(json.loads(file.read_text())["observations"] == previous["observations"]
               for file in history.glob("*.json"))


def test_six_calibration_pages_present_next_action_without_certification(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path/"config"))
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path/"data")
        async with app.run_test(size=(118, 39)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            page = app.screen
            assert isinstance(page, DisplayCheckScreen)
            from psychophysics_lab.config.calibration_progress import calibration_progress
            for key in ("bind", "geometry", "spatial", "luminance", "timing", "review"):
                page._go_to_stage(key)
                await pilot.pause()
                assert "NEXT:" in str(page.query_one("#calibration-next-action", Static).render())
                assert page.active_calibration_stage == key
                expected = stage_next_action(key, calibration_progress(page._profile(), app.local_config_root))
                assert "NEXT:" in expected
            page._go_to_stage("luminance")
            guidance=str(page.query_one("#calibration-next-action", Static).render()).lower()
            assert "next:" in guidance and "photometer" in guidance
    asyncio.run(scenario())


def test_keep_old_test_values_goes_to_experiment_without_modifying_measurements(tmp_path, monkeypatch):
    root, old_profile, changed, previous = _saved_profile(monkeypatch, tmp_path)
    active=active_directory(root, changed)/"luminance.json"
    original=active.read_bytes()

    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/"participants")
        async with app.run_test(size=(120, 40)) as pilot:
            await app.push_screen(LuminanceDataScreen(changed))
            await pilot.pause()
            page=app.screen
            page.query_one("#dataset-keep-test",Button).press()
            await pilot.pause()
            assert len(app.screen_stack)==1
            assert app.query_one("#run-intent",Select).value=="test"
            assert "retained unchanged" in str(
                app.query_one("#setup-status",Static).render()
            )
    asyncio.run(scenario())
    assert active.read_bytes()==original
    assert load_active(root, changed)==previous
