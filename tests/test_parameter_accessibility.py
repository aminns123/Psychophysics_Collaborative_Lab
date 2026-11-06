"""Researcher edits must reach the existing scientific path and recorded snapshot."""
import asyncio
import csv
import json
from pathlib import Path

import numpy as np
import pytest
from textual.widgets import Button, DataTable, Input, Select, Static, TextArea

from psychophysics_lab.config.stimulus_parameters import document_for, resolve_stimuli
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.researcher import RunContext
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui.full_text import FullTextScreen
from psychophysics_lab.ui.settings_review import describe_settings, review_rows
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen
from psychophysics_lab.ui.stimulus_editor import StimulusValueEditor
from simulations.run import simulate

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ("contrast_sensitivity", "contrast_sensitivity_windowed", "line_position_baseline",
            "line_position_flanker", "ellipse_centre", "ellipse_major_axis", "orientation_adaptive",
            "orientation_task", "probe_above_below", "example_experiment")


def selected_values(spec):
    # Explicit test choices for required inputs, never new production defaults.
    supplied = {"ring_increment": .03, "probe_vertical_offset_deg": .4, "flanker_cpd": 2.}
    return spec.normalise_values({k: v for k, v in supplied.items() if k in spec.field_defaults()})


async def enter_review(app, pilot, identity, values):
    app.query_one("#participant", Input).value = "PARAMETER_ACCESS"
    app.query_one("#experiment", Select).value = identity
    await pilot.pause()
    app.screen.query_one("#configure", Button).press()
    await pilot.pause()
    config = app.screen
    config.defaults.update(values)
    app.config_drafts.setdefault(config.draft_key, {}).update(values)
    for key, value in values.items():
        matches = config.query("#field-" + key.replace("_", "-"))
        if matches:
            widget = matches.first()
            widget.value = value if isinstance(widget, Select) else str(value)
    config.query_one("#review", Button).press()
    await pilot.pause()
    assert isinstance(app.screen, ReviewScreen)
    return app.screen


@pytest.mark.parametrize("identity", OFFICIAL)
def test_every_declared_scientific_input_visible_in_actual_review(tmp_path, identity):
    async def scenario():
        spec = get_experiment(identity)
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(80, 24)) as pilot:
            review = await enter_review(app, pilot, identity, selected_values(spec))
            assert review.configuration_error is None
            table = review.query_one("#resolved-settings-table", DataTable)
            assert table.row_count == len(review._review_rows)
            for field in spec.fields:
                candidates = [i for i, row in enumerate(review._review_rows)
                              if row[0] in {"Experiment", "Adaptive"} and row[1] == field.display_label]
                assert len(candidates) == 1, field.key
                detail = table.row_details[candidates[0]]
                assert field.key in detail and field.display_label in detail
                assert "Range" in detail or "Choices" in detail
            for slot, selected in review.request.stimulus_snapshots.items():
                stimulus = get_stimulus(selected["document"]["stimulus_id"])
                for field in stimulus.parameters:
                    i = next(i for i, row in enumerate(review._review_rows)
                             if row[0] == slot and row[1] == field.display_label)
                    detail = table.row_details[i]
                    assert field.key in detail and field.display_label in detail
                    assert "Range" in detail or "Choices" in detail
                    if review._row_authorities[i]["edit_kind"] == "stimulus":
                        assert review._file_targets[i]["kind"] == "stimulus_json", (identity, slot, field.key)
                        path = review._file_targets[i]["path"]
                        assert path is None or path.suffix == ".json"
            assert any(row[0] == "Scientific definitions" for row in review._review_rows)
            assert any(row[0] == "Display profile" and "(metres)" in row[1] for row in review._review_rows)
            assert all(a["edit_kind"] is None for r, a in zip(review._review_rows, review._row_authorities)
                       if r[0] in {"Scientific definitions", "Ellipse geometry", "Stimulus geometry", "Display profile"})
    asyncio.run(scenario())


