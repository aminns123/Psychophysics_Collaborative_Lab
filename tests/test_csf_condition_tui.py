"""Current CSF condition and adaptation controls in researcher configuration."""
import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, Input

from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.setup import ExperimentConfigScreen, PsyCoLabSetupApp
from psychophysics_lab.experiments.contrast_sensitivity import make_conditions
from simulations.registry import get_simulation

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("size",[(80,24),(100,30)])
def test_csf_config_exposes_selected_cpd_repetitions_and_initial_rule(tmp_path,size):
    experiment=get_experiment("contrast_sensitivity")
    defaults=experiment.field_defaults()
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"psy_data")
        async with app.run_test(size=size) as pilot:
            screen=ExperimentConfigScreen(
                data_root=tmp_path/"psy_data",participant_id="H001",
                session_mode="new",experiment=experiment,
                monitor_profile_id="legacy_reference_display",defaults=defaults
            )
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one("#field-frequencies-cpd",Input).value="1.5,3,7"
            screen.query_one("#field-staircases-per-condition",Input).value="2"
            screen.query_one("#field-initial-one-down-limit",Input).value="5"
            effective=screen._collect()
            assert effective["frequencies_cpd"]=="1.5,3,7"
            assert effective["staircases_per_condition"]==2
            assert effective["initial_one_down_limit"]==5
            assert len(make_conditions(effective))==6
            screen.query_one("#field-frequencies-cpd",Input).value="2,not_a_frequency"
            with pytest.raises(ValueError):
                screen._collect()
    asyncio.run(scenario())


def test_simulation_defaults_are_derived_from_same_public_experiment():
    experiment=get_experiment("contrast_sensitivity")
    simulation=get_simulation("contrast_sensitivity")
    for field in experiment.fields:
        assert field.key in simulation.defaults
        assert simulation.defaults[field.key]==field.default
    assert experiment.adaptive.algorithm_id=="consecutive_up_down"
