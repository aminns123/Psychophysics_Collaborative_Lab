import asyncio
import json
from pathlib import Path
import pytest
from textual.widgets import Button, Input, Select, Static, TextArea
from psychophysics_lab.experiments.registry import get_experiment, list_experiments
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ReviewScreen, _source_inventory
from psychophysics_lab.ui.stimulus_parameters import JsonPresetEditor, StimulusParametersPanel
from simulations.scenarios.run import run_scenario
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("size", [(80, 24), (120, 40)])
def test_json_preset_edit_reload_review_simulate_and_save(tmp_path, size):
    launch = None
    async def scenario():
        nonlocal launch
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        spec = get_experiment("orientation_task")
        async with app.run_test(size=size) as pilot:
            app.push_screen(ExperimentConfigScreen(data_root=app.data_root, participant_id="student", session_mode="new",
                experiment=spec, monitor_profile_id="legacy_reference_display", defaults=spec.field_defaults()))
            await pilot.pause()
            screen = app.screen
            screen.query_one("#field-trial-count", Input).value = "3"
            screen.query_one("#field-response-keys", Input).value = "LEFT,RIGHT"
            panel = screen.query_one(StimulusParametersPanel)
            panel.query_one("#stimulus-edit-target", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, JsonPresetEditor)
            text = app.screen.query_one("#stimulus-json-editor", TextArea)
            document = json.loads(text.text)
            document["parameters"]["orientation_deg"] = 45.
            text.load_text(json.dumps(document))
            app.screen.query_one("#stimulus-preset-name", Input).value = "tilt45"
            assert await pilot.click("#json-save")
            await pilot.pause()
            assert app.screen is screen
            assert panel.current()["document"]["parameters"]["orientation_deg"] == 45.
            original = panel.path.read_text()
            panel.path.write_text("invalid json")
            with pytest.raises(ValueError, match="Cannot load"):
                screen._collect()
            panel.path.write_text(original)
            panel.query_one("#stimulus-reload-target", Button).press()
            await pilot.pause()
            assert await pilot.click("#review")
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            app.screen.query_one("#run-simulation", Button).press()
            await pilot.pause()
            launch = app.screen._launch_request()
            assert launch.stimulus_snapshots["target"]["document"]["parameters"]["orientation_deg"] == 45.
    asyncio.run(scenario())
    result = run_scenario(experiment_id=launch.experiment_id, scenario_id=launch.scenario_id,
        data_root=launch.data_root, repo_root=ROOT, seeds=launch.seeds, experiment_values=launch.experiment_values,
        observer_parameters=launch.observer_parameters, stimulus_snapshots=launch.stimulus_snapshots)
    assert result.passed
    saved = json.loads((result.runs[0].artifacts.run_directory / "stimulus_parameters.json").read_text())
    assert saved["slots"]["target"]["file_identity"] == "tilt45.json"
    assert all(c.passed for c in validate_run(result.runs[0].artifacts.run_directory))


def test_exact_source_roles_and_editor_fallback(tmp_path, monkeypatch):
    for experiment in list_experiments():
        roles = _source_inventory(ROOT, experiment)
        assert {role for role, _ in roles} >= {"Definition", "Procedure"}
        assert any(role.startswith("Stimulus / renderer") for role, _ in roles)
    roles = dict(_source_inventory(ROOT, get_experiment("orientation_adaptive")))
    assert roles["Definition"].name == "orientation_adaptive.py"
    assert roles["Procedure"] == roles["Definition"]
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("No editor installed")
    monkeypatch.setattr("psychophysics_lab.ui.setup.open_source", unavailable)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test() as pilot:
            app.inspect_source(roles["Procedure"])
            await pilot.pause()
            viewer = app.screen.query_one(TextArea)
            assert viewer.read_only and "def procedure(run)" in viewer.text
    asyncio.run(scenario())
