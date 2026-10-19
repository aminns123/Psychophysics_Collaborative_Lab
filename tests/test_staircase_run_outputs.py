"""Per-run adaptive figures and canonical data survive partial and completed runs.

These checks exercise the current CSF experiment and figure APIs. Legacy CSF
scenario IDs and its retired response-file renderer are not supported.
"""
import csv
import hashlib
import json
from pathlib import Path
import time

import pytest

from simulations.run import simulate
from psychophysics_lab.analysis.previews import (
    create_run_figures, create_staircase_preview, latest_staircase_plot
)
from psychophysics_lab.analysis.thresholds import analyse_thresholds
from psychophysics_lab.experiments._internal.registry import get_experiment
from test_pipeline_repairs import saved_run

ROOT=Path(__file__).resolve().parents[1]


def test_multiple_independent_staircases_per_condition_and_nonempty_dynamic_plot(tmp_path):
    data=tmp_path/"data"
    artifacts,_=simulate(data_root=data,repo_root=ROOT,seed=17,analyse=False,
        values={"frequencies_cpd":"2,8","staircases_per_condition":3,
                "max_trials":120,"reversal_termination":10})
    run=artifacts.run_directory
    assert (run/"trials.tsv").is_file()
    history=json.loads((run/"adaptive_session.json").read_text())
    assert len(history["staircases"])==6
    assert (run/"analysis/staircases.png").stat().st_size>3000
    with (run/"trials.tsv").open(newline="",encoding="utf-8") as handle:
        rows=list(csv.DictReader(handle,delimiter="\t"))
    observed={(r["stimulus_condition"],r["staircase_id"]) for r in rows}
    assert len(observed)>=2
    quicklook=json.loads((run/"analysis/staircase_preview.json").read_text())
    assert quicklook["staircases_plotted"]==len({sid for _,sid in observed})
    assert quicklook["plotted_accepted_trials"]==len(rows)
    for png in quicklook["condition_plots"]:
        assert (run/"analysis"/png).stat().st_size>1000
    assert latest_staircase_plot(data_root=data,run_directory=run)==run/"analysis/staircases.png"


def test_repeated_seeds_create_independent_self_contained_runs(tmp_path):
    data=tmp_path/"data"
    runs=[]
    for seed in (41,42):
        run,_=simulate(data_root=data,repo_root=ROOT,seed=seed,analyse=False,
            values={"frequencies_cpd":"2","staircases_per_condition":1,"max_trials":8})
        runs.append(run.run_directory)
        manifest=json.loads((run.run_directory/"manifest.json").read_text())
        assert manifest["data_kind"]=="synthetic"
        assert (run.run_directory/"trials.tsv").is_file()
        assert (run.run_directory/"analysis/staircases.png").is_file()
    assert len(set(runs))==2


def test_staircase_instance_count_is_a_selected_public_experiment_field():
    spec=get_experiment("contrast_sensitivity")
    assert "staircases_per_condition" in {f.key for f in spec.fields}
    assert "staircases_per_condition" in spec.adaptive.controls
    assert spec.normalise_values(spec.field_defaults() | {
        "staircases_per_condition":4})["staircases_per_condition"]==4
    for invalid in (0,-1):
        with pytest.raises(ValueError):
            spec.normalise_values(spec.field_defaults() | {
                "staircases_per_condition":invalid})
    # Researcher-selected repetition counts are not capped at an old thesis default.
    assert spec.normalise_values(spec.field_defaults() | {
        "staircases_per_condition":25})["staircases_per_condition"] == 25


@pytest.mark.parametrize("status",["completed","max_trials_reached","aborted_by_user","error"])
def test_human_partial_run_creates_staircase_figures_from_canonical_records(tmp_path,status):
    # These stored rows have human provenance; no fake participant renderer is
    # required to test the post-acquisition data contract.
    run=saved_run(tmp_path,status=status,kind="human",complete=False)
    original=(run/"trials.tsv").read_bytes()
    report=create_run_figures(data_root=tmp_path,run_directory=run)
    assert report["data_kind"]=="human"
    assert (run/"analysis/staircases.png").is_file()
    assert (run/"analysis/staircase_preview.json").is_file()
    assert (run/"analysis/analysis_status.json").is_file()
    assert (run/"trials.tsv").read_bytes()==original


def test_reanalysis_stays_in_the_run_and_never_changes_raw_trials(tmp_path):
    data=tmp_path/"data"
    artifacts,_=simulate(data_root=data,repo_root=ROOT,seed=18,analyse=False,
        values={"frequencies_cpd":"2","staircases_per_condition":1,"max_trials":80})
    run=artifacts.run_directory
    before=(run/"trials.tsv").read_bytes()
    for retained in (2,3):
        try:
            summary=analyse_thresholds(data_root=data,run_directory=run,
                last_n_reversals=retained,exploratory=True)
        except ValueError as exc:
            # An incomplete staircase with no reversals must be reported as
            # unavailable rather than fabricated as a primary estimate.
            assert "reversal" in str(exc).lower()
        else:
            assert summary.output_directory.is_relative_to(run/"analysis/thresholds")
    assert (run/"trials.tsv").read_bytes()==before


def test_terminal_simulation_heartbeat_prints_activity_dots(capsys):
    from simulations.progress import simulation_heartbeat
    with simulation_heartbeat("Testing simulated participant",interval=.001):
        time.sleep(.03)
    content=capsys.readouterr().out
    assert "Testing simulated participant" in content
    assert "." in content and "finished" in content


def test_data_browser_can_open_ordinary_saved_adaptive_run_without_hardware(tmp_path,monkeypatch):
    import asyncio
    from textual.widgets import Button, Static
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    from psychophysics_lab.ui import plots as viewer

    data=tmp_path/"data"
    case,_=simulate(data_root=data,repo_root=ROOT,seed=22,analyse=False,
        values={"frequencies_cpd":"2","staircases_per_condition":1,"max_trials":12})
    opened=[]
    monkeypatch.setattr(viewer,"open_run_directory",
                        lambda data_root,run_dir:opened.append((data_root,run_dir)))
    async def navigate():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=data)
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one("#nav-data",Button).press()
            await pilot.pause()
            details=str(app.screen.query_one("#data-details",Static).render())
            assert "Staircases plotted" in details
            app.screen.query_one("#open-run-folder",Button).press()
            await pilot.pause()
            assert opened and opened[0][1]==case.run_directory
    asyncio.run(navigate())
