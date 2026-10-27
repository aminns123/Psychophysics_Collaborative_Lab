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
    module = importlib.import_module("psychophysics_lab.experiments." + identity)
    if identity == "contrast_sensitivity_windowed":
        # This variant deliberately imports the common trial engine rather
        # than duplicating it just to satisfy a source-layout convention.
        from psychophysics_lab.experiments import contrast_sensitivity as shared
        for name in ("make_conditions", "interpret_response",
                     "update_experiment", "finish_experiment"):
            assert getattr(module, name) is getattr(shared, name)
        assert module.prepare_stimuli is not shared.prepare_stimuli
        assert module.SPEC.id != shared.SPEC.id
        assert module.SPEC.stimulus_slots["grating"] != shared.SPEC.stimulus_slots["grating"]
    source = (FOLDER / (identity + ".py")).read_text(encoding="utf-8")
    migrated = hasattr(module, "trial_events")
    sections = ("PARAMETERS", "SESSION START", "TRIAL EVENTS", "SCIENTIFIC RULES",
                "STOPPING AND RESULTS", "FRAMEWORK REGISTRATION") if migrated else SECTIONS
    headings = [source.index(f"# {i}. {section}") for i, section in enumerate(sections, 1)]
    assert headings == sorted(headings)
    tree = ast.parse(source)
    positions = {n.name: n.lineno for n in tree.body if isinstance(n, ast.FunctionDef)}
    names = (("trial_events", "prepare_stimuli", "make_conditions", "procedure", "definition")
             if migrated else ("make_conditions", "prepare_stimuli", "make_trial", "procedure", "definition"))
    if identity == "contrast_sensitivity_windowed":
        names = ("trial_events", "prepare_stimuli", "procedure", "definition")
    assert [positions[n] for n in names] == sorted(positions[n] for n in names)
    module = importlib.import_module("psychophysics_lab.experiments." + identity)
    from psychophysics_lab.experiments._internal.source_names import SOURCE_IDS

    assert module.SPEC.id == SOURCE_IDS.get(identity, identity)
    assert tuple(f for f in module.SPEC.fields if f.key != "response_keys") == tuple(f for f in module.FIELDS if f.key != "response_keys")
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
    }
    assert not (set(EXPERIMENTS) & internal)
    assert all((FOLDER / "_internal" / (name + ".py")).is_file() for name in internal)
    from psychophysics_lab.experiments._internal.contributions import discover_experiment_modules

    discovered = discover_experiment_modules()
    assert discovered and all("._internal." not in name for name in discovered)


@pytest.mark.parametrize("identity,custom", [
    ("line_position_baseline", {"positions_deg":"0","probe_vertical_offset_deg":.5}),
    ("line_position_flanker", {"positions_deg":"0","probe_vertical_offset_deg":.5,"flanker_cpd":2.}),
    ("ellipse_centre", {"aspect_ratios":"1","ring_increment":.1}),
    ("ellipse_major_axis", {"aspect_ratios":"1","positions_deg":"0","ring_increment":.1}),
    ("contrast_sensitivity", {"frequencies_cpd":"2"}),
    ("orientation_adaptive", {"trial_count":4,"n_down":3,"n_up":2}),
])
def test_tui_values_reach_each_active_adaptive_engine_and_preserve_data(tmp_path,monkeypatch,identity,custom):
    module=importlib.import_module("psychophysics_lab.experiments."+identity)
    chosen=module.SPEC.normalise_values(module.SPEC.field_defaults() | custom | {
        "max_trials":4
    } if identity!="orientation_adaptive" else module.SPEC.field_defaults() | custom)
    assert all(chosen[key]==value for key,value in custom.items())
    assert module.SPEC.procedure is module.procedure
    conditions=module.make_conditions(chosen)
    assert conditions
    # Run the same public experiment through the actual synthetic trial
    # recorder and validator rather than the deleted historical adapters.
    from simulations.psychometric import PsychometricObserver
    artifacts,_=simulate(repo_root=ROOT,data_root=tmp_path/"runs",
        experiment_id=identity,values=chosen,seed=19,analyse=False,
        observer=TeachingObserver(accuracy=1.0))
    assert artifacts.accepted_trials>0
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
            if name in {"update_experiment", "is_finished"} and not hasattr(module, name):
                # A study using the public contrast-method strategy may own
                # adaptive updates/stopping in its imported method instead
                # of duplicating them inside the scientific experiment file.
                assert callable(getattr(module, "adaptive_method", None)) or module.SPEC.adaptive is None
                continue
            parameters = tuple(inspect.signature(getattr(module, name)).parameters.values())
            assert tuple(p.name for p in parameters[:len(arguments)]) == arguments, (
                identity,
                name,
            )
            assert all(p.kind is inspect.Parameter.KEYWORD_ONLY
                       and p.default is not inspect.Parameter.empty
                       for p in parameters[len(arguments):]), (identity, name)
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
        if "trial_count" in module.SPEC.field_defaults()
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
    if identity in {"contrast_sensitivity", "contrast_sensitivity_windowed"}:
        values |= {"max_trials": 4, "frequencies_cpd": "2", "starting_contrast": 0.02}
    if identity in {"line_position_baseline","line_position_flanker","ellipse_major_axis","ellipse_centre"}:
        values = {"max_trials":4,"probe_vertical_offset_deg":.5} if identity.startswith("line_") else {"max_trials":4,"ring_increment":.1}
        if identity == "line_position_flanker": values["flanker_cpd"] = 2.
    calls = []
    event_name = "trial_events" if hasattr(module, "trial_events") else "make_trial"
    prepare, make_trial = module.prepare_stimuli, getattr(module, event_name)
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
        from psychophysics_lab.core.timeline import as_trial_timeline
        authored = make_trial(settings, condition)
        result = as_trial_timeline(authored)
        assert not any(isinstance(p, (UpdateState, UpdateAdaptive)) for p in result.phases)
        responses = [p for p in result.phases if p.kind == "response"]
        assert len(responses) == 1 and responses[0].actions == module.SPEC.response_paradigm.alternatives
        if module.SPEC.response_paradigm.alternatives == ("first", "second"):
            assert responses[0].actions == ("first", "second")
            assert [
                p.name
                for p in result.phases
                if p.name in {"interval_one", "inter_interval", "interval_two"}
            ] == ["interval_one", "inter_interval", "interval_two"]
        return authored

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
    monkeypatch.setattr(module, event_name, checked_trial)
    monkeypatch.setattr(module, "interpret_response", checked_interpret)
    if update is not None:
        monkeypatch.setattr(module, "update_experiment", checked_update)
        if identity == "contrast_sensitivity_windowed":
            # The imported method factory resolves the callback in its owning
            # module; instrument the function actually used by that method.
            from psychophysics_lab.experiments import contrast_sensitivity as shared
            monkeypatch.setattr(shared,"update_experiment",checked_update)
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
