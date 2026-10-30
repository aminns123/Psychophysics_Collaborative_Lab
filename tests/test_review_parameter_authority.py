"""First-time researcher: Review explains the real input and opens its editor."""
import asyncio
import json
from dataclasses import replace
from pathlib import Path
import pytest
from textual.widgets import Button, DataTable, Input, Select, Static

from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen, ExperimentConfigScreen, ExperimentParametersScreen
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
from psychophysics_lab.ui.stimulus_editor import StimulusValueEditor
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.config.stimulus_parameters import document_for
from psychophysics_lab.stimuli.registry import get_stimulus

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("identity,slot",[("orientation_task","target"),("contrast_sensitivity_windowed","grating")])
def test_adopt_refreshed_defaults_replaces_retained_snapshot_without_overwriting_experiment(tmp_path,monkeypatch,identity,slot):
    from psychophysics_lab.stimuli import registry
    from psychophysics_lab.config.stimulus_parameters import snapshot
    experiment=get_experiment(identity)
    original=get_stimulus(experiment.stimulus_defaults[slot])
    old=next(f.default for f in original.parameters if f.key=="size_deg")
    updated=replace(original,parameters=tuple(replace(f,default=old*1.2) if f.key=="size_deg" else f for f in original.parameters))
    monkeypatch.setitem(registry._REGISTRY,original.id,updated)
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(120,45)) as pilot:
            config,review=await enter_review(app,pilot,identity,
                {"aperture_diameter_deg":1.,"fade_width_deg":.1} if identity.endswith("windowed") else {})
            review.query_one("#back",Button).press()
            await pilot.pause()
            config.query_one('#review', Button).press()
            await pilot.pause()
            app.screen.query_one('#review-edit-inputs', Button).press()
            await pilot.pause()
            config = app.screen
            panel=next(p for p in config.query(StimulusParametersPanel) if p.slot==slot)
            if updated.default_config:
                panel.query_one("#stimulus-preset-"+slot,Select).value="library_defaults"
                await pilot.pause()
                assert panel.current()["file_identity"]=="library_defaults"
                assert panel.current()["document"]["parameters"]["size_deg"]==old*1.2
            retained=document_for(updated)
            retained["parameters"]["size_deg"]=old
            panel.loaded=snapshot(retained,file_identity="library_defaults")
            panel.path=None
            app.stimulus_drafts[panel.cache_key]=(panel.loaded,None)
            panel.refresh_presets()
            assert panel.query_one("#stimulus-preset-"+slot,Select).value=="library_defaults"
            before=config._collect()
            panel.query_one("#stimulus-defaults-"+slot,Button).press()
            await pilot.pause()
            assert panel.current()["document"]["parameters"]["size_deg"]==old*1.2
            assert config._collect()==before
            config.query_one("#review",Button).press()
            await pilot.pause()
            review=app.screen
            row=next(i for i,r in enumerate(review._review_rows) if r[0]==slot
                     and r[1]==next(f.display_label for f in updated.parameters if f.key=="size_deg"))
            expected=1. if identity.endswith("windowed") else old*1.2
            assert float(review._review_rows[row][2])==expected
    asyncio.run(scenario())


@pytest.mark.parametrize("size", [(80,24),(120,40)])
@pytest.mark.parametrize("entry", ["2,4","2,nan"])
@pytest.mark.parametrize("identity", ["contrast_sensitivity", "contrast_sensitivity_windowed"])
def test_sidebar_review_applies_or_rejects_current_draft_instead_of_discarding_it(tmp_path,size,entry,identity):
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=size) as pilot:
            _,review=await enter_review(app,pilot,identity)
            review.query_one("#review-show-response-instructions").value=False
            await pilot.pause()
            assert review.request.show_response_instructions is False
            row=next(i for i,a in enumerate(review._row_authorities) if a["field"]=="frequencies_cpd")
            review._edit_review_parameter(row)
            await pilot.pause()
            config=app.screen
            field=config.query_one("#field-frequencies-cpd",Input)
            field.value=entry
            # Same keyboard route used in the real Windows entry-point audit.
            await pilot.press("f6","tab","tab","enter")
            await pilot.pause()
            if "nan" in entry:
                assert app.screen is config
                assert field.value==entry
                assert "2,8"==review.request.experiment_values["frequencies_cpd"]
                message = str(config.query_one("#config-status",Static).renderable)
                assert "0.5-32 cycles/degree" in message
                assert message.isascii()
                field.value="2,4"
                config.query_one("#path-review",Button).press()
                await pilot.pause()
            assert app.screen is review
            assert review.request.experiment_values["frequencies_cpd"]=="2,4"
            assert review.request.show_response_instructions is False
    asyncio.run(scenario())


