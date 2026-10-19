"""Faults, data meanings and design freedom from the October repository audit."""
import asyncio
import csv
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.preflight import validate_setup, display_configuration_notes, human_requirements
from psychophysics_lab.core.presentation import render_values, Response
from psychophysics_lab.core.trial_execution import VirtualPresentation
from psychophysics_lab.data.session import read_json_records
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.researcher import CollectResponse
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def teaching_run(folder, count=1):
    return simulate(repo_root=ROOT, data_root=folder, experiment_id="orientation_task",
                    values={"trial_count": count}, analyse=False)[0]


@pytest.mark.parametrize("filename", ["trial_actions.json", "trial_presentations.json"])
def test_summary_failure_cannot_discard_accepted_responses(tmp_path, monkeypatch, filename):
    from psychophysics_lab import researcher
    original = researcher.atomic_write_json

    def fail(path, payload):
        if path.name == filename:
            raise OSError("injected summary failure")
        return original(path, payload)

    monkeypatch.setattr(researcher, "atomic_write_json", fail)
    artifacts = teaching_run(tmp_path, 2)
    assert artifacts.status == "error" and artifacts.accepted_trials == 2
    rows = list(csv.DictReader(artifacts.trial_log_file.open(), delimiter="\t"))
    journal = list(read_json_records(artifacts.run_directory / "trial_events.jsonl"))
    assert len(rows) == len(journal) == 2
    assert [r["response_key"].removeprefix("SIMULATED_") for r in rows] == [r["presentation"]["phase_events"][-1]["response"]["key"] for r in journal]
    other = "trial_presentations.json" if filename == "trial_actions.json" else "trial_actions.json"
    assert (artifacts.run_directory / other).is_file()
    manifest = json.loads(artifacts.manifest_file.read_text())
    assert manifest["persistence_errors"] and manifest["accepted_trials"] == 2


@pytest.mark.parametrize("fault", ["canonical", "journal", "lifecycle"])
def test_independent_records_survive_other_persistence_failures(tmp_path, monkeypatch, fault):
    from psychophysics_lab import researcher
    original_append = researcher.TrialLog.append
    original_write = researcher.atomic_write_json

    def append(log, row):
        if fault == "canonical":
            raise OSError("canonical fault")
        return original_append(log, row)

    def write(path, payload):
        if fault == "lifecycle" and path.name == "procedure_lifecycle.json" and payload["accepted_trials"]:
            raise OSError("lifecycle fault")
        return original_write(path, payload)

    def fail_journal(*args):
        raise OSError("journal fault")

    monkeypatch.setattr(researcher.TrialLog, "append", append)
    monkeypatch.setattr(researcher, "atomic_write_json", write)
    if fault == "journal":
        monkeypatch.setattr(researcher, "append_json_record", fail_journal)
    with pytest.raises(OSError, match=fault):
        teaching_run(tmp_path)
    run = next(tmp_path.rglob("manifest.json")).parent
    rows = list(csv.DictReader((run / "trials.tsv").open(), delimiter="\t"))
    trace = json.loads((run / "trial_actions.json").read_text())["trials"][0]
    answer = next(e["response"] for e in trace["events"] if e["kind"] == "response")
    assert answer["valid"] and answer["key"]
    assert len(rows) == (0 if fault == "canonical" else 1)
    if fault != "journal":
        assert list(read_json_records(run / "trial_events.jsonl"))[0]["trial"] == trace
    assert json.loads((run / "manifest.json").read_text())["status"] == "error"


def test_callback_error_remains_primary_when_journal_also_fails(tmp_path, monkeypatch):
    from psychophysics_lab import researcher
    from psychophysics_lab.experiments._internal import registry

    def procedure(run):
        run.initialise(expected_trials=1, resolution={"task": "callback failure"})
        from psychophysics_lab.researcher import TrialTimeline, Show, CollectResponse
        with run.trial(TrialTimeline((Show("target", slot="target", duration=1),
                                     CollectResponse(actions=("negative", "positive")))),
                       target=0, condition=0):
            raise RuntimeError("original scientific error")

    spec = replace(get_experiment("orientation_task"), id="callback_fault", procedure=procedure, source_paths=())
    monkeypatch.setitem(registry._REGISTRY, spec.id, spec)
    monkeypatch.setattr(researcher, "append_json_record", lambda *a: (_ for _ in ()).throw(OSError("journal fault")))
    with pytest.raises(RuntimeError, match="original scientific error") as caught:
        simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=spec.id, values={"trial_count": 1}, analyse=False)
    assert any("journal fault" in note for note in caught.value.__notes__)
    manifest = json.loads(next(tmp_path.rglob("manifest.json")).read_text())
    assert manifest["accepted_trials"] == 1 and manifest["status"] == "error"


