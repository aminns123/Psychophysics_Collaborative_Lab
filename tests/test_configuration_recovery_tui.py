"""Exercise the actual Review, recovery and cancellation routes in Textual."""

import asyncio
import json

import pytest
from textual.widgets import Button, Checkbox, DataTable, Input, Static

from psychophysics_lab.config.sharing import make_document, read_document
from psychophysics_lab.ui.configuration_recovery import (
    ConfigurationRecoveryScreen, ConfirmHistoricalValues, RecoveryValueEditor,
)
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen
from test_configuration_sharing import ROOT
from test_parameter_accessibility import enter_review, selected_values
from psychophysics_lab.experiments._internal.registry import get_experiment


@pytest.mark.parametrize("schema", [1, 2])
def test_recovery_preview_keyboard_edit_cancel_and_save(tmp_path, schema):
    path = tmp_path/"historical settings.json"

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"lab runs")
        async with app.run_test(size=(80, 24)) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            original = review.request
            profile = app.monitor_profiles[original.monitor_profile_id]
            source = make_document(ROOT, original, profile)
            source["schema_version"] = schema
            source["stimuli"]["probe"]["parameters"]["length_deg"] = 1.0
            del source["stimuli"]["probe"]["parameters"]["width_deg"]
            source["experiment"]["values"]["retired_setting"] = 8
            raw = json.dumps(source).encode()
            path.write_bytes(raw)
            review.query_one("#review-import-configuration", Button).press()
            await pilot.pause()
            importer = app.screen
            importer.query_one("#configuration-path", Input).value = str(path)
            preview = importer.query_one("#configuration-preview", Button)
            recover = importer.query_one("#configuration-recover", Button)
            preview.press()
            await pilot.pause()
            assert importer.query_one("#configuration-approve", Button).disabled
            assert not recover.disabled
            assert "1 unmapped entries" in str(importer.query_one("#configuration-feedback", Static).renderable)
            assert review.request is original and not list(app.local_config_root.glob("parameter_files/**/configuration.json"))
            # Changing the selected file after preview invalidates the draft.
            path.write_bytes(raw + b"\n")
            recover.press()
            await pilot.pause()
            assert app.screen is importer and recover.disabled
            assert "Original file changed" in str(importer.query_one("#configuration-feedback", Static).renderable)
            path.write_bytes(raw)

            async def enter_draft():
                preview.press()
                await pilot.pause()
                recover.press()
                await pilot.pause()
                assert isinstance(app.screen, ConfigurationRecoveryScreen)
                return app.screen

            draft = await enter_draft()
            assert not draft.query("#run-presentation-test") and not draft.query("#review-export-configuration")
            assert draft.query_one("#recovery-save", Button).disabled
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is importer and review.request is original
            assert not list(app.local_config_root.glob("parameter_files/**/configuration.json"))

            draft = await enter_draft()
            await pilot.click("#recovery-accept-compatible")
            await pilot.pause()
            if schema == 1:
                assert isinstance(app.screen, ConfirmHistoricalValues)
                await pilot.press("escape")
                await pilot.pause()
                assert app.screen is draft and draft.draft.unresolved == len(draft.draft.rows)
                await pilot.click("#recovery-accept-compatible")
                await pilot.pause()
                app.screen.query_one("#recovery-confirm-checked", Button).press()
                await pilot.pause()
            assert draft.draft.unresolved == 1
            table = draft.query_one("#recovery-settings", DataTable)
            index = next(i for i, row in enumerate(draft.draft.rows)
                         if row.path == ("stimuli", "probe", "parameters", "width_deg"))
            table.move_cursor(row=index)
            table.focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, RecoveryValueEditor)
            editor = app.screen
            editor.query_one("#recovery-replace", Button).press()
            await pilot.pause()
            assert "explicit value" in str(editor.query_one("#recovery-editor-error", Static).renderable)
            editor.query_one("#recovery-value", Input).value = "0.013"
            editor.query_one("#recovery-replace", Button).press()
            await pilot.pause()
            assert app.screen is draft and draft.draft.unresolved == 0
            assert draft.query_one("#recovery-save", Button).disabled
            draft.query_one("#recovery-reviewed", Checkbox).value = True
            await pilot.pause()
            await pilot.click("#recovery-save")
            await pilot.pause()
            recovered = app.screen
            assert isinstance(recovered, ReviewScreen) and recovered is not review
            assert recovered.configuration_error is None and review.request == original
            probe = recovered.request.stimulus_snapshots["probe"]["document"]["parameters"]
            assert probe["length_deg"] == 1.0 and probe["width_deg"] == .013
            assert any(row[0] == "probe" and row[2] == "0.013" for row in recovered._review_rows)
            saved, = app.local_config_root.glob("parameter_files/**/configuration.json")
            assert read_document(saved)["schema_version"] == 2
            assert (saved.parent/"recovery"/"original.json").read_bytes() == path.read_bytes() == raw
            recovered.query_one("#run-presentation-test", Button).press()
            await pilot.pause()
            assert app.screen.request is recovered.request
            app.screen.query_one("#presentation-cancel", Button).press()
            await pilot.pause()
            assert app.screen is recovered
    asyncio.run(scenario())
