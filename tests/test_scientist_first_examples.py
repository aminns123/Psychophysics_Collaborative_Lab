"""Executable investigation: public extensions, real runner and canonical data."""
import csv
import ast
from dataclasses import replace
import json
import importlib.util
from pathlib import Path
import shutil
import sys

import pytest
from psychophysics_lab import extensions as ext
from psychophysics_lab.development import execute_user_action
from psychophysics_lab.experiments import contrast_sensitivity as reference
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.researcher import TrialTimeline
from simulations.run import simulate
from simulations.registry import TeachingObserver
from simulations.psychometric import PsychometricObserver
from scripts.validate_run import validate_run
from psychophysics_lab.data.reader import load_run

ROOT = Path(__file__).resolve().parents[1]
CSF = "demolab__csf_two_part"
TEMPORAL = "demolab__temporal_order"
VALUES = dict(frequencies_cpd="2,8", staircases_per_condition=2, max_trials=160,
              n_down=1, n_up=1, reversal_termination=4, threshold_reversals=2,
              fixed_contrasts="0,.1", fixed_repetitions=2)


@pytest.fixture
def lab(tmp_path, monkeypatch):
    registry.list_experiments()
    ext.unload()
    folder = tmp_path / "laboratory"
    shutil.copytree(ROOT / "examples/scientist_first", folder)
    monkeypatch.setattr("psychophysics_lab.development.user_data_root", lambda repo: tmp_path / "checks")
    monkeypatch.setattr("psychophysics_lab.analysis.previews.create_run_figures", lambda **kwargs: None)
    ext.configure(ROOT, folder, trusted=True)
    assert not ext.load(ROOT, development=True)
    yield folder
    ext.unload()


def module(identity):
    return sys.modules[registry.get_experiment(identity).procedure.__module__]


def ready(identity, values):
    assert execute_user_action(ROOT, "test", identity, values) == 0
    ext.publish(ROOT, "experiment", identity)
    assert ext.status(ROOT, "experiment", identity) == "ready"


def read(run, filename):
    return json.loads((run.run_directory / filename).read_text(encoding="utf-8"))


def presentations(run):
    return [json.loads(line)["presentation"] for line in
            (run.run_directory / "trial_events.jsonl").read_text(encoding="utf-8").splitlines()
            if "presentation" in json.loads(line)]


