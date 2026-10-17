import csv
import json
from pathlib import Path
import pytest
from psychophysics_lab.adaptive.legacy_flanker import LegacyFlankerAdaptive
from psychophysics_lab.experiments.indirect_flanker import make_trial as timeline
from psychophysics_lab.experiments.ellipse_2d import prepare_stimuli as scenes, make_trial as ellipse_timeline
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.core.synthetic import SimulationRun
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((Path(__file__).parent / "fixtures/legacy_flanker/numeric.json").read_text())


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c:c["name"])
def test_original_numeric_capture(case):
    a = LegacyFlankerAdaptive((1,2), start_contrast=.1, max_trials=1000,
                             reversal_limit=1000, condition_trial_limit=1000)
    for row in case["rows"]:
        identity, correct = row["identity"], row["correct"]
        expected = a.preview(identity, correct)
        assert a.states[identity].next_intensity == pytest.approx(row["presented"], abs=1e-12)
        a.respond(identity, correct, lambda step:expected[1])
        s = a.states[identity]
        assert s.next_intensity == pytest.approx(row["next"], abs=1e-12)
        assert s.correct_ticks == row["correct_ticks"]
        assert s.reversal_count == row["reversals"]


def test_invalid_numeric_update_does_not_consume_response():
    a = LegacyFlankerAdaptive((1,), start_contrast=.1)
    before = a.snapshot()
    with pytest.raises(ValueError):
        a.respond(1, True, lambda step:float("nan"))
    assert a.snapshot() == before


def test_adaptive_early_retirement_and_ceiling_are_distinct():
    a = LegacyFlankerAdaptive((1,), start_contrast=.1, max_trials=10, condition_trial_limit=2)
    for _ in range(2):
        value = a.preview(1, True)[1]
        a.respond(1, True, lambda step:value)
    assert a.status == "completed"
    with pytest.raises(RuntimeError):
        a.select(lambda ids:ids[0])
    b = LegacyFlankerAdaptive((1,), start_contrast=.1, max_trials=1)
    value = b.preview(1,True)[1]
    b.respond(1,True,lambda step:value)
    assert b.status == "max_trials_reached"


def test_source_phase_order_and_response_meanings():
    pair = timeline({}, {"first_trial":True})
    assert [(p.name,p.duration_ms) for p in pair.phases[:5]] == [
        ("leading_fixation",250),("fixation",250),("pre_interval",250),("stimulus",250),("delay",500)]
    assert pair.phases[-2].actions == ("up","down")
    ellipse = ellipse_timeline({}, {"first_trial":False})
    assert [p.name for p in ellipse.phases] == ["fixation","pre_interval","decision","interval_one",
        "inter_interval","interval_two","delay","answer","accepted_response"]
    assert ellipse.phases[-2].actions == ("first","second")


def simulate(tmp_path, identity, **overrides):
    data = tmp_path / "synthetic_data"
    values = {"reference_width_px":1920,"reference_height_px":1080,"start_contrast":.1,
              "trials_per_condition":3}
    if identity == "ellipse_2d":
        values |= {"condition_positions_deg":"[0.25, 0.5]", "decision_scene":"fixation_only_development"}
    values |= overrides
    sim = SimulationRun(data, {"seed":123,"physical_display_used":False,
                              "observer_parameters":{"accuracy":1.}}, lambda *args:None)
    return run_request(SetupRequest("synthetic_123","new",identity,"legacy_reference_display",values),
                       repo_root=ROOT,data_root=data,simulation=sim)


@pytest.mark.parametrize("identity", ["indirect_flanker","base_flanker","ellipse_2d"])
def test_virtual_end_to_end_preserves_canonical_provenance(tmp_path, identity):
    result = simulate(tmp_path, identity)
    assert result.status == "max_trials_reached"
    failures = [c for c in validate_run(result.run_directory) if not c.passed]
    assert not failures
    rows = list(csv.DictReader(result.trial_log_file.open(),delimiter="\t"))
    assert rows and all(r["response_key"].startswith("SIMULATED_") for r in rows)
    assert all(r["presented_screen_intensity"] and r["next_screen_intensity"] and r["staircase_id"] for r in rows)
    actions = json.loads((result.run_directory / "trial_actions.json").read_text())["trials"]
    assert all(t["status"] == "completed" for t in actions)
    manifest = json.loads((result.run_directory / "manifest.json").read_text())
    assert "src/psychophysics_lab/stimulus_library.py" in manifest["software"]["runtime_source_sha256"]
    lifecycle = json.loads((result.run_directory / "procedure_lifecycle.json").read_text())
    assert lifecycle["adaptive_stop_status"] == "max_trials_reached"


def test_pair_differs_only_by_grating_and_is_reproducible(tmp_path):
    a = simulate(tmp_path / "a", "indirect_flanker")
    b = simulate(tmp_path / "b", "base_flanker")
    assert a.trial_log_file.read_bytes() == b.trial_log_file.read_bytes()
    traces = [json.loads((r.run_directory / "trial_actions.json").read_text())["trials"] for r in (a,b)]
    for left,right in zip(*traces):
        assert left["target"] == right["target"] and left["condition"] == right["condition"]
        docs = [json.loads(t["resolved_stimuli"]["stimulus"]["parameters"]["scene_json"]) for t in (left,right)]
        assert docs[0]["drawings"][0]["kind"] == "grating"
        assert docs[0]["drawings"][1:] == docs[1]["drawings"]


