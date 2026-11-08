"""Actual Textual Save/Apply interaction and persistence tests, no physical display needed."""
from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path

import pytest
from textual.widgets import Button, Collapsible, Input, Select, Static

from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.local import load_presets, config_root
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.setup import (
    DisplayCheckScreen, ExperimentParametersScreen, PsyCoLabSetupApp,
)
from psychophysics_lab.ui.profiles import ProfileScreen
from psychophysics_lab.experiments.contrast_sensitivity import SPEC as CSF_SPEC

ROOT = Path(__file__).resolve().parents[1]


def test_calibration_save_unbound_draft_updates_visible_profile_and_survives_restart(tmp_path, monkeypatch):
    """A researcher can save screen dimensions without first detecting a monitor."""
    machine = tmp_path / "machine_configuration"
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(machine))

    async def scenario():
        data_root = tmp_path / "experiment_data"
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=data_root)
        async with app.run_test(size=(100, 30)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            app.screen.query_one("#edit-profile", Button).press()
            await pilot.pause()
            profile_screen = app.screen
            assert isinstance(profile_screen, ProfileScreen)
            profile_screen.query_one("#profile-physical_width_m", Input).value = "0.535"
            profile_screen.query_one("#profile-physical_height_m", Input).value = "0.301"
            profile_screen.query_one("#profile-viewing_distance_m", Input).value = "0.75"
            profile_screen.query_one("#profile-pixel-width", Input).value = "2560"
            profile_screen.query_one("#profile-pixel-height", Input).value = "1440"
            profile_screen.query_one("#profile-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            assert app.screen.query_one("#geometry-monitor", Select).value == "legacy_reference_display_local"
            saved = app.monitor_profiles["legacy_reference_display_local"]
            assert saved.expected_resolution_px == (2560, 1440)
            assert saved.physical_width_m == pytest.approx(.535)
            assert saved.physical_height_m == pytest.approx(.301)
            assert saved.viewing_distance_m == pytest.approx(.75)
            assert saved.display_binding is None
            assert not saved.qualified_experiments
            assert saved.geometry_status == "manual_unverified"
            summary = str(app.screen.query_one("#spatial-calibration-summary", Static).render())
            assert "Pixels/degree" in summary
            assert "2560" in str(app.screen.query_one("#geometry-preview", Static).render())

        # Reconstruct the program, do not just inspect in-memory screen state.
        fresh = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=data_root)
        assert "legacy_reference_display_local" in fresh.monitor_profiles
        assert fresh.monitor_profiles["legacy_reference_display_local"].physical_width_m == pytest.approx(.535)
        assert (machine / "profiles" / "legacy_reference_display_local" / "revision_000001.json").is_file()
    asyncio.run(scenario())


def test_calibration_invalid_save_keeps_editor_open_and_shows_fixed_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "machine"))
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(80, 24)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            app.screen.query_one("#edit-profile", Button).press()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProfileScreen)
            screen.query_one("#profile-physical_width_m", Input).value = "0"
            screen.query_one("#profile-save", Button).press()
            await pilot.pause()
            assert app.screen is screen
            feedback = str(screen.query_one("#profile-save-feedback", Static).render())
            assert "Display NOT saved" in feedback
            assert "positive" in feedback
            assert not (tmp_path / "machine" / "profiles").exists()
    asyncio.run(scenario())


