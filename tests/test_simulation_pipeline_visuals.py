"""Current virtual-observer settings and run-figure parity without obsolete scenarios."""
from __future__ import annotations
import asyncio
import csv
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Static, Collapsible, Select

from simulations.registry import get_simulation
from simulations.run import simulate
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.analysis.thresholds import analyse_thresholds
from psychophysics_lab.analysis.previews import (
    create_staircase_preview, latest_staircase_plot, latest_threshold_plot
)
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, DataScreen
from psychophysics_lab.ui.simulations import SimulationsScreen
from psychophysics_lab.ui import plots as image_viewer

ROOT=Path(__file__).resolve().parents[1]


def test_all_human_fields_and_virtual_only_observer_controls_exposed():
    spec=get_experiment("contrast_sensitivity")
    virtual=get_simulation(spec.id)
    assert set(virtual.defaults)=={f.key for f in spec.fields}
    assert {"n_down","n_up","logUNIT_UP","logUNIT_DW","frequencies_cpd"} <= set(virtual.defaults)
    assert "threshold" not in spec.field_defaults()
    observer=virtual.observer_factory()
    assert observer.simulation_parameters() if hasattr(observer,"simulation_parameters") else True


def test_current_simulated_run_saves_selected_adaptive_parameters(tmp_path):
    data=tmp_path/"data"
    artifacts,_=simulate(data_root=data,repo_root=ROOT,seed=441,analyse=False,
        values={"n_down":3,"n_up":1,"logUNIT_UP":.2,"logUNIT_DW":.15,
                "reversal_termination":7,"threshold_reversals":3,
                "max_trials":8,"frequencies_cpd":"1.5",
                "starting_contrast":.04})
    run=artifacts.run_directory
    manifest=json.loads((run/"manifest.json").read_text())
    config=json.loads((run/"experiment_config.json").read_text())
    assert manifest["data_kind"]=="synthetic"
    actual=config["normalised_experiment_values"]
    assert actual["n_down"]==3 and actual["n_up"]==1
    assert actual["logUNIT_UP"]==.2
    assert actual["logUNIT_DW"]==.15
    assert actual["starting_contrast"]==.04
    assert actual["frequencies_cpd"]=="1.5"
    assert (run/"analysis/staircases.png").is_file()


def test_raw_trials_remain_unchanged_by_exploratory_analysis(tmp_path):
    data=tmp_path/"data"
    case,_=simulate(data_root=data,repo_root=ROOT,seed=123,
        values={"max_trials":120,"frequencies_cpd":"2","staircases_per_condition":1},
        analyse=False)
    run=case.run_directory
    initial=(run/"trials.tsv").read_bytes()
    preview=create_staircase_preview(data_root=data,run_directory=run)
    assert preview.plot_file and preview.plot_file.is_file()
    assert latest_staircase_plot(data_root=data,run_directory=run).is_file()
    for retained in (1,2):
        try:
            result=analyse_thresholds(data_root=data,run_directory=run,
                last_n_reversals=retained,create_plot=True,exploratory=True)
        except ValueError as exc:
            assert "reversal" in str(exc).lower()
        else:
            assert result.output_directory.is_relative_to(run/"analysis/thresholds")
    assert (run/"trials.tsv").read_bytes()==initial
    with pytest.raises(ValueError):
        analyse_thresholds(data_root=data,run_directory=run,last_n_reversals=0,exploratory=True)


def test_simulation_tui_exposes_selected_public_csf_adaptive_fields(tmp_path):
    async def scenario():
        # Modern default navigation intentionally routes simulations through
        # Experiment -> Configure -> Review. The standalone advanced legacy
        # SimulationsScreen is available only when explicitly opted in.
        app=PsyCoLabSetupApp(include_historical=True,repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one("#nav-simulations",Button).press()
            await pilot.pause(.2)
            for _ in range(20):
                if isinstance(app.screen,SimulationsScreen):
                    break
                await pilot.pause(.1)
            screen=app.screen
            assert isinstance(screen,SimulationsScreen)
            screen.query_one("#sim-experiment",Select).value="contrast_sensitivity"
            await pilot.pause()
            index,selected=screen._current()
            fields=list(get_experiment(selected.experiment_id).fields)
            controls={f.key:i for i,f in enumerate(fields)}
            for key in ("n_down","n_up","logUNIT_UP","logUNIT_DW"):
                widget=screen.query_one(f"#sim-experiment-value-{index}-{controls[key]}",Input)
                assert not widget.disabled
            screen.query_one(f"#sim-experiment-value-{index}-{controls['n_down']}",Input).value="3"
            assert screen._request().experiment_values["n_down"]==3
            screen.query_one(f"#sim-experiment-value-{index}-{controls['n_down']}",Input).value="0"
            with pytest.raises(ValueError):
                screen._request()
    asyncio.run(scenario())


def test_data_browser_opens_actual_derived_staircase_png_safely(tmp_path,monkeypatch):
    data=tmp_path/"data"
    case,_=simulate(data_root=data,repo_root=ROOT,seed=27,
        values={"max_trials":8,"frequencies_cpd":"2"},analyse=False)
    opened=[]
    real_open=image_viewer.open_analysis_png
    monkeypatch.setattr(image_viewer,"open_analysis_png",
                        lambda data_root,image_path:opened.append(Path(image_path)))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=data)
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one("#nav-data",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,DataScreen)
            app.screen.query_one("#open-staircase-image",Button).press()
            await pilot.pause()
            assert opened and opened[0].is_file()
    asyncio.run(scenario())
    with pytest.raises(ValueError,match="PNG"):
        real_open(data,case.trial_log_file)