def test_missing_ellipse_science_is_not_invented(tmp_path):
    with pytest.raises(ValueError,match="expALL_decsison"):
        simulate(tmp_path,"ellipse_2d",decision_scene="unresolved")
    with pytest.raises(ValueError,match="Condition positions"):
        simulate(tmp_path / "other","ellipse_2d",condition_positions_deg="[]")


def test_human_preflight_and_direct_calls_are_blocked_before_display():
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.config.preflight import human_blockers
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    for identity in ("indirect_flanker","base_flanker","ellipse_2d"):
        spec = get_experiment(identity)
        assert any("Development reconstruction" in message for message in human_blockers(spec,profile))
        with pytest.raises(ValueError,match="Development reconstruction"):
            spec.procedure(type("Run",(),{"synthetic":False})())
    from psychophysics_lab.experiments._internal.flanker_response import SPEC
    assert SPEC is get_experiment("contrast_sensitivity")
    assert SPEC.procedure is None


def test_ellipse_literal_geometry_and_both_interval_orders():
    from types import SimpleNamespace
    from psychophysics_lab.experiments.ellipse_2d import pixel_geometry
    from psychophysics_lab.config.monitor import load_monitor_profiles
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    g = pixel_geometry(SimpleNamespace(display=profile, values={"reference_width_px":1920,"reference_height_px":1080}))
    import json
    run = SimpleNamespace(values={"background":.24, "scene_size_deg":18.})
    a = scenes(run, {"position_deg":.25, "target":0, "intensity":.4}, {"geometry":g})
    b = scenes(run, {"position_deg":.25, "target":1, "intensity":.4}, {"geometry":g})
    assert a["first"] == b["second"]
    assert a["second"] == b["first"]
    ring,probe,dot = json.loads(a["first"]["scene_json"])["drawings"]
    assert ring["parameters"]["y_deg"] == dot["parameters"]["y_deg"] == g["fixation_y_deg"]
    assert probe["parameters"]["x_deg"] == .25
    assert g["ellipse_rx_deg"] > 4  # 250 px on this explicitly selected reference display, not .5 deg


def test_missing_monitor_resolution_is_not_invented():
    from types import SimpleNamespace
    from psychophysics_lab.experiments.ellipse_2d import pixel_geometry
    from psychophysics_lab.config.monitor import load_monitor_profiles
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    with pytest.raises(ValueError,match="historical resolution is unknown"):
        pixel_geometry(SimpleNamespace(display=profile,values={"reference_width_px":0,"reference_height_px":0}))


def test_out_of_range_next_value_is_not_silently_clamped(tmp_path, monkeypatch):
    from psychophysics_lab.researcher import RunContext
    original = RunContext.trial
    def always_wrong(run,*args,**kwargs):
        run.observer_parameters = {"accuracy":0.}
        return original(run,*args,**kwargs)
    monkeypatch.setattr(RunContext,"trial",always_wrong)
    with pytest.raises(ValueError,match="exceeds digital range"):
        simulate(tmp_path,"base_flanker",start_contrast=1.,condition_positions_deg="[0.25]")
    directory = next((tmp_path/"synthetic_data").rglob("manifest.json")).parent
    assert json.loads((directory/"manifest.json").read_text())["status"] == "error"
    rows = list(csv.DictReader((directory/"trials.tsv").open(),delimiter="\t"))
    assert len(rows) == 1 and float(rows[0]["next_screen_intensity"]) > 1
    assert all(c.passed for c in validate_run(directory))


def test_adaptive_completion_requires_owned_stopped_algorithm(tmp_path):
    from psychophysics_lab.researcher import RunContext
    from psychophysics_lab.config.monitor import load_monitor_profiles
    spec = get_experiment("base_flanker")
    run = RunContext(spec.normalise_values({}),load_monitor_profiles(ROOT)["legacy_reference_display"],spec,tmp_path,synthetic=True)
    run.initialise(expected_trials=3,resolution={"test":"adaptive boundary"})
    a = run.adaptive((1,),start_contrast=.1,max_trials=3,condition_trial_limit=1)
    with pytest.raises(ValueError):
        run.complete_adaptive(a)
    candidate = a.preview(1,True)[1]
    run.update_adaptive(a,1,True,lambda step:candidate)
    run.record(stimulus_condition=.25,target_alternative=0,participant_response=0,response_key="UP",correct=1,adaptive=a)
    run.complete_adaptive(a)
    life = json.loads((tmp_path/"procedure_lifecycle.json").read_text())
    assert life["status"] == "completed" and life["response_ceiling"] == 3 and life["accepted_trials"] == 1


def test_registered_development_protocol_does_not_change_csf_default():
    from psychophysics_lab.experiments._internal.registry import list_experiments
    specs = list_experiments()
    assert specs[0].id == "contrast_sensitivity"
    assert {s.id for s in specs if s.acquisition_block_reason} >= {"base_flanker","indirect_flanker","ellipse_2d"}
