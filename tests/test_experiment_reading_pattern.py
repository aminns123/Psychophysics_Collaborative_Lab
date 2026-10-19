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
SECTIONS = (
    "SETTINGS AND STIMULI",
    "CONDITIONS AND TRIAL ORDER",
    "PREPARE STIMULI",
    "ONE TRIAL",
    "RESPONSES AND ADAPTATION",
    "RUN AND FINISH",
    "FRAMEWORK CONNECTION",
)


@pytest.mark.parametrize("identity", EXPERIMENTS)
def test_every_researcher_file_has_the_same_actual_reading_order(identity):
    source = (FOLDER / (identity + ".py")).read_text(encoding="utf-8")
    headings = [source.index(f"# {i}. {section}") for i, section in enumerate(SECTIONS, 1)]
    assert headings == sorted(headings)
    tree = ast.parse(source)
    positions = {n.name: n.lineno for n in tree.body if isinstance(n, ast.FunctionDef)}
    names = ("make_conditions", "prepare_stimuli", "make_trial", "procedure", "definition")
    assert [positions[n] for n in names] == sorted(positions[n] for n in names)
    module = importlib.import_module("psychophysics_lab.experiments." + identity)
    from psychophysics_lab.experiments._internal.source_names import SOURCE_IDS

    assert module.SPEC.id == SOURCE_IDS.get(identity, identity)
    assert tuple(f for f in module.SPEC.fields if f.key != "response_keys") == module.FIELDS
    assert dict(module.SPEC.stimulus_slots) == module.STIMULUS_SLOTS
    assert dict(module.SPEC.stimulus_defaults) == module.STIMULUS_DEFAULTS
    assert module.SPEC.response_paradigm == module.RESPONSES


def test_framework_helpers_do_not_appear_as_experiment_files():
    internal = {
        "spec",
        "registry",
        "responses",
        "contributions",
        "library_builder",
        "flanker_response",
    }
    assert not (set(EXPERIMENTS) & internal)
    assert all((FOLDER / "_internal" / (name + ".py")).is_file() for name in internal)
    from psychophysics_lab.experiments._internal.contributions import discover_experiment_modules

    discovered = discover_experiment_modules()
    assert discovered and all("._internal." not in name for name in discovered)


@pytest.mark.parametrize(
    "identity", ["base_flanker", "indirect_flanker", "ellipse_2d", "orientation_adaptive"]
)
def test_tui_values_reach_each_adaptive_engine_and_preserve_valid_data(
    tmp_path, monkeypatch, identity
):
    legacy = identity != "orientation_adaptive"
    module = importlib.import_module("psychophysics_lab.experiments." + ("_internal.historical." if legacy else "") + identity)
    selected = (
        {
            "n_down": 4,
            "trial_point": 2,
            "reverse_point": 2,
            "log_up": 0.1,
            "log_down": 0.07,
            "initial_log_down": 0.04,
            "reversal_limit": 3,
            "condition_trial_limit": 2,
            "trials_per_condition": 2,
            "start_contrast": 0.02,
            "reference_width_px": 1920,
            "reference_height_px": 1080,
        }
        if legacy
        else {"n_down": 3, "n_up": 2, "down_factor": 0.6, "up_factor": 1.1, "trial_count": 4}
    )
    if identity == "ellipse_2d":
        selected |= {
            "decision_scene": "fixation_only_development",
            "condition_positions_deg": "[0.25, 0.5]",
        }

    async def collect():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / "tui_data")
        async with app.run_test(size=(100, 40)) as pilot:
            app.push_screen(
                ExperimentConfigScreen(
                    data_root=tmp_path / "tui_data",
                    participant_id="T001",
                    session_mode="new",
                    experiment=module.SPEC,
                    monitor_profile_id="legacy_reference_display",
                    defaults=module.SPEC.field_defaults() | selected,
                )
            )
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
    artifacts, _ = simulate(
        repo_root=ROOT,
        data_root=tmp_path / "runs",
        experiment_id=identity,
        values=values,
        stimulus_snapshots=snapshots,
        observer=TeachingObserver(accuracy=1.0),
        analyse=False,
    )
    assert seen and artifacts.accepted_trials > 0
    if legacy:
        for key in module.SPEC.adaptive.controls:
            assert getattr(seen[0], key) == selected[key]
    else:
        assert seen[0].configurations[0].n_down == 3
        assert seen[0].configurations[0].n_up == 2
        assert module.next_contrast(
            {"contrast": 0.1, "down_factor": 0.6, "up_factor": 1.1},
            {"correct": True},
            module.Step.DOWN,
        ) == pytest.approx(0.06)
    assert all(check.passed for check in validate_run(artifacts.run_directory))


