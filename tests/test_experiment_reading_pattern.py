"""Keep one researcher reading pattern and prove TUI values drive adaptation."""
import ast
import asyncio
import importlib
from pathlib import Path

import pytest
from textual.widgets import Input

from psychophysics_lab.researcher import RunContext
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "src/psychophysics_lab/experiments"
EXPERIMENTS = tuple(p.stem for p in sorted(FOLDER.glob("*.py")) if p.stem != "__init__")
SECTIONS = ("SETTINGS AND STIMULI", "CONDITIONS AND TRIAL ORDER", "PREPARE STIMULI",
            "ONE TRIAL", "RESPONSES AND ADAPTATION", "RUN AND FINISH", "FRAMEWORK CONNECTION")


@pytest.mark.parametrize("identity", EXPERIMENTS)
def test_every_researcher_file_has_the_same_actual_reading_order(identity):
    source = (FOLDER/(identity+".py")).read_text(encoding="utf-8")
    headings = [source.index(f"# {i}. {section}") for i, section in enumerate(SECTIONS, 1)]
    assert headings == sorted(headings)
    tree = ast.parse(source)
    positions = {n.name:n.lineno for n in tree.body if isinstance(n, ast.FunctionDef)}
    names = ("make_conditions", "prepare_stimuli", "make_trial", "procedure", "definition")
    assert [positions[n] for n in names] == sorted(positions[n] for n in names)
    module = importlib.import_module("psychophysics_lab.experiments."+identity)
    assert module.SPEC.id == identity
    assert tuple(f for f in module.SPEC.fields if f.key != "response_keys") == module.FIELDS
    assert dict(module.SPEC.stimulus_slots) == module.STIMULUS_SLOTS
    assert dict(module.SPEC.stimulus_defaults) == module.STIMULUS_DEFAULTS
    assert module.SPEC.response_paradigm == module.RESPONSES


def test_framework_helpers_do_not_appear_as_experiment_files():
    internal = {"spec", "registry", "responses", "contributions", "library_builder", "flanker_response"}
    assert not (set(EXPERIMENTS) & internal)
    assert all((FOLDER/"_internal"/(name+".py")).is_file() for name in internal)
    from psychophysics_lab.experiments._internal.contributions import discover_experiment_modules
    discovered = discover_experiment_modules()
    assert discovered and all("._internal." not in name for name in discovered)


@pytest.mark.parametrize("identity", ["base_flanker", "indirect_flanker", "ellipse_2d", "orientation_adaptive"])
def test_tui_values_reach_each_adaptive_engine_and_preserve_valid_data(tmp_path, monkeypatch, identity):
    module = importlib.import_module("psychophysics_lab.experiments."+identity)
    legacy = identity != "orientation_adaptive"
    selected = ({"n_down":4, "trial_point":2, "reverse_point":2, "log_up":.1,
        "log_down":.07, "initial_log_down":.04, "reversal_limit":3, "condition_trial_limit":2,
        "trials_per_condition":2, "start_contrast":.02,
        "reference_width_px":1920, "reference_height_px":1080} if legacy else
        {"n_down":3, "n_up":2, "down_factor":.6, "up_factor":1.1, "trial_count":4})
    if identity == "ellipse_2d":
        selected |= {"decision_scene":"fixation_only_development", "condition_positions_deg":"[0.25, 0.5]"}
    async def collect():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/"tui_data")
        async with app.run_test(size=(100, 40)) as pilot:
            app.push_screen(ExperimentConfigScreen(data_root=tmp_path/"tui_data", participant_id="T001",
                session_mode="new", experiment=module.SPEC, monitor_profile_id="legacy_reference_display",
                defaults=module.SPEC.field_defaults() | selected))
            await pilot.pause()
            # Exercise changes after mounting, not only initial defaults.
            app.screen.query_one("#field-n-down", Input).value = str(selected["n_down"])
            values = app.screen._collect()
            return values, app.screen.stimulus_snapshots
    values, snapshots = asyncio.run(collect())
    assert all(values[key] == value for key, value in selected.items())
    seen = []
    original = RunContext.adaptive
    def capture(run, *args, **kwargs):
        algorithm = original(run, *args, **kwargs)
        seen.append(algorithm)
        return algorithm
    monkeypatch.setattr(RunContext, "adaptive", capture)
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path/"runs", experiment_id=identity,
        values=values, stimulus_snapshots=snapshots, observer=TeachingObserver(accuracy=1.), analyse=False)
    assert seen and artifacts.accepted_trials > 0
    if legacy:
        for key in module.SPEC.adaptive.controls:
            assert getattr(seen[0], key) == selected[key]
    else:
        assert seen[0].configurations[0].n_down == 3
        assert seen[0].configurations[0].n_up == 2
        assert module.next_contrast({"contrast":.1, "down_factor":.6, "up_factor":1.1},
                                   {"correct":True}, module.Step.DOWN) == pytest.approx(.06)
    assert all(check.passed for check in validate_run(artifacts.run_directory))
