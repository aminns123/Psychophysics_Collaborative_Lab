"""Focused regressions for a single authoritative Review and table-only mode."""
import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Button, DataTable, Input

from psychophysics_lab.ui.review_files import json_value_line
from psychophysics_lab.ui.review_fullscreen import ReviewTableFullscreen
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen

ROOT = Path(__file__).resolve().parents[1]


def test_json_parameter_navigation_finds_scientific_value_not_metadata(tmp_path):
    experiment = tmp_path / "experiment.json"
    experiment.write_text(json.dumps({
        "parameter_info": {"logUNIT_UP": {"units": "log10"}},
        "schema_version": 1,
        "values": {"n_down": 3, "logUNIT_UP": 0.21},
    }, indent=2), encoding="utf-8")
    line = json_value_line(experiment, "logUNIT_UP")
    assert line > 1
    text = experiment.read_text(encoding="utf-8").splitlines()
    assert '"logUNIT_UP": 0.21' in text[line - 1]
    assert json_value_line(experiment, "absent") == 1

    stimulus = tmp_path / "stimulus.json"
    stimulus.write_text(json.dumps({
        "parameters": {"probe_length_deg": 0.5},
        "parameter_info": {"probe_length_deg": {"description": "not the value"}},
    }, indent=2), encoding="utf-8")
    line = json_value_line(stimulus, "probe_length_deg")
    assert '"probe_length_deg": 0.5' in stimulus.read_text().splitlines()[line - 1]


def test_editor_goto_for_parameter_json(tmp_path, monkeypatch):
    import psychophysics_lab.ui.editor as editor
    root = tmp_path / "checkout"
    root.mkdir()
    config = tmp_path / "config"
    config.mkdir()
    path = config / "draft.json"
    path.write_text('{"values": {"trial_count": 4}}')
    calls = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda command, **kw: calls.append((command, kw)))
    editor.open_parameter_file(root, path, config, executable="code", line=8)
    command = calls[-1][0]
    assert command[0] == "code"
    assert "--goto" in command
    assert command[-1] == f"{path.resolve()}:8"


@pytest.mark.parametrize("size", [(80, 24), (120, 40), (160, 55)])
def test_fullscreen_mirrors_review_and_can_edit_from_selected_cell(tmp_path, monkeypatch, size):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    opened = []
    monkeypatch.setattr(
        "psychophysics_lab.ui.editor.open_parameter_file",
        lambda *args, **kwargs: opened.append((args, kwargs)),
    )

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=size) as pilot:
            app.query_one("#participant", Input).value = "EXPANDED"
            app.screen.query_one("#configure", Button).press()
            await pilot.pause()
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            review = app.screen
            assert isinstance(review, ReviewScreen)
            original = review.query_one("#resolved-settings-table", DataTable)
            original_count = original.row_count
            assert original_count > 0
            assert review.query_one("#review-expand-table", Button)

            review.query_one("#review-expand-table", Button).press()
            await pilot.pause()
            expanded = app.screen
            assert isinstance(expanded, ReviewTableFullscreen)
            table = expanded.query_one("#expanded-settings-table", DataTable)
            assert table.row_count == original_count
            assert table.region.width == size[0]
            assert table.region.height > 0
            assert not expanded.query("#hub-nav")

            row = next(index for index in range(table.row_count)
                       if str(table.get_row_at(index)[0]) == "Adaptive"
                       and "Increase in probe difference" in str(table.get_row_at(index)[1]))
            table.move_cursor(row=row, column=2)
            table.focus()
            await pilot.press("enter")
            await pilot.pause()
            assert opened
            # Unsaved experiment values export to local JSON, then open
            # at the actual field (not line one).
            assert opened[-1][1]["line"] > 1
            assert table.row_count == review.query_one("#resolved-settings-table", DataTable).row_count

            expanded.query_one("#expanded-review-back", Button).press()
            await pilot.pause()
            assert app.screen is review
            assert original.cursor_row == row

    asyncio.run(asyncio.wait_for(scenario(), 45))