def test_scientific_interfaces_are_readable_without_identical_main_loops():
    import inspect

    contracts = {
        "make_conditions": ("settings",),
        "choose_condition": ("run", "conditions", "state"),
        "prepare_stimuli": ("run", "condition", "state"),
        "make_trial": ("settings", "condition"),
        "interpret_response": ("condition", "response"),
        "update_experiment": ("run", "condition", "state", "response", "trial"),
        "is_finished": ("run", "conditions", "state"),
        "initialise_experiment": ("run", "conditions"),
        "trial_record": ("run", "condition", "state"),
        "finish_experiment": ("run", "conditions", "state"),
    }
    procedures = []
    for identity in EXPERIMENTS:
        module = importlib.import_module("psychophysics_lab.experiments." + identity)
        for name, arguments in contracts.items():
            if name in {"update_experiment","is_finished"} and module.SPEC.adaptive is None and not hasattr(module,name):
                continue
            assert tuple(inspect.signature(getattr(module, name)).parameters) == arguments, (
                identity,
                name,
            )
        node = ast.parse(inspect.getsource(module.procedure)).body[0]
        procedures.append(ast.dump(node, include_attributes=False))
        assert not any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id in {"UpdateAdaptive", "UpdateState"}
            for n in ast.walk(ast.parse(inspect.getsource(module.make_trial)))
        )
    assert len(set(procedures)) > 1  # scientifically justified fixed/adaptive structures differ


@pytest.mark.parametrize("identity", EXPERIMENTS)
def test_actual_condition_stimulus_response_contract_for_every_experiment(
    tmp_path, monkeypatch, identity
):
    from psychophysics_lab.experiments._internal import registry
    from psychophysics_lab.stimuli.registry import get_stimulus
    from psychophysics_lab.researcher import UpdateState, UpdateAdaptive

    module = importlib.import_module("psychophysics_lab.experiments." + identity)
    # Exercise the managed custom file in isolation without publishing edited source.
    if identity == "new_probe_vertical_line_stimulus":
        monkeypatch.setitem(registry._REGISTRY, module.SPEC.id, module.SPEC)
    values = (
        {"trial_count": 4}
        if identity
        not in {"base_flanker", "indirect_flanker", "ellipse_2d", "contrast_sensitivity"}
        else {}
    )
    if identity in {"base_flanker", "indirect_flanker", "ellipse_2d"}:
        values |= {
            "reference_width_px": 1920,
            "reference_height_px": 1080,
            "start_contrast": 0.02,
            "trials_per_condition": 2,
        }
    if identity == "ellipse_2d":
        values |= {
            "condition_positions_deg": "[0.25, 0.5]",
            "decision_scene": "fixation_only_development",
        }
    if identity == "contrast_sensitivity":
        values |= {"max_trials": 4, "frequencies_cpd": "2", "starting_contrast": 0.02}
    if identity in {"line_position_baseline","line_position_flanker","ellipse_major_axis","ellipse_centre"}:
        values = {"max_trials":4,"probe_vertical_offset_deg":.5} if identity.startswith("line_") else {"max_trials":4,"ring_increment":.1}
        if identity == "line_position_flanker": values["flanker_cpd"] = 2.
    calls = []
    prepare, make_trial = module.prepare_stimuli, module.make_trial
    interpret, update = module.interpret_response, getattr(module,"update_experiment",None)

    def checked_prepare(run, condition, state):
        assert isinstance(condition, dict) and {"target", "value"} <= condition.keys()
        assert condition["target"] in (0, 1)
        result = prepare(run, condition, state)
        assert isinstance(result, dict) and result
        for slot, parameters in result.items():
            stimulus = get_stimulus(run.stimulus_snapshots[slot]["document"]["stimulus_id"])
            assert stimulus.validate_parameters(parameters) == parameters
        calls.append("prepare")
        return result

    def checked_trial(settings, condition):
        result = make_trial(settings, condition)
        assert not any(isinstance(p, (UpdateState, UpdateAdaptive)) for p in result.phases)
        responses = [p for p in result.phases if p.kind == "response"]
        assert len(responses) == 1 and responses[0].actions == module.RESPONSES.alternatives
        if module.PARADIGM == "two_interval_forced_choice":
            assert responses[0].actions == ("first", "second")
            assert [
                p.name
                for p in result.phases
                if p.name in {"interval_one", "inter_interval", "interval_two"}
            ] == ["interval_one", "inter_interval", "interval_two"]
        return result

    def checked_interpret(condition, response):
        calls.append("interpret")
        assert response["valid"]
        result = interpret(condition, response)
        assert result["correct"] == (condition["target"] == response["alternative"])
        return result

    def checked_update(run, condition, state, response, trial):
        calls.append("update")
        assert calls[-2] == "interpret"
        return update(run, condition, state, response, trial)

    monkeypatch.setattr(module, "prepare_stimuli", checked_prepare)
    monkeypatch.setattr(module, "make_trial", checked_trial)
    monkeypatch.setattr(module, "interpret_response", checked_interpret)
    if update is not None:
        monkeypatch.setattr(module, "update_experiment", checked_update)
    artifacts, _ = simulate(
        repo_root=ROOT,
        data_root=tmp_path / "data",
        experiment_id=module.SPEC.id,
        values=values,
        observer=TeachingObserver(accuracy=1.0),
        analyse=False,
    )
    assert artifacts.accepted_trials > 0
    # Ignore the explicit pre-acquisition render planning, before interpretation.
    first_interpretation = calls.index("interpret")
    assert all(c == "prepare" for c in calls[:first_interpretation])
    calls = calls[first_interpretation-1:]
    assert calls == [
        stage
        for _ in range(artifacts.accepted_trials)
        for stage in (("prepare", "interpret", "update") if update is not None else ("prepare", "interpret"))
    ]
    assert all(check.passed for check in validate_run(artifacts.run_directory))
