"""Both setup modes expose the same CSF conditions and initial staircase controls."""
import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Collapsible

from simulations.controls import effective_experiment_values
from simulations.scenarios import get_scenario
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.setup import (
    ExperimentConfigScreen, PsyCoLabSetupApp
)
from psychophysics_lab.ui.simulations import (
    SimulationsScreen, AdaptiveAlgorithmScreen,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("screen_size", [(80, 24), (100, 30)])
def test_simulation_tui_exposes_ordered_conditions_and_introductory_rule(tmp_path, screen_size):
    async def test():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "psy_data")
        async with app.run_test(size=screen_size) as pilot:
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SimulationsScreen)
            index, scenario = screen._current()
            fields = {field.key: i for i, field in enumerate(get_experiment(scenario.experiment_id).fields)}
            conditions_panel = screen.query_one(f"#sim-conditions-{index}", Collapsible)
            assert not conditions_panel.collapsed
            def value(key):
                return screen.query_one(f"#sim-experiment-value-{index}-{fields[key]}", Input)

            assert value("number_conditions").value == "2"
            assert value("condition_values").value == "63,252"
            value("number_conditions").value = "3"
            value("condition_values").value = "252,63,126"
            value("staircases_per_condition").value = "2"
            value("initial_one_down_limit").value = "6"
            request = screen._request()
            assert request.experiment_values["number_conditions"] == 3
            assert request.experiment_values["condition_values"] == "252,63,126"
            assert request.experiment_values["staircases_per_condition"] == 2
            assert request.experiment_values["initial_one_down_limit"] == 6

            # The same early phase must be visible in Adaptive algorithm editor.
            screen.query_one("#sim-edit-adaptive", Button).press()
            await pilot.pause()
            editor = app.screen
            assert isinstance(editor, AdaptiveAlgorithmScreen)
            number = fields["initial_one_down_limit"]
            assert editor.query_one(f"#adaptive-value-{number}", Input).value == "6"
            editor.query_one("#adaptive-cancel", Button).press()
            await pilot.pause()
            assert app.screen is screen

            value("number_conditions").value = "2"
            with pytest.raises(ValueError, match="Number of conditions"):
                screen._request()
    asyncio.run(test())


def test_human_config_same_fields_and_validates_conditions(tmp_path):
    from simulations.csf import DEFAULT_VALUES
    experiment = get_experiment("legacy_contrast_sensitivity")
    defaults = experiment.normalise_values(dict(DEFAULT_VALUES))

    async def test():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "psy_data")
        async with app.run_test(size=(100, 30)) as pilot:
            app.push_screen(
                ExperimentConfigScreen(
                    data_root=tmp_path / "psy_data", participant_id="H001",
                    session_mode="new", experiment=experiment,
                    monitor_profile_id="legacy_reference_display", defaults=defaults,
                )
            )
            await pilot.pause()
            screen = app.screen
            conditions = next(group for group in screen.query(Collapsible)
                              if group.title == "Stimulus conditions")
            assert not conditions.collapsed
            screen.query_one("#field-number-conditions", Input).value = "3"
            screen.query_one("#field-condition-values", Input).value = "63,126,252"
            screen.query_one("#field-initial-one-down-limit", Input).value = "4"
            screen.query_one("#field-staircases-per-condition", Input).value = "2"
            collected = screen._collect()
            assert collected["number_conditions"] == 3
            assert collected["condition_values"] == "63,126,252"
            assert collected["initial_one_down_limit"] == 4
            assert collected["staircases_per_condition"] == 2
            screen.query_one("#field-number-conditions", Input).value = "2"
            with pytest.raises(ValueError, match="Number of conditions"):
                screen._collect()
    asyncio.run(test())