async def enter_review(app, pilot, identity, changes=None):
    app.query_one("#participant", Input).value = "REVIEW_NOVICE"
    app.query_one("#experiment", Select).value = identity
    await pilot.pause()
    app.screen.query_one("#configure", Button).press()
    await pilot.pause()
    config = app.screen
    for key, value in (changes or {}).items():
        config.defaults[key] = value
        app.config_drafts.setdefault(config.draft_key, {})[key] = value
    config.query_one("#review", Button).press()
    await pilot.pause()
    assert isinstance(app.screen, ReviewScreen)
    return config, app.screen


@pytest.mark.parametrize("identity,key,new_value,slot,parameter", [
    ("contrast_sensitivity_windowed", "aperture_diameter_deg", 1., "grating", "size_deg"),
    ("contrast_sensitivity", "grating_sigma_deg", .3, "grating", "sigma_deg"),
])
@pytest.mark.parametrize("size", [(80,24), (160,55)])
def test_edit_controlling_input_from_resolved_row_and_reload_saved_json(tmp_path, monkeypatch, identity, key, new_value, slot, parameter, size):
    monkeypatch.setattr("psychophysics_lab.ui.editor.open_parameter_file", lambda *a, **k: None)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=size) as pilot:
            _, review = await enter_review(app, pilot, identity)
            table = review.query_one("#resolved-settings-table", DataTable)
            label = next(f.display_label for f in get_stimulus(review.request.stimulus_snapshots[slot]["document"]["stimulus_id"]).parameters if f.key == parameter)
            row = next(i for i in range(table.row_count) if str(table.get_row_at(i)[0]) == slot and str(table.get_row_at(i)[1]) == label)
            table.move_cursor(row=row)
            await pilot.pause()
            assert str(table.get_row_at(row)[3]) == "Experiment-controlled"
            detail = str(review.query_one("#review-file-location", Static).renderable)
            assert key in detail and "WHERE TO CHANGE: Review" in detail
            button=review.query_one("#review-edit-value", Button)
            button.focus()
            button.scroll_visible(immediate=True,top=True,force=True)
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            app.save_screenshot(filename="review-before-edit.svg",path=tmp_path)
            clicked=await pilot.click("#review-edit-value",offset=(3,1))
            await pilot.pause()
            assert isinstance(app.screen, ExperimentParametersScreen), (clicked,button.region,type(app.screen).__name__)
            widget = app.screen.query_one("#field-" + key.replace("_", "-"), Input)
            assert widget.has_focus
            widget.value = str(new_value)
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            assert app.screen is review and review.request.experiment_values[key] == new_value
            assert float(table.get_row_at(row)[2]) == new_value
            # Advanced export/reload remains available without becoming the normal edit path.
            review._open_review_file(row)
            path = review._file_sources["experiment"]
            assert path is not None and path.is_relative_to(app.local_config_root)
            document = json.loads(path.read_text(encoding="utf-8"))
            document["values"][key] = new_value * 1.2
            path.write_text(json.dumps(document), encoding="utf-8")
            review.query_one("#review-reload-files", Button).press()
            await pilot.pause()
            assert review.request.experiment_values[key] == new_value * 1.2
            assert float(table.get_row_at(row)[2]) == new_value * 1.2
            # A selected experiment input stays authoritative over renderer defaults/presets.
            assert review._row_authorities[row]["field"] == key
            assert "Experiment-controlled" == review._row_authorities[row]["status"]
            app.save_screenshot(filename=f"review-{identity}-{size[0]}.svg", path=tmp_path)
    asyncio.run(scenario())


