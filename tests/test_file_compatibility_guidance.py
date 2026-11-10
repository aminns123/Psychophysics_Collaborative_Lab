"""Recover standalone researcher files through the existing Review workflow."""

import asyncio
from copy import deepcopy
import json

import pytest
from textual.widgets import Button, Checkbox, DataTable, Input, Select, Static

from psychophysics_lab import extensions
from psychophysics_lab.config.sharing import make_document, read_document
from psychophysics_lab.development import execute_user_action
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.setup import ExperimentParametersScreen, PsyCoLabSetupApp, ReviewScreen
from test_configuration_sharing import ROOT, request_for
from test_laboratory_extensions import EXPERIMENT, STIMULUS, enable, lab
from test_parameter_accessibility import enter_review, selected_values


def component(document, request, profile, *, slot=None):
    from psychophysics_lab.configuration_recovery import prepare_component_recovery

    return prepare_component_recovery(document, json.dumps(document).encode(), ROOT, request, profile,
                                      slot=slot, verify_sources=lambda *_: None)


async def open_draft(app, pilot, review, path):
    review.query_one("#review-import-configuration", Button).press()
    await pilot.pause()
    importer = app.screen
    importer.query_one("#configuration-path", Input).value = str(path)
    importer.query_one("#configuration-preview", Button).press()
    await pilot.pause()
    assert importer.query_one("#configuration-approve", Button).disabled
    assert not importer.query_one("#configuration-recover", Button).disabled
    importer.query_one("#configuration-recover", Button).press()
    await pilot.pause()
    return app.screen


async def accept_reviewed(app, pilot, draft):
    draft.query_one("#recovery-accept-compatible", Button).press()
    await pilot.pause()
    app.screen.query_one("#recovery-confirm-checked", Button).press()
    await pilot.pause()


async def replace_field(app, pilot, draft, key, value):
    table = draft.query_one("#recovery-settings", DataTable)
    table.move_cursor(row=next(i for i, row in enumerate(draft.draft.review_rows) if row.field.key == key))
    table.focus()
    await pilot.press("enter")
    await pilot.pause()
    app.screen.query_one("#recovery-value", Input).value = value
    app.screen.query_one("#recovery-replace", Button).press()
    await pilot.pause()