@pytest.mark.parametrize("method", ["adaptive", "constant_stimuli"])
@pytest.mark.parametrize("opening", [False, True])
@pytest.mark.parametrize("observer", [TeachingObserver(.65), PsychometricObserver()])
def test_csf_matches_reference_trial_bytes_histories_estimators_and_stimuli(lab, tmp_path, monkeypatch, method, opening, observer):
    values = VALUES | {"contrast_method": method}
    ready(CSF, values)
    prototype = module(CSF)
    assert prototype.SPEC.field_defaults() == reference.SPEC.field_defaults()
    assert prototype.make_conditions(prototype.SPEC.normalise_values(values)) == reference.make_conditions(reference.SPEC.normalise_values(values))
    for identity in ("contrast_sensitivity", CSF):
        spec = registry.get_experiment(identity)
        if not opening:
            monkeypatch.setitem(registry._REGISTRY, identity, replace(spec, session_start=[]))
    runs = [simulate(repo_root=ROOT, data_root=tmp_path / "runs", experiment_id=identity,
                     values=values, seed=137, observer=observer, analyse=False)[0]
            for identity in ("contrast_sensitivity", CSF, CSF)]
    baseline, candidate, repeated = runs
    assert candidate.trial_log_file.read_bytes() == baseline.trial_log_file.read_bytes() == repeated.trial_log_file.read_bytes()
    assert (candidate.status, candidate.accepted_trials) == (baseline.status, baseline.accepted_trials)
    for filename in ("adaptive_history.json", "adaptive_session.json", "primary_thresholds.json"):
        if (baseline.run_directory / filename).exists():
            assert read(candidate, filename) == read(baseline, filename)
    # Function provenance correctly identifies the external source. Only that
    # qualified callback label differs; compare every other action/state value.
    old_actions = read(baseline, "trial_actions.json")
    new_actions = read(candidate, "trial_actions.json")
    renamed = json.dumps(new_actions).replace(prototype.__name__ + ".change_contrast", reference.__name__ + ".change_contrast")
    assert json.loads(renamed) == old_actions
    def function_body(author, name):
        tree = ast.parse(Path(author.__file__).read_text(encoding="utf-8"))
        return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), include_attributes=False)
    # Track construction now derives from the explicit scientific factor list;
    # its complete values/order are compared above, rather than its source AST.
    for name in ("choose_condition", "change_contrast", "update_experiment", "is_finished", "primary_rule"):
        assert function_body(prototype, name) == function_body(reference, name)
    if method == "adaptive":
        assert read(candidate, "resolved_experiment.json")["reversal_contrasts"] == read(baseline, "resolved_experiment.json")["reversal_contrasts"]
    else:
        assert read(candidate, "resolved_experiment.json")["observed_level_accuracy"] == read(baseline, "resolved_experiment.json")["observed_level_accuracy"]
    for run in runs:
        assert (run.run_directory / "session_events.json").exists() == opening
        assert len(load_run(run.run_directory)["trials"]) == 20
        assert all(c.passed for c in validate_run(run.run_directory))
    assert candidate.accepted_trials > 0
    saved_presentations = presentations(candidate)
    assert len(saved_presentations) == candidate.accepted_trials
    assert all(set(p["measurements"]) == set(prototype.MEASUREMENT_UNITS) for p in saved_presentations)
    old_journal = [json.loads(line) for line in (baseline.run_directory / "trial_events.jsonl").read_text(encoding="utf-8").splitlines()]
    new_journal = [json.loads(line) for line in (candidate.run_directory / "trial_events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["trial"]["resolved_stimuli"] for x in old_journal] == [x["trial"]["resolved_stimuli"] for x in new_journal]
    provenance = read(candidate, "manifest.json")
    assert CSF in json.dumps(provenance)


@pytest.mark.parametrize("identity", [CSF, TEMPORAL])
def test_public_test_ready_source_invalidation_and_measurement_validation(lab, tmp_path, monkeypatch, identity):
    values = VALUES if identity == CSF else {"soa_ms": "-100,100", "repetitions": 1}
    ready(identity, values)
    author = module(identity)
    assert author.SPEC.id == Path(author.__file__).stem
    assert author.SPEC.source_paths == (f"experiments/{identity}.py",)
    checker = author._measurements if identity == CSF else author._record
    settings = author.SPEC.normalise_values(values)
    condition = ({"frequency_cpd": 2., "repeat": 1, "target": 0, "contrast": .1}
                 if identity == CSF else {"soa_ms": -100, "target": 0, "repeat": 1})
    for invalid in ({}, dict.fromkeys(author.MEASUREMENT_UNITS, float("nan")),
                    dict.fromkeys(author.MEASUREMENT_UNITS, [1])):
        monkeypatch.setattr(author, "trial_measurements", lambda *args, value=invalid: value)
        with pytest.raises(ValueError, match="measurement"):
            checker(settings, condition)
    source = lab / "experiments" / (identity + ".py")
    source.write_bytes(source.read_bytes() + b"\n# scientific source revision\n")
    assert ext.status(ROOT, "experiment", identity) == "draft"
    with pytest.raises(ValueError, match="successful"):
        ext.publish(ROOT, "experiment", identity)
    with pytest.raises(ValueError, match="changed|source"):
        simulate(repo_root=ROOT, data_root=tmp_path / "changed", experiment_id=identity, values=values, analyse=False)


@pytest.mark.parametrize("values", [{"frequencies_cpd": "nan"}, {"frequencies_cpd": "2,2"},
    {"frequencies_cpd": "0.49"}, {"frequencies_cpd": "33"}, {"frequencies_cpd": "2,"},
    {"contrast_method": "constant_stimuli", "fixed_contrasts": "-1"},
    {"starting_contrast": 1., "background_intensity": .1},
    {"threshold_reversals": 5, "reversal_termination": 2}])
def test_csf_rejects_invalid_scientific_settings(lab, values):
    spec = registry.get_experiment(CSF)
    with pytest.raises(ValueError):
        spec.normalise_values(values)


@pytest.mark.parametrize("values", [{"soa_ms": "0"}, {"soa_ms": "100"}, {"soa_ms": "-10,10"},
    {"soa_ms": "-100,100,100"}, {"soa_ms": "nan"}, {"soa_ms": "wrong"},
    {"soa_ms": "-100.5,100.5"}, {"soa_ms": "-6000,6000"}, {"max_trials": 1}])
def test_temporal_rejects_invalid_scientific_settings(lab, values):
    with pytest.raises(ValueError):
        registry.get_experiment(TEMPORAL).normalise_values(values)


def test_temporal_events_implement_signed_onset_order_and_balanced_deterministic_schedule(lab):
    author = module(TEMPORAL)
    settings = author.SPEC.field_defaults()
    schedule = author.make_conditions(settings, 137)
    assert schedule == author.make_conditions(settings, 137)
    assert schedule != author.make_conditions(settings, 138)
    assert len(schedule) == len(author.signed_soas(settings)) * settings["repetitions"]
    assert sum(c["target"] == 0 for c in schedule) == len(schedule) // 2
    for condition in schedule:
        plan = TrialTimeline(author.trial_events(settings, condition)).resolve(settings)
        onset, times = 0, {}
        for event in plan.phases:
            times[event.name] = onset
            onset += event.duration_ms
        assert times["target"] - times["cue"] == condition["soa_ms"]
        assert [p.name for p in plan.phases] == (["fixation", "target", "gap", "cue", "answer"]
            if condition["target"] == 0 else ["fixation", "cue", "gap", "target", "answer"])
        for alternative in (0, 1):
            response = {"alternative": alternative, "correct": alternative == condition["target"]}
            assert author.interpret_response(condition, response)["correct"] == response["correct"]


def test_temporal_pipeline_records_measurements_results_and_repeatable_trials(lab, tmp_path):
    values = {"soa_ms": "-100,100", "repetitions": 2}
    ready(TEMPORAL, values)
    runs = [simulate(repo_root=ROOT, data_root=tmp_path / "runs", experiment_id=TEMPORAL,
                     values=values, seed=137, observer=TeachingObserver(.65), analyse=False)[0] for _ in range(2)]
    assert runs[0].trial_log_file.read_bytes() == runs[1].trial_log_file.read_bytes()
    for run in runs:
        assert run.status == "completed" and run.accepted_trials == 4
        assert all(c.passed for c in validate_run(run.run_directory))
        rows = load_run(run.run_directory)["trials"]
        assert len(rows) == 20 and len(rows["trial_index"]) == 4
        cells = read(run, "resolved_experiment.json")["observed_temporal_accuracy"]
        assert sum(c["accepted"] for c in cells) == 4
        assert sum(c["correct"] for c in cells) == sum(int(v) for v in rows["correct"])
        assert len(read(run, "session_events.json")["events"]) == 2
        assert all(set(p["measurements"]) == set(module(TEMPORAL).MEASUREMENT_UNITS) for p in presentations(run))


@pytest.mark.parametrize("identity,method", [(CSF, "adaptive"), (CSF, "constant_stimuli"), (TEMPORAL, None)])
def test_generic_review_inspects_the_authoritative_events(lab, monkeypatch, identity, method):
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from psychophysics_lab.ui.settings_review import describe_settings
    author = module(identity)
    spec = registry.get_experiment(identity)
    settings = spec.normalise_values({"contrast_method": method} if method else {})
    original = author.trial_events
    calls = []
    def changed(settings, condition):
        calls.append(condition)
        events = original(settings, condition)
        return [replace(events[0], duration_ms=17)] + events[1:]
    monkeypatch.setattr(author, "trial_events", changed)
    result = describe_settings(spec, settings, resolve_stimuli(spec, settings, repo_root=ROOT),
                               profile=load_monitor_profiles(ROOT)["legacy_reference_display"])
    assert calls and result["trial_event_function"] == "trial_events"
    assert result["phases"][0]["duration_ms"] == 17


@pytest.mark.parametrize("identity,method", [(CSF, "adaptive"), (CSF, "constant_stimuli"), (TEMPORAL, None)])
@pytest.mark.parametrize("opening", [False, True])
def test_actual_software_phase_player_preserves_trials_and_response_keys(lab, tmp_path, monkeypatch, identity, method, opening):
    from test_stage_b_event_first import software_window
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from psychophysics_lab.researcher import RunContext
    display = software_window(monkeypatch)
    spec = registry.get_experiment(identity)
    if not opening:
        spec = replace(spec, session_start=[])
    selected = (VALUES | {"contrast_method": method, "fixed_repetitions": 1, "max_trials": 8}
                if identity == CSF else {"soa_ms": "-100,100", "repetitions": 1})
    settings = spec.normalise_values(selected | {"response_keys": "A,L"})
    profile = replace(load_monitor_profiles(ROOT)["legacy_reference_display"], expected_resolution_px=display.resolution)
    folder = tmp_path / "software_display"
    folder.mkdir()
    run = RunContext(settings, profile, spec, folder, seed=137, data_kind="uncalibrated_presentation_test",
                     stimulus_snapshots=resolve_stimuli(spec, settings, repo_root=ROOT))
    try:
        spec.procedure(run)
    finally:
        run.close()
    expected = (8 if method == "adaptive" else 4) if identity == CSF else 2
    assert run.accepted_trials == expected
    with (folder / "trials.tsv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert len(rows) == expected and all(row["response_key"] == "A" for row in rows)
    assert all(int(row["participant_response"]) == 0 for row in rows)
    assert (folder / "session_events.json").exists() == opening
    if opening:
        trace = json.loads((folder / "session_events.json").read_text(encoding="utf-8"))
        assert len(trace["events"]) == 2 and not any("response" in e for e in trace["events"])


@pytest.mark.parametrize("identity", [CSF, TEMPORAL])
def test_actual_phase_player_escape_before_trial_one(lab, tmp_path, monkeypatch, identity):
    from test_stage_b_event_first import software_window
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from psychophysics_lab.researcher import RunContext, ParticipantAbort
    display = software_window(monkeypatch, escape=True)
    spec = registry.get_experiment(identity)
    settings = spec.normalise_values(VALUES if identity == CSF else {})
    profile = replace(load_monitor_profiles(ROOT)["legacy_reference_display"], expected_resolution_px=display.resolution)
    folder = tmp_path / "software_abort"
    folder.mkdir()
    run = RunContext(settings, profile, spec, folder, seed=137, data_kind="uncalibrated_presentation_test",
                     stimulus_snapshots=resolve_stimuli(spec, settings, repo_root=ROOT))
    try:
        with pytest.raises(ParticipantAbort):
            spec.procedure(run)
        assert run.accepted_trials == 0
    finally:
        run.close()


def test_reference_example_has_no_official_source_dependency_or_hash_guard(lab, monkeypatch):
    author = module(CSF)
    source = Path(author.__file__).read_text(encoding="utf-8")
    assert "REFERENCE_SHA256" not in source
    assert "reference." not in source
    imports = [n.module or "" for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)]
    assert not any(name.startswith("psychophysics_lab.experiments") for name in imports)
    def forbidden(*args, **kwargs):
        raise AssertionError("Official experiment callback must not be invoked")
    for name in ("initialise_experiment", "prepare_stimuli", "trial_record", "fixed_trial_record", "make_fixed_schedule", "validate_settings"):
        monkeypatch.setattr(reference, name, forbidden)
    settings = author.SPEC.normalise_values(VALUES)
    assert len(author.make_conditions(settings)) == 4
    assert author.fixed_conditions(settings, 137)
    ready(CSF, VALUES)


def test_csf_response_ceiling_retains_incomplete_reference_result(lab, tmp_path):
    ready(CSF, VALUES)
    selected = VALUES | {"max_trials": 2, "contrast_method": "adaptive"}
    runs = [simulate(repo_root=ROOT, data_root=tmp_path / "ceiling", experiment_id=identity,
                     values=selected, seed=137, observer=TeachingObserver(1.), analyse=False)[0]
            for identity in ("contrast_sensitivity", CSF)]
    assert runs[0].accepted_trials == runs[1].accepted_trials == 2
    assert runs[0].status == runs[1].status != "completed"
    assert runs[0].trial_log_file.read_bytes() == runs[1].trial_log_file.read_bytes()
    assert read(runs[0], "adaptive_history.json") == read(runs[1], "adaptive_history.json")
    assert read(runs[0], "primary_thresholds.json") == read(runs[1], "primary_thresholds.json")


@pytest.mark.parametrize("identity", [CSF, TEMPORAL])
def test_derived_export_has_units_and_never_changes_or_overwrites_saved_data(lab, tmp_path, identity):
    values = VALUES | {"contrast_method": "constant_stimuli", "fixed_repetitions": 1} if identity == CSF else {"soa_ms": "-100,100", "repetitions": 1}
    ready(identity, values)
    run, _ = simulate(repo_root=ROOT, data_root=tmp_path / "runs", experiment_id=identity,
                      values=values, seed=137, observer=TeachingObserver(.65), analyse=False)
    original = {p.relative_to(run.run_directory): p.read_bytes() for p in run.run_directory.rglob("*") if p.is_file()}
    spec = importlib.util.spec_from_file_location("measurement_export", ROOT / "examples/scientist_first/export_measurements.py")
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    destination = tmp_path / "derived.tsv"
    assert exporter.export_measurements(run.run_directory, destination) == destination
    with destination.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    assert len(rows) == run.accepted_trials + 1
    assert all("[" in header and "]" in header for header in rows[0])
    with pytest.raises(FileExistsError):
        exporter.export_measurements(run.run_directory, destination)
    with pytest.raises(ValueError, match="outside"):
        exporter.export_measurements(run.run_directory, run.run_directory / "derived.tsv")
    assert original == {p.relative_to(run.run_directory): p.read_bytes() for p in run.run_directory.rglob("*") if p.is_file()}
