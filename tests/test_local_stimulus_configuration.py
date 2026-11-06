"""Ordinary configuration uses existing local JSON, never shared class edits."""
import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Button, DataTable, Input, Select

from psychophysics_lab.config.stimulus_parameters import load_parameters
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentParametersScreen
from psychophysics_lab.ui.stimulus_editor import StimulusValueEditor
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
from test_parameter_accessibility import enter_review, selected_values

ROOT = Path(__file__).resolve().parents[1]


def probe_row(review):
    return next(i for i, a in enumerate(review._row_authorities)
                if a["slot"] == "probe" and a["field"] == "length_deg")


def set_probe(editor, length, width):
    for key, value in (("length_deg", length), ("width_deg", width)):
        index = next(i for i, f in enumerate(editor.panel.stimulus.parameters) if f.key == key)
        editor.query_one(f"#stimulus-value-{index}", Input).value = str(value)


@pytest.mark.parametrize("expanded", [False, True])
def test_enter_edits_probe_and_invalid_experiment_does_not_save_json(tmp_path, monkeypatch, expanded):
    shared = ROOT / "src/psychophysics_lab/stimulus_library.py"
    original = shared.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Routine configuration opened an external editor")
    monkeypatch.setattr("psychophysics_lab.ui.setup.open_source", forbidden)
    monkeypatch.setattr("psychophysics_lab.ui.editor.open_parameter_file", forbidden)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(80, 24)) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            review.query_one("#review-group", Select).value = "probe"
            await pilot.pause()
            row = review._visible_rows.index(probe_row(review))
            if expanded:
                review.query_one("#review-expand-table", Button).press()
                await pilot.pause()
                table = app.screen.query_one("#expanded-settings-table", DataTable)
            else:
                table = review.query_one("#resolved-settings-table", DataTable)
            table.move_cursor(row=row, column=2)
            table.focus()
            await pilot.press("enter")
            await pilot.pause()
            editor = app.screen
            assert isinstance(editor, StimulusValueEditor) and editor.focus_key == "length_deg"
            set_probe(editor, 1.4, .035)
            editor.query_one("#stimulus-values-apply", Button).press()
            await pilot.pause()
            config = app.screen
            assert isinstance(config, ExperimentParametersScreen)
            config.query_one("#field-ring-radius-deg", Input).value = ".1"
            config.query_one("#review", Button).press()
            await pilot.pause()
            assert app.screen is config
            directory = app.local_config_root / "parameter_files" / "ellipse_centre"
            assert not list(directory.glob("*.json"))
            config.query_one("#field-ring-radius-deg", Input).value = ".5"
            config.query_one("#review", Button).press()
            await pilot.pause()
            assert app.screen is review and not review.configuration_error
            path = review._file_sources["stimuli"]["probe"]
            assert path == directory / "probe.json"
            selected = load_parameters(path, get_stimulus("probe_line"))
            assert selected == review.request.stimulus_snapshots["probe"]
            assert selected["document"]["parameters"]["length_deg"] == 1.4
            assert selected["document"]["parameters"]["width_deg"] == .035
            assert selected["document"]["parameter_info"]["display_contrast"]["source"] == "controlled by experiment each trial"
            app.verify_settings_current(review.request)
            # A later external edit still blocks Test/Run until re-reviewed.
            path.write_text(path.read_text() + "\n", encoding="utf-8")
            with pytest.raises(ValueError, match="Review again"):
                app.verify_settings_current(review.request)
    asyncio.run(scenario())
    assert shared.read_bytes() == original


def test_saved_selection_reloads_in_fresh_tui_and_edits_preserve_old_json(tmp_path, monkeypatch):
    local = tmp_path / "local configuration"
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(local))
    saved = {}
    async def create():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(100, 36)) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            review._edit_review_parameter(probe_row(review))
            await pilot.pause()
            set_probe(app.screen, 1.3, .025)
            app.screen.query_one("#stimulus-values-apply", Button).press()
            await pilot.pause()
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            saved["path"] = review._file_sources["stimuli"]["probe"]
            saved["bytes"] = saved["path"].read_bytes()
    asyncio.run(create())
    async def reload_and_edit():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(100, 36)) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            review._edit_experiment_inputs()
            await pilot.pause()
            config = app.screen
            panel = next(p for p in config.query(StimulusParametersPanel) if p.slot == "probe")
            # Defaults remain defaults until the researcher selects local JSON.
            assert panel.current()["document"]["parameters"]["length_deg"] == 1.
            panel.query_one("#stimulus-preset-probe", Select).value = str(saved["path"])
            await pilot.pause()
            assert panel.current()["document"]["parameters"]["length_deg"] == 1.3
            config.query_one("#review", Button).press()
            await pilot.pause()
            assert review.request.stimulus_snapshots["probe"]["document"]["parameters"]["width_deg"] == .025
            review._edit_review_parameter(probe_row(review))
            await pilot.pause()
            set_probe(app.screen, 1.6, .04)
            app.screen.query_one("#stimulus-values-apply", Button).press()
            await pilot.pause()
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            path = review._file_sources["stimuli"]["probe"]
            assert path != saved["path"] and path.parent == saved["path"].parent
            assert saved["path"].read_bytes() == saved["bytes"]
            assert json.loads(path.read_text())["parameters"]["length_deg"] == 1.6
            app.verify_settings_current(review.request)
    asyncio.run(reload_and_edit())


def test_stimulus_implementation_authoring_remains_explicitly_available(tmp_path, monkeypatch):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        opened = []
        monkeypatch.setattr(app, "inspect_source", lambda path: opened.append(path))
        async with app.run_test(size=(80, 24)) as pilot:
            app.open_hub_page("stimuli")
            await pilot.pause()
            app.screen.query_one("#view-shared-stimulus-library", Button).press()
            await pilot.pause()
            assert opened == [ROOT / "src/psychophysics_lab/stimulus_library.py"]
    asyncio.run(scenario())
