"""Real-pipeline parity: editable experiment settings, synthetic records and plots."""
from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Static, Collapsible

from simulations.controls import effective_experiment_values, effective_observer_values
from simulations.scenarios import get_scenario, run_scenario
from simulations.run import simulate
from psychophysics_lab.experiments.registry import get_experiment
from psychophysics_lab.analysis.thresholds import analyse_thresholds
from psychophysics_lab.analysis.previews import (
    create_staircase_preview, latest_staircase_plot, latest_threshold_plot,
)
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, DataScreen
from psychophysics_lab.ui.simulations import SimulationsScreen
from psychophysics_lab.ui import plots as image_viewer

ROOT = Path(__file__).resolve().parents[1]


def test_all_human_fields_and_virtual_only_observer_controls_exposed():
    scenario = get_scenario("contrast_sensitivity", "csf_short_censored")
    spec = get_experiment("contrast_sensitivity")
    experiment_values = effective_experiment_values(scenario)
    assert set(experiment_values) == {f.key for f in spec.fields}
    assert experiment_values["n_down"] == 2
    assert experiment_values["n_up"] == 1
    assert experiment_values["logUNIT_UP"] == .35
    assert experiment_values["logUNIT_DW"] == pytest.approx(.5488*.35)
    assert experiment_values["max_trials"] == 1
    observer = effective_observer_values(scenario)
    assert {"threshold", "preferred_condition", "tuning_width_octaves", "slope", "lapse"} <= set(observer)
    assert "lapse" not in experiment_values


def test_complete_run_records_human_equivalent_adaptive_overrides(tmp_path):
    root = tmp_path / "local_psychophysics_data"
    result = run_scenario(
        experiment_id="contrast_sensitivity", scenario_id="csf_short_censored",
        data_root=root, repo_root=ROOT, seeds=(441,),
        observer_parameters={"slope": 4.0, "threshold": .07},
        experiment_values={
            "n_down": 3, "n_up": 1, "logUNIT_UP": .20,
            "logUNIT_DW": .7393*.20, "reversal_termination": 7,
            "max_trials": 1, "timeAB": 175, "starting_probe_intensity": .8,
        },
        monitor_profile_id="legacy_reference_display",
    )
    assert result.passed
    run = result.runs[0].artifacts.run_directory
    manifest = json.loads((run / "manifest.json").read_text())
    with (run / "trials.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 1
    assert manifest["data_kind"] == "synthetic"
    assert manifest["simulation"]["observer_parameters"]["slope"] == 4.0
    configuration = json.loads((run / "experiment_config.json").read_text())
    actual = configuration["normalised_experiment_values"]
    assert actual["n_down"] == 3
    assert actual["n_up"] == 1
    assert actual["logUNIT_UP"] == .20
    assert actual["logUNIT_DW"] == pytest.approx(.7393*.20)
    assert actual["timeAB"] == 175
    assert actual["starting_probe_intensity"] == .8
    assert manifest["monitor_profile_id"] == "legacy_reference_display"
    assert result.report_file.is_file()
    report = json.loads(result.report_file.read_text())
    single = report["runs"][0]
    assert (root / single["canonical_trials"]).read_bytes() == (run / "trials.tsv").read_bytes()
    assert (root / single["staircase_plot"]).is_file()
    assert single["threshold_plot"] is None  # Insufficient reversals: do not invent THC.


def test_canonical_trials_unchanged_after_exploratory_n_reversal_analysis(tmp_path):
    root = tmp_path / "local_psychophysics_data"
    artifacts, _ = simulate(
        data_root=root, repo_root=ROOT, seed=123, values={"max_trials": 140}
    )
    run = artifacts.run_directory
    initial = (run / "trials.tsv").read_bytes()
    preview = create_staircase_preview(data_root=root, run_directory=run)
    assert preview.plot_file and preview.plot_file.is_file()
    assert latest_staircase_plot(data_root=root, run_directory=run).is_file()
    one = analyse_thresholds(data_root=root, run_directory=run,
                             last_n_reversals=1, create_plot=True)
    two = analyse_thresholds(data_root=root, run_directory=run,
                             last_n_reversals=2, create_plot=True)
    assert all(row.retained_count == 1 for row in one.staircase_thresholds)
    assert all(row.retained_count in (1, 2) for row in two.staircase_thresholds)
    assert latest_threshold_plot(data_root=root, run_directory=run).is_file()
    assert one.plot_file.is_file()
    assert json.loads(one.summary_json.read_text())["last_n_reversals"] == 1
    assert (run / "trials.tsv").read_bytes() == initial
    with pytest.raises(ValueError, match="Last N"):
        analyse_thresholds(data_root=root, run_directory=run, last_n_reversals=0)


def test_tui_exposes_human_config_and_step_calculator(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(100, 30)) as pilot:
            app.query_one("#nav-simulations", Button).press()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SimulationsScreen)
            index, selected = screen._current()
            fields = list(get_experiment(selected.experiment_id).fields)
            controls = {f.key: i for i, f in enumerate(fields)}
            n_index = controls["n_down"]
            up_index = controls["logUNIT_UP"]
            down_index = controls["logUNIT_DW"]
            screen.query_one(f"#sim-experiment-value-{index}-{n_index}", Input).value = "3"
            screen.query_one(f"#sim-experiment-value-{index}-{up_index}", Input).value = ".4"
            collapse = next(c for c in screen.query(Collapsible) if "Experiment settings" in c.title)
            collapse.collapsed = False
            await pilot.pause()
            screen.query_one(f"#sim-calculate-down-{index}", Button).press()
            await pilot.pause()
            assert float(screen.query_one(f"#sim-experiment-value-{index}-{down_index}", Input).value) == pytest.approx(.4*.7393)
            request = screen._request()
            assert request.experiment_values["n_down"] == 3
            assert request.experiment_values["logUNIT_DW"] == pytest.approx(.4*.7393)
            assert request.monitor_profile_id == "legacy_reference_display"
            assert set(request.experiment_values) == {f.key for f in fields}
            screen.query_one(f"#sim-experiment-value-{index}-{n_index}", Input).value = "0"
            with pytest.raises(ValueError, match="n-down"):
                screen._request()
    asyncio.run(scenario())


def test_data_browser_can_open_saved_staircases_without_hardware(tmp_path, monkeypatch):
    root = tmp_path / "local_psychophysics_data"
    result = run_scenario(experiment_id="contrast_sensitivity",
                          scenario_id="csf_short_censored", data_root=root, repo_root=ROOT)
    opened = []
    real_open_png = image_viewer.open_analysis_png
    monkeypatch.setattr(image_viewer, "open_analysis_png",
                        lambda data_root, image_path: opened.append(Path(image_path)))
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=root)
        async with app.run_test(size=(100, 30)) as pilot:
            app.query_one("#nav-data", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, DataScreen)
            app.screen.query_one("#open-staircase-image", Button).press()
            await pilot.pause()
            assert opened
            assert opened[0].is_file()
            assert opened[0].is_relative_to(root)
    asyncio.run(scenario())
    with pytest.raises(ValueError, match="PNG"):
        real_open_png(root, result.runs[0].artifacts.trial_log_file)