def test_summary_writes_are_once_per_run_and_journal_is_durable_before_finish(tmp_path, monkeypatch):
    from psychophysics_lab import researcher
    counts = {}
    original = researcher.atomic_write_json
    original_record = researcher.RunContext.trial

    def write(path, payload):
        counts[path.name] = counts.get(path.name, 0) + 1
        return original(path, payload)

    def next_trial(run, *args, **kwargs):
        if run.accepted_trials:
            records = list(read_json_records(run.run_directory / "trial_events.jsonl"))
            assert len(records) == run.accepted_trials
            assert not (run.run_directory / "trial_actions.json").exists()
        return original_record(run, *args, **kwargs)

    monkeypatch.setattr(researcher, "atomic_write_json", write)
    monkeypatch.setattr(researcher.RunContext, "trial", next_trial)
    artifacts = teaching_run(tmp_path, 12)
    assert counts["trial_actions.json"] == counts["trial_presentations.json"] == 1
    assert len(list(read_json_records(artifacts.run_directory / "trial_events.jsonl"))) == 12
    assert all(check.passed for check in validate_run(artifacts.run_directory))


@pytest.mark.parametrize("tail", [b'{"trial":', b'{"message":"\xe2\x82'])
def test_truncated_journal_tail_is_reported_after_readable_prefix(tmp_path, tail):
    path = tmp_path / "journal.jsonl"
    path.write_bytes(b'{"trial": 1}\n' + tail)
    records = read_json_records(path)
    assert next(records) == {"trial": 1}
    with pytest.raises(ValueError, match="Incomplete final"):
        next(records)


@pytest.mark.parametrize("identity,units", [("contrast_sensitivity", "digital_peak_to_peak"),
    ("line_position_baseline", "digital_probe_increment"), ("line_position_flanker", "digital_probe_increment"),
    ("ellipse_centre", "digital_probe_increment"), ("ellipse_major_axis", "digital_probe_increment")])
def test_saved_dictionary_agrees_with_actual_scientific_strength(tmp_path, identity, units):
    values = {"max_trials": 2}
    if identity.startswith("line_"):
        values["probe_vertical_offset_deg"] = .5
        if identity.endswith("flanker"):
            values["flanker_cpd"] = 2.
    elif identity.startswith("ellipse_"):
        values["ring_increment"] = .1
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=identity, values=values, analyse=False)
    definitions = {r["column_name"]: r for r in csv.DictReader((artifacts.run_directory / "trial_data_dictionary.tsv").open(), delimiter="\t")}
    resolved = json.loads((artifacts.run_directory / "resolved_experiment.json").read_text())
    assert definitions["presented_display_contrast"]["units_or_encoding"] == units == resolved["primary_estimator"]["units"]
    assert definitions["next_display_contrast"]["units_or_encoding"] == units
    assert "0 =" in definitions["target_alternative"]["units_or_encoding"]
    records = list(read_json_records(artifacts.run_directory / "trial_events.jsonl"))
    data = records[0]["trial"]
    assert data["initial_state"]["contrast"] in [s["parameters"]["contrast"] for s in data["resolved_stimuli"].values() if "contrast" in s["parameters"]]
    assert all(c.passed for c in validate_run(artifacts.run_directory))


def test_saved_dictionary_validation_does_not_depend_on_current_experiment(tmp_path, monkeypatch):
    from psychophysics_lab.experiments._internal import registry
    from psychophysics_lab.data.trials import TRIAL_COLUMN_DEFINITIONS
    artifacts = teaching_run(tmp_path)
    monkeypatch.setitem(registry._REGISTRY, "orientation_task", replace(get_experiment("orientation_task"),
        trial_column_overrides={"participant_response": {"units_or_encoding": "a future unrelated convention"}}))
    monkeypatch.setitem(TRIAL_COLUMN_DEFINITIONS, "participant_response",
                        replace(TRIAL_COLUMN_DEFINITIONS["participant_response"], meaning="Future shared definition"))
    assert all(c.passed for c in validate_run(artifacts.run_directory))


def test_older_dictionary_is_preserved_and_validation_limits_are_explicit(tmp_path):
    artifacts = teaching_run(tmp_path)
    manifest = json.loads(artifacts.manifest_file.read_text())
    manifest.pop("trial_dictionary_overrides")
    artifacts.manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    before = (artifacts.run_directory / "trial_data_dictionary.tsv").read_bytes()
    checks = validate_run(artifacts.run_directory)
    assert all(c.passed for c in checks)
    assert "Older run" in next(c.detail for c in checks if "Trial dictionary" in c.name)
    assert (artifacts.run_directory / "trial_data_dictionary.tsv").read_bytes() == before