@pytest.mark.parametrize("size", [(80, 24), (120, 40)])
def test_grouped_rows_keep_full_details_edit_and_source_targets(tmp_path, monkeypatch, size):
    opened = []
    monkeypatch.setattr("psychophysics_lab.ui.editor.open_parameter_file", lambda root, path, *args, **kw: opened.append(path))
    monkeypatch.setattr("psychophysics_lab.ui.setup.open_source", lambda root, path, **kw: opened.append(path))
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=size) as pilot:
            review = await enter_review(app, pilot, "ellipse_centre", selected_values(get_experiment("ellipse_centre")))
            selector = review.query_one("#review-group", Select)
            selector.value = "probe"
            await pilot.pause()
            table = review.query_one("#resolved-settings-table", DataTable)
            assert table.row_count == sum(r[0] == "probe" for r in review._review_rows)
            row = next(i for i, r in enumerate(review._visible_rows)
                       if review._row_authorities[r]["field"] == "length_deg")
            table.move_cursor(row=row)
            table.focus()
            await pilot.press("f2")
            await pilot.pause()
            assert isinstance(app.screen, FullTextScreen)
            text = app.screen.query_one("#full-text-content", TextArea)
            assert text.read_only and text.soft_wrap
            assert 0 < text.region.width <= size[0] and 0 < text.region.height < size[1]
            assert text.text == review._parameter_details(review._visible_row(row))
            assert "length_deg" in text.text and "20" in text.text and "degrees" in text.text
            await pilot.press("escape")
            await pilot.pause()
            review._open_review_file()
            assert opened[-1] == review._file_targets[review._visible_row()]["path"]
            assert opened[-1].is_relative_to(app.local_config_root)
            assert json.loads(opened[-1].read_text())["stimulus_id"] == "probe_line"
            review._edit_review_parameter()
            await pilot.pause()
            editor = app.screen
            assert isinstance(editor, StimulusValueEditor)
            assert editor.focus_key == "length_deg"
            await pilot.press("f2")
            await pilot.pause()
            assert "length_deg" in app.screen.query_one(TextArea).text
            await pilot.press("escape")
            await pilot.pause()
            editor.query_one("#stimulus-values-back", Button).press()
            await pilot.pause()
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            selector.value = "all"
            await pilot.pause()
            assert table.row_count == len(review._review_rows)
    asyncio.run(scenario())


@pytest.mark.parametrize("ratio", [.5, .75, 1.])
def test_ellipse_axes_match_real_rendering_and_width_is_invariant(ratio):
    stimulus = get_stimulus("ellipse_ring")
    parameters = document_for(stimulus)["parameters"] | {
        "outer_radius_deg": .8, "inner_inset_deg": .1, "aspect_ratio": ratio,
        "orientation_deg": 0., "display_contrast": .4}
    axis = np.linspace(-1., 1., 1001)
    x, y = np.meshgrid(axis, axis)
    image = stimulus.render(parameters, x, y)
    mask = image > parameters["background"]
    rows, columns = np.nonzero(mask)
    assert axis[columns].max() - axis[columns].min() == pytest.approx(1.6, abs=.0041)
    assert axis[rows].max() - axis[rows].min() == pytest.approx(1.6*ratio, abs=.0041)
    a, b, inset = .8, .8*ratio, .1
    expected = (((x/a)**2+(y/b)**2 <= 1) & ~((x/(a-inset))**2+(y/(b-inset))**2 < 1))
    np.testing.assert_array_equal(mask, expected)


def test_configure_author_and_experiment_information_have_keyboard_full_text(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(80, 24)) as pilot:
            app.query_one("#participant", Input).value = "FULL_TEXT"
            app.screen.query_one("#configure", Button).press()
            await pilot.pause()
            config = app.screen
            field = config.query_one("#field-max-trials", Input)
            field.focus()
            await pilot.press("f2")
            await pilot.pause()
            assert "max_trials" in app.screen.query_one(TextArea).text
            assert "Current selection" in app.screen.query_one(TextArea).text
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is config and field.has_focus
            app.open_hub_page("experiments")
            await pilot.pause()
            author = app.screen
            expected = str(author.query_one("#experiment-inspection", Static).renderable)
            author.query_one("#inspect-experiment", Select).focus()
            await pilot.press("f2")
            await pilot.pause()
            assert expected and expected in app.screen.query_one(TextArea).text
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is author
    asyncio.run(scenario())


