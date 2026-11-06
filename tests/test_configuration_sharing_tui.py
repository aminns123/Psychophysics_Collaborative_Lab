"""Native Textual sharing routes use the same Review/Test/Run settings."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Static, DataTable, DirectoryTree, Select

from psychophysics_lab.config.sharing import make_document, read_document, write_export
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen
from psychophysics_lab.ui.configuration_sharing import ConfigurationSharingScreen, ConfigurationFilePicker, JSONTree
from test_parameter_accessibility import OFFICIAL, selected_values, enter_review
from test_local_stimulus_configuration import probe_row, set_probe
from psychophysics_lab.experiments._internal.registry import get_experiment

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("identity", OFFICIAL)
def test_review_import_round_trip_for_every_official_experiment(tmp_path, identity):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"local data")
        async with app.run_test(size=(100, 36)) as pilot:
            old = await enter_review(app, pilot, identity, selected_values(get_experiment(identity)))
            request = old.request
            profile = app.monitor_profiles[request.monitor_profile_id]
            document = make_document(ROOT, request, profile)
            path = tmp_path/"downloaded configuration.json"
            write_export(path, document)
            old.query_one("#review-import-configuration", Button).press()
            await pilot.pause()
            importer = app.screen
            assert isinstance(importer, ConfigurationSharingScreen)
            importer.query_one("#configuration-path", Input).value = str(path)
            importer.query_one("#configuration-preview", Button).press()
            await pilot.pause()
            assert importer.query_one("#configuration-differences", DataTable).row_count > len(request.experiment_values)
            assert not importer.query_one("#configuration-approve", Button).disabled
            assert old.request == request
            importer.query_one("#configuration-approve", Button).press()
            await pilot.pause()
            review = app.screen
            assert isinstance(review, ReviewScreen) and review is not old
            assert review.configuration_error is None
            assert review.request.experiment_values == request.experiment_values
            assert make_document(ROOT, review.request, profile) == document
            assert review.request.monitor_profile_id == request.monitor_profile_id
            assert review.request.participant_id == request.participant_id
            assert all(Path(p).is_file() for p in app.review_parameter_files[app.settings_key(review.request)])
            app.verify_settings_current(review.request)
    asyncio.run(scenario())


def test_ellipse_two_researchers_save_export_browse_preview_cancel_import_and_test(tmp_path, monkeypatch):
    shared_class = ROOT/"src/psychophysics_lab/stimulus_library.py"
    original_source = shared_class.read_bytes()
    export = tmp_path/"files exchanged between labs"/"ellipse settings.json"
    export.parent.mkdir()
    sender_local = tmp_path/"sender configuration"
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(sender_local))
    async def sender():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"sender data")
        async with app.run_test(size=(80, 24)) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre",
                selected_values(get_experiment("ellipse_centre")) | {"max_trials": 4, "staircases_per_condition": 1})
            review._edit_review_parameter(probe_row(review))
            await pilot.pause()
            set_probe(app.screen, 1.4, .035)
            app.screen.query_one("#stimulus-values-apply", Button).press()
            await pilot.pause()
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            review.query_one("#review-save-configuration", Button).press()
            await pilot.pause()
            assert "Saved new local configuration" in str(review.query_one("#review-status", Static).renderable)
            saved = list(sender_local.glob("parameter_files/ellipse_centre/configuration_*/configuration.json"))
            assert len(saved) == 1
            review.query_one("#review-export-configuration", Button).press()
            await pilot.pause()
            app.screen.query_one("#configuration-path", Input).value = str(export)
            app.screen.query_one("#configuration-export", Button).press()
            await pilot.pause()
            assert read_document(export) == read_document(saved[0])
    asyncio.run(sender())
    sender_bytes = {p: p.read_bytes() for p in sender_local.rglob("*.json")}
    recipient_local = tmp_path/"recipient configuration"
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(recipient_local))
    sentinel = tmp_path/"recipient data"/"historical result.txt"
    sentinel.parent.mkdir()
    sentinel.write_text("Preserve original data")
    async def recipient():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=sentinel.parent)
        async with app.run_test(size=(80, 24)) as pilot:
            old = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            old.request = replace(old.request, participant_id="RECIPIENT_ONLY")
            previous = deepcopy(old.request)
            old.query_one("#review-import-configuration", Button).press()
            await pilot.pause()
            importer = app.screen
            importer.query_one("#configuration-browse", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ConfigurationFilePicker)
            picker = app.screen
            picker.query_one("#configuration-picker-location", Input).value = str(export.parent)
            picker.query_one("#configuration-picker-open", Button).press()
            await pilot.pause()
            tree = picker.query_one(JSONTree)
            assert tree.path == export.parent
            tree.post_message(DirectoryTree.FileSelected(tree.root, export))
            await pilot.pause()
            assert app.screen is importer and importer.query_one("#configuration-path", Input).value == str(export)
            importer.query_one("#configuration-preview", Button).press()
            await pilot.pause()
            assert "differences" in str(importer.query_one("#configuration-feedback", Static).renderable)
            assert old.request == previous
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is old and old.request == previous
            assert not list(recipient_local.glob("parameter_files/**/configuration.json"))
            old.query_one("#review-import-configuration", Button).press()
            await pilot.pause()
            importer = app.screen
            importer.query_one("#configuration-path", Input).value = str(export)
            importer.query_one("#configuration-preview", Button).press()
            await pilot.pause()
            importer.query_one("#configuration-approve", Button).press()
            await pilot.pause()
            review = app.screen
            assert isinstance(review, ReviewScreen) and not review.configuration_error
            assert review.request.participant_id == "RECIPIENT_ONLY"
            assert review.request.monitor_profile_id == previous.monitor_profile_id
            assert review.request.data_root == previous.data_root
            assert review.request.stimulus_snapshots["probe"]["document"]["parameters"]["length_deg"] == 1.4
            assert review.request.stimulus_snapshots["probe"]["document"]["parameters"]["width_deg"] == .035
            assert any(row[0] == "probe" and row[2] == "1.4" for row in review._review_rows)
            imported = review.request
            review.query_one("#run-presentation-test", Button).press()
            await pilot.pause()
            assert app.screen.request is imported
            app.screen.query_one("#presentation-cancel", Button).press()
            await pilot.pause()
            review._edit_experiment_inputs()
            await pilot.pause()
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            assert app.screen is review
            assert review.request.stimulus_snapshots == imported.stimulus_snapshots
            app.verify_settings_current(review.request)
            # Execution no longer depends on the sender's/download location.
            export.unlink()
            app.verify_settings_current(review.request)
            review.query_one("#review-run-intent", Select).value = "simulation"
            await pilot.pause()
            review.query_one("#run-simulation", Button).press()
            await pilot.pause()
            assert app.screen is not review, str(review.query_one("#review-status", Static).renderable)
            launch = app.screen._launch_request()
            assert launch.stimulus_snapshots == imported.stimulus_snapshots
            app.pop_screen()
            await pilot.pause()
            review.query_one("#back", Button).press()
            await pilot.pause()
            assert app.screen is old and old.request == previous
            old._edit_experiment_inputs()
            await pilot.pause()
            from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
            probe = next(p for p in app.screen.query(StimulusParametersPanel) if p.slot == "probe")
            assert probe.current()["document"]["parameters"] == previous.stimulus_snapshots["probe"]["document"]["parameters"]
    asyncio.run(recipient())
    assert shared_class.read_bytes() == original_source
    assert all(p.read_bytes() == data for p, data in sender_bytes.items())
    assert sentinel.read_text() == "Preserve original data"


def test_invalid_and_changed_import_do_not_partially_apply(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"data")
        async with app.run_test(size=(80, 24)) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            previous = deepcopy(review.request)
            drafts = deepcopy(app.config_drafts)
            path = tmp_path/"download.json"
            good = make_document(ROOT, review.request, app.monitor_profiles[review.request.monitor_profile_id])
            write_export(path, good)
            review.query_one("#review-import-configuration", Button).press()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#configuration-path", Input).value = str(path)
            screen.query_one("#configuration-preview", Button).press()
            await pilot.pause()
            bad = deepcopy(good)
            bad["experiment"]["values"]["ring_radius_deg"] = -1
            path.write_text(json.dumps(bad))
            screen.query_one("#configuration-approve", Button).press()
            await pilot.pause()
            assert app.screen is screen and screen.query_one("#configuration-approve", Button).disabled
            assert "nothing was applied" in str(screen.query_one("#configuration-feedback", Static).renderable)
            screen.query_one("#configuration-preview", Button).press()
            await pilot.pause()
            assert screen.query_one("#configuration-approve", Button).disabled
            assert review.request == previous and app.config_drafts == drafts
            assert not list(app.local_config_root.glob("parameter_files/**/configuration.json"))
    asyncio.run(scenario())


def test_import_identifies_another_experiment_and_keeps_existing_review(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"data")
        async with app.run_test(size=(80, 24)) as pilot:
            old = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            previous = deepcopy(old.request)
            from test_configuration_sharing import request_for
            incoming, profile = request_for("orientation_task")
            path = tmp_path/"another study.json"
            write_export(path, make_document(ROOT, incoming, profile))
            old.query_one("#review-import-configuration", Button).press()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#configuration-path", Input).value = str(path)
            screen.query_one("#configuration-preview", Button).press()
            await pilot.pause()
            assert "orientation_task" in str(screen.query_one("#configuration-feedback", Static).renderable)
            screen.query_one("#configuration-approve", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen) and app.screen.request.experiment_id == "orientation_task"
            app.screen._edit_experiment_inputs()
            await pilot.pause()
            assert app.screen.experiment.id == "orientation_task"
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            app.screen.query_one("#back", Button).press()
            await pilot.pause()
            assert app.screen is old and old.request == previous
    asyncio.run(scenario())