def test_crop_and_blank_target_choices_remain_available(tmp_path):
    from psychophysics_lab.stimuli.registry import get_stimulus
    from psychophysics_lab.config.stimulus_parameters import document_for, snapshot
    stimulus = get_stimulus("detection_scene")
    # This fixture intentionally puts the complete reference probe outside
    # the aperture; researcher-edited class defaults must not change the case.
    parameters = document_for(stimulus)["parameters"] | {
        "size_deg": .1, "probe_y_deg": .5, "probe_length_deg": .133}
    np.testing.assert_array_equal(render_values(stimulus, parameters), render_values(stimulus, parameters | {"probe_present": False}))
    spec = get_experiment("line_position_baseline")
    profile = replace(load_monitor_profiles(ROOT)["legacy_reference_display"], expected_resolution_px=(1920, 1080))
    selected = snapshot(document_for(stimulus, parameters), file_identity="intentional_crop")
    request = SetupRequest("crop_test", "new", spec.id, profile.id, spec.field_defaults() | {"probe_vertical_offset_deg": .5},
                           stimulus_snapshots={slot: selected for slot in spec.stimulus_slots})
    assert validate_setup(request, spec, profile, mode="configuration")


def test_png_preview_preserves_positive_y_up_for_array_equations(tmp_path, monkeypatch):
    from matplotlib.image import imread
    from psychophysics_lab.core import presentation
    spec = SimpleNamespace(validate_parameters=lambda p: p, extent_parameter="size_deg",
                           render=lambda p, x, y: np.where(y > 0, 1., 0.))
    monkeypatch.setattr(presentation, "get_stimulus", lambda _: spec)
    output = tmp_path / "positive_y.png"
    presentation.preview_stimulus("array_equation", {"size_deg": 2}, output)
    png = imread(output)
    assert np.all(png[0, :, :3] == 1)  # Top of PNG is positive y.
    assert np.all(png[-1, :, :3] == 0)


@pytest.mark.parametrize("identity,selected", [("contrast_sensitivity", {"frequencies_cpd": "32"}),
                                              ("line_position_flanker", {"flanker_cpd": 32., "probe_vertical_offset_deg": .5})])
def test_condition_sampling_feedback_does_not_block_editing_or_simulation(identity, selected):
    spec = get_experiment(identity)
    profile = replace(load_monitor_profiles(ROOT)["legacy_reference_display"], expected_resolution_px=(1920, 1080))
    request = SetupRequest("synthetic_1", "new", spec.id, profile.id, spec.field_defaults() | selected)
    assert validate_setup(request, spec, profile, mode="configuration")
    assert validate_setup(request, spec, profile, mode="simulation")
    assert display_configuration_notes(spec, profile, request.experiment_values)
    sampling = next(r for r in human_requirements(spec, profile, request.experiment_values) if r["key"] == "sampling")
    assert not sampling["passed"]
    with pytest.raises(ValueError, match="sampling"):
        validate_setup(request, spec, profile, mode="human")


def test_sampling_feedback_covers_the_raster_backends_lower_pixel_axis_limit():
    spec = get_experiment("contrast_sensitivity")
    profile = replace(load_monitor_profiles(ROOT)["legacy_reference_display"], expected_resolution_px=(1920, 540))
    values = spec.field_defaults() | {"frequencies_cpd": "20"}
    assert display_configuration_notes(spec, profile, values)


def test_incomplete_condition_settings_produce_feedback_without_crashing_review():
    spec = get_experiment("line_position_flanker")
    profile = replace(load_monitor_profiles(ROOT)["legacy_reference_display"], expected_resolution_px=(1920, 1080))
    assert display_configuration_notes(spec, profile, spec.field_defaults())


@pytest.mark.parametrize("reaction_time,accepted", [(.099, True), (.1, False), (.101, False)])
def test_virtual_timeout_matches_live_boundary(reaction_time, accepted):
    backend = VirtualPresentation(Response(0, "F", reaction_time))
    phase = CollectResponse(actions=("negative", "positive"), timeout=100)
    if accepted:
        assert backend.play_phase(phase, {}).reaction_time_s == reaction_time
    else:
        with pytest.raises(TimeoutError):
            backend.play_phase(phase, {})


def test_invalid_python_file_does_not_hide_valid_discoveries(tmp_path, monkeypatch):
    from psychophysics_lab.experiments._internal import contributions as loader
    from psychophysics_lab import authoring, paths
    folder = tmp_path / "experiments"
    (folder / "_internal").mkdir(parents=True)
    (folder / "unfinished.py").write_text("def unfinished(\n")
    (folder / "working.py").write_text("SPEC = object()\n")
    monkeypatch.setattr(loader, "__file__", str(folder / "_internal/contributions.py"))
    monkeypatch.setattr(authoring, "inventory", lambda root: ())
    monkeypatch.setattr(paths, "find_repo_root", lambda: tmp_path)
    with pytest.warns(RuntimeWarning, match="unfinished.py"):
        modules = loader.discover_experiment_modules()
    assert modules == ("psychophysics_lab.experiments.working",)