def test_incomplete_preset_guides_to_review_without_filling_defaults(tmp_path):
    async def scenario():
        identity = "ellipse_centre"
        spec = get_experiment(identity)
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"runs")
        values = selected_values(spec)
        source = app.local_config_root/"presets"/identity/"historical.json"
        source.parent.mkdir(parents=True)
        historical = values | {"background_intensity": .27}
        del historical["stimulus_ms"]
        raw = json.dumps({"experiment_id": identity, "values": historical}).encode()
        source.write_bytes(raw)
        async with app.run_test(size=(90, 26)) as pilot:
            app.push_screen(ExperimentParametersScreen(
                data_root=tmp_path/"runs", participant_id="RECOVERY", session_mode="new",
                experiment=spec, monitor_profile_id="legacy_reference_display", defaults=values))
            await pilot.pause()
            config = app.screen
            config.query_one("#config-preset", Select).value = "historical"
            config.query_one("#load-preset", Button).press()
            await pilot.pause()
            status = str(config.query_one("#config-status", Static).render())
            assert "Missing settings: stimulus_ms" in status
            assert "Recover settings as draft" in status
            assert config.query_one("#field-background-intensity", Input).value == str(values["background_intensity"])
            assert source.read_bytes() == raw
            app.pop_screen()
            await pilot.pause()

            review = await enter_review(app, pilot, identity, values)
            previous = review.request
            draft = await open_draft(app, pilot, review, source)
            assert len(draft.draft.review_rows) == len(spec.fields)
            await accept_reviewed(app, pilot, draft)
            assert draft.draft.unresolved == 1 and draft.query_one("#recovery-save", Button).disabled
            await replace_field(app, pilot, draft, "stimulus_ms", "220")
            draft.query_one("#recovery-reviewed", Checkbox).value = True
            await pilot.pause()
            draft.query_one("#recovery-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen) and app.screen is not review
            recovered = app.screen.request
            assert recovered.experiment_values["stimulus_ms"] == 220
            assert recovered.experiment_values["background_intensity"] == .27
            assert recovered.stimulus_snapshots["ready_fixation"]["document"]["parameters"]["background"] == .27
            assert recovered.stimulus_snapshots["probe"]["document"] == previous.stimulus_snapshots["probe"]["document"]
            saved, = app.local_config_root.glob("parameter_files/**/configuration.json")
            assert (saved.parent/"recovery"/"original.json").read_bytes() == source.read_bytes() == raw
            report = read_document(saved.parent/"recovery"/"decisions.json")
            assert report["original_kind"] == "experiment settings" and report["original_schema"] is None
            assert any(decision["action"] == "resolve experiment binding"
                       for row in report["parameters"] for decision in row["decisions"])
    asyncio.run(scenario())


def test_standalone_stimulus_recovers_only_selected_slot(tmp_path):
    async def scenario():
        identity = "ellipse_centre"
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"runs")
        async with app.run_test(size=(80, 24)) as pilot:
            review = await enter_review(app, pilot, identity, selected_values(get_experiment(identity)))
            previous = review.request
            source = tmp_path/"old probe.json"
            document = deepcopy(previous.stimulus_snapshots["probe"]["document"])
            document["parameters"]["old_width_arcmin"] = 1.2
            del document["parameters"]["width_deg"]
            document["parameter_info"] = {"length_deg": {"units": "arcmin"}}
            raw = json.dumps(document).encode()
            source.write_bytes(raw)
            draft = await open_draft(app, pilot, review, source)
            assert {row.path[1] for row in draft.draft.review_rows} == {"probe"}
            assert {row.field.key: row.status for row in draft.draft.review_rows}["length_deg"] == "Different units"
            await accept_reviewed(app, pilot, draft)
            assert draft.draft.unresolved == 2
            await replace_field(app, pilot, draft, "length_deg", "1.0")
            await replace_field(app, pilot, draft, "width_deg", "0.02")
            draft.query_one("#recovery-reviewed", Checkbox).value = True
            await pilot.pause()
            draft.query_one("#recovery-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen) and app.screen is not review
            assert app.screen.request.experiment_values == previous.experiment_values
            probe = app.screen.request.stimulus_snapshots["probe"]["document"]["parameters"]
            assert probe["length_deg"] == 1 and probe["width_deg"] == .02
            assert app.screen.request.stimulus_snapshots["ellipse"]["document"] == previous.stimulus_snapshots["ellipse"]["document"]
            saved, = app.local_config_root.glob("parameter_files/**/configuration.json")
            assert (saved.parent/"recovery"/"original.json").read_bytes() == source.read_bytes() == raw
            report = read_document(saved.parent/"recovery"/"decisions.json")
            assert any(item["path"][-1] == "old_width_arcmin" and item["value"] == 1.2 for item in report["unmapped"])
    asyncio.run(scenario())


def test_shared_stimulus_requires_slot_and_cannot_replace_experiment_binding():
    request, profile = request_for("contrast_sensitivity")
    document = deepcopy(request.stimulus_snapshots["ready_fixation"]["document"])
    document["parameters"]["background"] = .55
    with pytest.raises(ValueError, match="more than one slot"):
        component(document, request, profile)
    draft = component(document, request, profile, slot="ready_fixation")
    background = next(row for row in draft.review_rows if row.field.key == "background")
    assert background.locked and background.status == "Experiment-controlled"
    assert background.value == request.experiment_values["background_intensity"]
    assert draft.unmapped[background.path] == .55
    with pytest.raises(ValueError, match="Controlled by experiment input"):
        background.decide("replace", ".55")


def test_old_contrast_convention_is_not_inferred_from_an_unverified_local_file():
    request, profile = request_for()
    document = make_document(ROOT, request, profile)["experiment"]
    del document["values"]["starting_probe_intensity"]
    document["values"]["starting_contrast"] = .13
    draft = component(document, request, profile)
    target = next(row for row in draft.review_rows if row.field.key == "starting_probe_intensity")
    assert target.status == "Missing" and target.suggestion is None and not target.resolved
    assert draft.unmapped[("experiment", "values", "starting_contrast")] == .13


@pytest.mark.parametrize("data, message", [
    ({"schema_version": 77, "stimulus_id": "probe_line", "parameters": {}}, "Local stimulus schema"),
    ({"schema_version": 1, "stimulus_id": "lab__missing", "parameters": {}}, "Install and verify"),
    ({"schema_version": 1, "experiment_id": "lab__other", "values": {}}, "Open Review for that experiment"),
])
def test_local_unknown_schema_or_dependency_fails_closed(data, message):
    request, profile = request_for()
    with pytest.raises(ValueError, match=message):
        component(data, request, profile)


def test_changed_lab_template_requires_explicit_new_field(lab, tmp_path):
    source = lab/"experiments"/(EXPERIMENT + ".py")
    updated = source.read_text(encoding="utf-8").replace(
        "FIELDS = (", 'FIELDS = (\n    ConfigField("new_lab_margin_deg", "Lab margin", "float", '
        '0.15, units="degrees", minimum=0.0, maximum=1.0),', 1)
    source.write_text(updated, encoding="utf-8")
    enable(lab)
    assert execute_user_action(ROOT, "preview", STIMULUS, {}) == 0
    extensions.publish(ROOT, "stimulus", STIMULUS)
    assert execute_user_action(ROOT, "test", EXPERIMENT, {"trial_count": 4}) == 0
    extensions.publish(ROOT, "experiment", EXPERIMENT)
    request, profile = request_for(EXPERIMENT)
    document = make_document(ROOT, request, profile)["experiment"]
    del document["values"]["new_lab_margin_deg"]
    draft = component(document, request, profile)
    margin = next(row for row in draft.review_rows if row.field.key == "new_lab_margin_deg")
    assert margin.status == "Missing" and not margin.resolved
    for row in draft.review_rows:
        if row is margin:
            row.decide("replace", ".25")
        else:
            row.decide("accept")
    saved, _, _ = draft.save(tmp_path/"config", ROOT, request, profile, reviewed=True,
                              verify_sources=lambda spec, snapshots: extensions.check_run(ROOT, spec, snapshots))
    assert saved.experiment_values["new_lab_margin_deg"] == .25
    assert extensions.status(ROOT, "experiment", EXPERIMENT) == "ready"