@pytest.mark.parametrize("identity,changes,slot,key", [
    ("line_position_baseline", {"probe_vertical_offset_deg": .4}, "first", "probe_length_deg"),
    ("orientation_task", {}, "target", "size_deg"),
    ("example_experiment", {}, "target", "line_length_deg"),
])
def test_stimulus_base_values_open_tui_editor_instead_of_requiring_python(tmp_path, identity, changes, slot, key):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(130,50)) as pilot:
            _, review = await enter_review(app, pilot, identity, changes)
            label = next(f.display_label for f in get_stimulus(review.request.stimulus_snapshots[slot]["document"]["stimulus_id"]).parameters if f.key == key)
            table = review.query_one("#resolved-settings-table", DataTable)
            row = next(i for i in range(table.row_count) if str(table.get_row_at(i)[0]) == slot and str(table.get_row_at(i)[1]) == label)
            table.move_cursor(row=row)
            review.query_one("#review-edit-value", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, StimulusValueEditor)
            editor = app.screen
            index = next(i for i,f in enumerate(editor.panel.stimulus.parameters) if f.key == key)
            widget = editor.query_one(f"#stimulus-value-{index}", Input)
            assert widget.has_focus and not widget.disabled
            new_value = float(widget.value) * 1.2
            widget.value = str(new_value)
            editor.query_one("#stimulus-value-name", Input).value = "novice selection"
            editor.query_one("#stimulus-values-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ExperimentParametersScreen)
            app.screen.query_one("#review", Button).press()
            await pilot.pause()
            assert app.screen is review
            assert review.request.stimulus_snapshots[slot]["document"]["parameters"][key] == new_value
            assert float(table.get_row_at(row)[2]) == new_value
    asyncio.run(scenario())


def test_conflicting_current_python_default_preset_and_experiment_control(tmp_path, monkeypatch):
    from psychophysics_lab.stimuli import registry
    from psychophysics_lab.ui.settings_review import describe_settings, review_rows
    from psychophysics_lab.ui.review_files import targets_for_rows
    from psychophysics_lab.ui.review_authority import authority_for_row
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli, snapshot
    spec = get_experiment("contrast_sensitivity_windowed")
    values = spec.normalise_values({"aperture_diameter_deg":1., "fade_width_deg":.1})
    original = get_stimulus("circular_windowed_sinusoidal_grating")
    refreshed = replace(original, parameters=tuple(replace(f,default=5.) if f.key == "size_deg" else f for f in original.parameters))
    monkeypatch.setitem(registry._REGISTRY, original.id, refreshed)
    selected = resolve_stimuli(spec, values, repo_root=ROOT)
    selected["grating"] = snapshot(document_for(refreshed, selected["grating"]["document"]["parameters"] | {"size_deg":7.}), file_identity="saved_stimulus.json")
    description = describe_settings(spec, values, selected)
    assert description["stimuli"]["grating"]["size_deg"] == 1.
    rows = review_rows(spec,values,selected,description)
    sources = {"experiment":None,"stimuli":{}}
    targets = targets_for_rows(spec,selected,description,rows,sources,ROOT)
    label = next(f.display_label for f in refreshed.parameters if f.key == "size_deg")
    row = next(i for i,r in enumerate(rows) if r[0]=="grating" and r[1] == label)
    authority = authority_for_row(spec,values,selected,description,rows[row],targets[row],sources)
    assert authority["field"] == "aperture_diameter_deg"
    assert targets[row]["key"] == "aperture_diameter_deg"
    assert "overrid" in rows[row][3] and "not an independent" in authority["explanation"]