def test_cli_guide_survives_non_unicode_redirected_stdout(tmp_path):
    env = os.environ | {"PYTHONIOENCODING": "cp1252", "PYTHONDONTWRITEBYTECODE": "1", "PSYCOLAB_CONFIG_DIR": str(tmp_path)}
    command = [sys.executable, "-B", "-c", "from psychophysics_lab.app import _main;raise SystemExit(_main(['--learn']))"]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    assert result.returncode == 0, result.stderr.decode("cp1252", errors="replace")
    assert b"Draw the stimulus" in result.stdout


def test_import_failure_rolls_back_only_the_broken_ordinary_contribution(monkeypatch):
    from psychophysics_lab import contributions, authoring
    from psychophysics_lab.experiments._internal import contributions as loader, registry, library_builder
    from psychophysics_lab.stimuli import registry as stimuli
    from psychophysics_lab.adaptive import registry as adaptive
    source = get_experiment("orientation_task")
    for module in (registry, stimuli, adaptive):
        monkeypatch.setattr(module, "_REGISTRY", dict(module._REGISTRY))
    monkeypatch.setattr(loader, "_loaded", False)
    monkeypatch.setattr(contributions, "EXPERIMENT_MODULES", None)
    monkeypatch.setattr(contributions, "ADAPTIVE_MODULES", ())
    monkeypatch.setattr(loader, "discover_experiment_modules", lambda: ("bad", "good"))
    monkeypatch.setattr(authoring, "load_authored", lambda *a, **k: {})
    monkeypatch.setattr(library_builder, "load_library", lambda **k: {})
    original = loader.importlib.import_module

    def load(name):
        if name == "bad":
            registry._REGISTRY["partial_bad_registration"] = source
            raise RuntimeError("unfinished contribution")
        if name == "good":
            return SimpleNamespace(SPEC=replace(source, id="good"))
        return original(name)

    monkeypatch.setattr(loader.importlib, "import_module", load)
    with pytest.warns(RuntimeWarning, match="bad.py"):
        loader.load_contributions()
    assert "partial_bad_registration" not in registry._REGISTRY
    assert "good" in registry._REGISTRY and "orientation_task" in registry._REGISTRY


def test_runtime_graphics_identity_reports_loaded_module_without_importing_it(monkeypatch):
    from psychophysics_lab.core.runner import _loaded_graphics_provenance
    monkeypatch.setitem(sys.modules, "pyglet", SimpleNamespace(version="1.5.19",
        __file__=str(ROOT / "src/psychophysics_lab/_reference_csf/packages.zip/pyglet/__init__.py")))
    result = _loaded_graphics_provenance(ROOT)
    assert result["version"] == "1.5.19" and "packages.zip" in result["origin"]
    assert str(ROOT) not in json.dumps(result)


def test_review_shows_condition_limit_without_disabling_simulation(tmp_path):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen
    from psychophysics_lab.config.local import config_root, save_profile
    from textual.widgets import Static
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile = save_profile(config_root(ROOT), replace(reference, id="review_display", origin="local",
                                                       expected_resolution_px=(1920, 1080)))

    async def check():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path)
        async with app.run_test(size=(110, 45)) as pilot:
            identity = profile.id
            spec = get_experiment("contrast_sensitivity")
            request = SetupRequest("synthetic_preview", "new", spec.id, identity,
                                   spec.normalise_values(spec.field_defaults() | {"frequencies_cpd": "32"}), str(tmp_path))
            app.run_intent = "simulation"
            app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            assert app.screen.query_one("#display-configuration-notes", Static).display
            assert app.screen.readiness_report["simulation_available"]
            assert not app.screen.readiness_report["human_ready"]
    asyncio.run(check())


def test_display_cleanup_is_attempted_even_if_all_summaries_fail(tmp_path, monkeypatch):
    from psychophysics_lab.researcher import RunContext
    from psychophysics_lab import researcher
    spec = get_experiment("orientation_task")
    context = RunContext(spec.field_defaults(), None, spec, tmp_path, synthetic=True)
    context._action_trials = []
    context._presentations = []
    context._adaptive_history = []
    closed = []
    context._presentation = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(researcher, "atomic_write_json", lambda *a: (_ for _ in ()).throw(OSError("summary fault")))
    with pytest.raises(OSError, match="summary fault"):
        context.close()
    assert closed == [True] and len(context._persistence_errors) == 3