def test_display_revision_save_uses_latest_value_and_preserves_previous_version(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "machine"))
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(100, 30)) as pilot:
            app.query_one("#nav-display", Button).press()
            await pilot.pause()
            app.screen.query_one("#edit-profile", Button).press()
            await pilot.pause()
            profile = app.screen
            profile.query_one("#profile-physical_width_m", Input).value = "0.500"
            profile.query_one("#profile-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            app.screen.query_one("#edit-profile", Button).press()
            await pilot.pause()
            second = app.screen
            second.query_one("#profile-physical_width_m", Input).value = "0.590"
            second.query_one("#profile-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DisplayCheckScreen)
            saved = app.monitor_profiles["legacy_reference_display_local"]
            assert saved.revision == 2
            assert saved.physical_width_m == pytest.approx(.590)
            assert "590" in str(app.screen.query_one("#geometry-preview", Static).render())
            folder = tmp_path / "machine" / "profiles" / "legacy_reference_display_local"
            assert sorted(p.name for p in folder.glob("revision_*.json")) == [
                "revision_000001.json", "revision_000002.json"
            ]
            import json
            older = json.loads((folder / "revision_000001.json").read_text())
            assert older["physical_width_m"] == pytest.approx(.500)
    asyncio.run(scenario())


def test_experiment_preset_save_load_reopen_and_duplicate_block(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "machine"))
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "data")
        experiment = get_experiment("contrast_sensitivity")
        defaults = experiment.field_defaults()
        async with app.run_test(size=(100, 30)) as pilot:
            app.push_screen(
                ExperimentParametersScreen(
                    data_root=tmp_path / "data", participant_id="T001",
                    session_mode="new", experiment=experiment,
                    monitor_profile_id="legacy_reference_display", defaults=defaults,
                )
            )
            await pilot.pause()
            screen = app.screen
            presets_panel = next(c for c in screen.query(Collapsible) if c.title == "Local presets")
            presets_panel.collapsed = False
            await pilot.pause()
            screen.query_one("#field-staircases-per-condition", Input).value = "3"
            screen.query_one("#field-frequencies-cpd", Input).value = "1,4,8"
            screen.query_one("#preset-name", Input).value = "three_conditions"
            screen.query_one("#save-preset", Button).press()
            await pilot.pause()
            assert "saved successfully" in str(screen.query_one("#config-status", Static).render())
            assert load_presets(app.local_config_root, experiment.id)["three_conditions"]["frequencies_cpd"] == "1,4,8"
            screen.query_one("#field-staircases-per-condition", Input).value = "2"
            screen.query_one("#field-frequencies-cpd", Input).value = "2,8"
            # Existing preset requires a new name; it may never silently overwrite.
            screen.query_one("#save-preset", Button).press()
            await pilot.pause()
            assert "already exists" in str(screen.query_one("#config-status", Static).render())
            assert load_presets(app.local_config_root, experiment.id)["three_conditions"]["frequencies_cpd"] == "1,4,8"
            screen.query_one("#config-preset", Select).value = "three_conditions"
            screen.query_one("#load-preset", Button).press()
            await pilot.pause()
            assert screen.query_one("#field-staircases-per-condition", Input).value == "3"
            assert screen.query_one("#field-frequencies-cpd", Input).value == "1,4,8"
            assert "loaded successfully" in str(screen.query_one("#config-status", Static).render())
            assert screen._collect()["staircases_per_condition"] == 3
            # The explicit Update action archives an old version and saves
            # the new values, rather than silently overwriting on Save new.
            screen.query_one("#field-frequencies-cpd", Input).value = "1,5,9"
            screen.query_one("#update-preset", Button).press()
            await pilot.pause()
            assert "updated successfully" in str(screen.query_one("#config-status", Static).render())
            assert load_presets(app.local_config_root, experiment.id)["three_conditions"]["frequencies_cpd"] == "1,5,9"
            backups = list((tmp_path / "machine" / "presets" /
                            experiment.id / ".history").glob("three_conditions_*.json"))
            assert len(backups) == 1
            import json
            assert json.loads(backups[0].read_text())["values"]["frequencies_cpd"] == "1,4,8"
            screen.query_one("#review", Button).press()
            await pilot.pause()
            assert app.screen.request.experiment_values["frequencies_cpd"] == "1,5,9"
            app.pop_screen()
            await pilot.pause()
            assert screen.query_one("#field-frequencies-cpd", Input).value == "1,5,9"
    asyncio.run(scenario())


def test_save_new_preset_rejections_preserve_research_files(tmp_path, monkeypatch):
    config = tmp_path / "configuration"
    data = tmp_path / "archive"
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(config))
    experiment = get_experiment("contrast_sensitivity")
    directory = config / "presets" / experiment.id
    retained = {
        directory / "future.json": json.dumps({
            "schema_version": 999, "experiment_id": experiment.id, "values": {"future_key": 4},
        }).encode(),
        directory / "malformed.json": b'{"schema_version":',
        directory / "Retained.json": json.dumps({
            "schema_version": 1, "experiment_id": experiment.id, "values": experiment.field_defaults(),
        }).encode(),
        directory / "occupied.json" / "retained.txt": b"directory entry to keep",
        config / "preferences.json": b'{"example":true}',
        config / "profiles" / "archived-calibration.json": b'{"geometry_status":"unverified"}',
        config / "parameter_files" / experiment.id / "configuration_imported" / "configuration.json":
            b'{"schema_version":2,"example":"already imported"}',
        data / "historical" / "run_001" / "trials.tsv": b"trial_index\tcorrect\n1\t1\n",
    }
    for path, contents in retained.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)

    def hashes():
        return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in retained}

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=data)
        async with app.run_test(size=(100, 30)) as pilot:
            app.push_screen(ExperimentParametersScreen(
                data_root=data, participant_id="TEST_ONLY", session_mode="new",
                experiment=experiment, monitor_profile_id="legacy_reference_display",
                defaults=experiment.field_defaults(),
            ))
            await pilot.pause()
            screen = app.screen
            next(panel for panel in screen.query(Collapsible) if panel.title == "Local presets").collapsed = False
            await pilot.pause()
            assert hashes() == {path: hashlib.sha256(raw).hexdigest() for path, raw in retained.items()}
            before = hashes()
            entries = sorted(directory.iterdir())

            async def reject(name, message):
                screen.query_one("#preset-name", Input).value = name
                screen.query_one("#save-preset", Button).press()
                await pilot.pause()
                status = str(screen.query_one("#config-status", Static).render())
                assert "Preset NOT saved" in status and message in status
                assert hashes() == before
                assert sorted(directory.iterdir()) == entries

            names = ["future", "malformed", "occupied", "Retained"]
            if (directory / "retained.json").exists():
                names.append("retained")
            for name in names:
                await reject(name, "Choose a new preset name")
            await reject("../escape", "invalid filename")

            operation = "rename" if os.name == "nt" else "link"
            publish = getattr(os, operation)

            def fail_publish(source, destination):
                if Path(destination) == directory / "cannot_publish.json":
                    raise PermissionError("injected publication failure")
                return publish(source, destination)

            with monkeypatch.context() as patch:
                patch.setattr(os, operation, fail_publish)
                await reject("cannot_publish", "Check the preset folder and try again")

    asyncio.run(scenario())