def test_ellipse_tui_edits_feed_render_execution_and_provenance(tmp_path, monkeypatch):
    chosen = {}
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(80, 24)) as pilot:
            values = selected_values(get_experiment("ellipse_centre")) | {"max_trials": 4, "staircases_per_condition": 1}
            review = await enter_review(app, pilot, "ellipse_centre", values)
            for field, value in (("ring_radius_deg", ".8"), ("aspect_ratios", "0.5,1"), ("ellipse_centre_y_deg", ".7")):
                row = next(i for i, a in enumerate(review._row_authorities) if a["field"] == field)
                review._edit_review_parameter(row)
                await pilot.pause()
                app.screen.query_one("#field-"+field.replace("_", "-"), Input).value = value
                app.screen.query_one("#review", Button).press()
                await pilot.pause()
                assert app.screen is review and review.configuration_error is None
            for slot, key, value in (("probe", "length_deg", "1.2"), ("probe", "width_deg", ".04"),
                                     ("ellipse", "inner_inset_deg", ".12")):
                row = next(i for i, a in enumerate(review._row_authorities) if a["field"] == key and a["slot"] == slot)
                review._edit_review_parameter(row)
                await pilot.pause()
                editor = app.screen
                assert isinstance(editor, StimulusValueEditor)
                index = next(i for i, f in enumerate(editor.panel.stimulus.parameters) if f.key == key)
                widget = editor.query_one(f"#stimulus-value-{index}", Input)
                widget.value = "nan"
                editor.query_one("#stimulus-values-apply", Button).press()
                await pilot.pause()
                assert app.screen is editor and "finite" in str(editor.query_one("#stimulus-values-status", Static).renderable)
                widget.value = value
                editor.query_one("#stimulus-values-apply", Button).press()
                await pilot.pause()
                app.screen.query_one("#review", Button).press()
                await pilot.pause()
                assert app.screen is review and review.configuration_error is None
                from psychophysics_lab.config.stimulus_parameters import load_parameters
                path = review._file_sources["stimuli"][slot]
                assert path.is_relative_to(app.local_config_root / "parameter_files" / "ellipse_centre")
                saved = load_parameters(path, get_stimulus(review.request.stimulus_snapshots[slot]["document"]["stimulus_id"]))
                assert saved == review.request.stimulus_snapshots[slot]
            app.verify_settings_current(review.request)
            assert not list(app.local_config_root.glob("stimulus_presets/**/*.json"))
            description = describe_settings(get_experiment("ellipse_centre"), review.request.experiment_values,
                                            review.request.stimulus_snapshots)
            geometry = [r for r in review._review_rows if r[0] == "Ellipse geometry"]
            assert any(r[2] == "1.6" and "Horizontal outer diameter" in r[1] for r in geometry)
            assert {r[2] for r in geometry if "vertical outer diameter" in r[1]} == {"0.8", "1.6"}
            for phase in description["phases"]:
                for placement in phase.get("stimuli", []):
                    if placement["slot"] in {"ellipse", "probe"}:
                        assert placement["x_deg"] == 0 and placement["y_deg"] == .7
            chosen["request"] = review.request
            from psychophysics_lab.ui.presentation_testing import PresentationTestScreen
            review.query_one("#run-presentation-test", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, PresentationTestScreen)
            assert app.screen.request is chosen["request"]
            app.screen.query_one("#presentation-cancel", Button).press()
            await pilot.pause()
            assert app.screen is review
    asyncio.run(scenario())
    request = chosen["request"]
    seen = []
    original = RunContext.trial
    def capture(run, *args, **kwargs):
        seen.append(kwargs["parameters_by_slot"])
        return original(run, *args, **kwargs)
    monkeypatch.setattr(RunContext, "trial", capture)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path / "simulation", experiment_id="ellipse_centre",
                            values=request.experiment_values, stimulus_snapshots=request.stimulus_snapshots, analyse=False)
    assert len(seen) == 4
    assert all(p["probe"]["length_deg"] == 1.2 and p["probe"]["width_deg"] == .04 for p in seen)
    assert all(p["ellipse"]["outer_radius_deg"] == .8 and p["ellipse"]["inner_inset_deg"] == .12 for p in seen)
    axis = np.linspace(-1., 1., 1001)
    x, y = np.meshgrid(axis, axis)
    image = get_stimulus("probe_line").render(seen[0]["probe"], x, y)
    rows, columns = np.nonzero(image > .5)
    assert axis[rows].max()-axis[rows].min() == pytest.approx(1.2, abs=.0041)
    assert axis[columns].max()-axis[columns].min() == pytest.approx(.04, abs=.0041)
    with artifacts.trial_log_file.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream, delimiter="\t"))
    for parameters, record in zip(seen, records):
        assert parameters["probe"]["display_contrast"]*.5 == pytest.approx(float(record["presented_display_contrast"]))
    saved = json.loads((artifacts.run_directory / "experiment_config.json").read_text())
    assert saved["request"]["experiment_values"] == request.experiment_values
    for slot in ("probe", "ellipse"):
        assert saved["request"]["stimulus_snapshots"][slot] == request.stimulus_snapshots[slot]
    journal = (artifacts.run_directory / "trial_events.jsonl").read_text()
    assert '"length_deg": 1.2' in journal and '"inner_inset_deg": 0.12' in journal
