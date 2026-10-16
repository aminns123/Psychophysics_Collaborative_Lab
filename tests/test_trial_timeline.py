"""Public chronological contract, former ellipse state-loop and CSF parity."""
from dataclasses import replace
import json
from pathlib import Path
import pytest

from psychophysics_lab.core.timeline import Phase, TrialTimeline, load_timeline
from psychophysics_lab.experiments.registry import get_experiment, register_experiment
from psychophysics_lab.config.stimulus_parameters import document_for, snapshot
from psychophysics_lab.stimuli.registry import get_stimulus
from scripts.validate_run import validate_run
from simulations.run import simulate

ROOT = Path(__file__).resolve().parents[1]


def test_ordered_json_phases_resolve_runtime_timings_and_reject_unbound_slots(tmp_path):
    spec = get_experiment("orientation_task")
    doc = ROOT / "configs/experiments/orientation_task.json"
    timeline = load_timeline(doc, timings=spec.field_defaults(), slots={"target"})
    assert [p.name for p in timeline.phases] == ["fixation", "target", "interval", "answer"]
    assert [p.duration_ms for p in timeline.phases] == [500, 200, 150, 0]
    assert timeline.phases[-1].kind == "response"
    changed = spec.field_defaults() | {"fixation_ms": 120, "stimulus_ms": 25}
    assert [p.duration_ms for p in load_timeline(doc, timings=changed, slots={"target"}).phases[:2]] == [120, 25]
    with pytest.raises(ValueError, match="undeclared"):
        load_timeline(doc, timings=changed, slots={"comparison"})
    with pytest.raises(ValueError, match="positive duration"):
        load_timeline(doc, timings=changed | {"fixation_ms": 0}, slots={"target"})


@pytest.mark.parametrize("invalid", [
    [Phase("fixate", "show", duration_ms=10)],
    [Phase("answer", "response"), Phase("stim", "show", duration_ms=10)],
    [Phase("first", "response"), Phase("second", "response")],
    [Phase("same", "show", duration_ms=5), Phase("same", "response")],
])
def test_invalid_trial_sequences_are_rejected(invalid):
    with pytest.raises(ValueError):
        TrialTimeline(tuple(invalid))


def test_unknown_json_fields_and_non_integer_durations_are_rejected(tmp_path):
    doc = {"schema_version": 1, "phases": [
        {"name": "stim", "kind": "show", "slot": "target", "duration_ms": 10.4},
        {"name": "answer", "kind": "response", "duration_ms": 0}]}
    path = tmp_path / "timeline.json"
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="integer"):
        load_timeline(path, slots={"target"})
    doc["phases"][0]["duration_ms"] = 10
    doc["phases"][0]["undocumented_switch"] = True
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="unknown fields"):
        load_timeline(path, slots={"target"})


def test_csf_reference_matches_existing_five_phase_queue():
    spec = get_experiment("contrast_sensitivity")
    timeline = load_timeline(ROOT / "configs/experiments/contrast_sensitivity.json",
                             timings=spec.field_defaults(), slots=spec.stimulus_slots)
    assert [(p.name, p.kind, p.duration_ms) for p in timeline.phases] == [
        ("fixation", "show", 250), ("new_condition", "show", 250),
        ("stimuli", "show", 200), ("interval", "show", 250),
        ("response", "response", 0)]
    # Compatibility contract: these phase role names also drive the original
    # dynamic CSF trial objects, rather than rewriting their OpenGL renderer.
    source = (ROOT / "Experiments/contrast_sensitivity_function.py").read_text()
    assert "existing_trials[phase.name] for phase in timeline.phases" in source
    assert '"new_condition": fixate_state_new_condition' in source
    assert '"response": fixateRESPONSE' in source


def test_timed_sequence_simulates_saves_phases_and_keeps_response_metadata(tmp_path):
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id="orientation_task",
                            values={"trial_count": 2, "fixation_ms": 100, "stimulus_ms": 40,
                                    "interval_ms": 50, "response_keys": "LEFT,RIGHT"})
    assert artifacts.status == "completed" and artifacts.accepted_trials == 2
    assert all(c.passed for c in validate_run(artifacts.run_directory))
    presentations = json.loads((artifacts.run_directory / "trial_presentations.json").read_text())
    assert len(presentations["trials"]) == 2
    for record in presentations["trials"]:
        phases = record["phase_events"]
        assert [p["name"] for p in phases] == ["fixation", "target", "interval", "answer"]
        assert [p["planned_onset_ms"] for p in phases] == [0, 100, 140, 190]
        assert all("simulated" in p["timing_basis"] for p in phases)
        assert record["reaction_time_s"] >= 0
        assert record["stimulus_id"] == "teaching_gabor"
    assert (artifacts.run_directory / "procedure_lifecycle.json").exists()


def test_two_stimuli_can_appear_in_order_and_record_custom_measurement(tmp_path, monkeypatch):
    from psychophysics_lab.experiments import registry
    monkeypatch.setattr(registry, "_REGISTRY", dict(registry._REGISTRY))
    def procedure(run):
        run.initialise(expected_trials=1, resolution={"task": "test sequential patch selection"})
        timeline = TrialTimeline((Phase("first", "show", "target", 20),
                                  Phase("second", "show", "comparison", 30),
                                  Phase("respond", "response", None, 0)))
        a = run.stimulus_parameters("target")
        b = run.stimulus_parameters("comparison")
        run.play_trial(timeline, target=0, condition="pair", parameters_by_slot={"target": a, "comparison": b},
                       measurements={"probe_offset_deg": 0.5})
        run.complete()
    base = get_experiment("orientation_task")
    spec = replace(base, id="sequential_stimuli", procedure=procedure, source_paths=(),
                   stimulus_slots={"target": "orientation_patch", "comparison": "orientation_patch"},
                   stimulus_defaults={"target": "teaching_gabor", "comparison": "teaching_gabor"})
    register_experiment(spec)
    stimulus = get_stimulus("teaching_gabor")
    d = document_for(stimulus)
    selected = {"target": snapshot(d, file_identity="target.json"),
                "comparison": snapshot(document_for(stimulus, d["parameters"] | {"orientation_deg": 70.}), file_identity="comparison.json")}
    artifacts, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", experiment_id=spec.id,
                            values={"trial_count": 1}, stimulus_snapshots=selected)
    assert all(c.passed for c in validate_run(artifacts.run_directory))
    record = json.loads((artifacts.run_directory / "trial_presentations.json").read_text())["trials"][0]
    assert [x["slot"] for x in record["phase_events"]] == ["target", "comparison", None]
    assert record["slot"] == "comparison"
    assert record["measurements"]["probe_offset_deg"] == .5


def test_authoring_screen_shows_create_buttons_and_timeline_file():
    from psychophysics_lab.ui.setup import _source_inventory
    spec = get_experiment("orientation_task")
    roles = dict(_source_inventory(ROOT, spec))
    assert roles["Trial timeline JSON"].name == "orientation_task.json"
    assert dict(_source_inventory(ROOT, get_experiment("contrast_sensitivity")))["Trial timeline JSON"].name == "contrast_sensitivity.json"


def test_build_buttons_scaffold_scientific_files_without_editor_changes(tmp_path, monkeypatch):
    import asyncio
    from textual.widgets import Input, Button
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentsScreen, StimuliScreen
    import psychophysics_lab.scaffold as authoring
    calls = []
    def scaffold_fake(root, name, *, kind):
        calls.append((name, kind))
        # The launcher is intentionally mocked: no files are written in this test.
        return (ROOT / "src/psychophysics_lab/experiments/orientation_task.py",)
    monkeypatch.setattr(authoring, "scaffold", scaffold_fake)
    # Inspecting a source file also goes through one public TUI method.
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        seen = []
        monkeypatch.setattr(app, "inspect_source", lambda source: seen.append(source))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.click("#nav-experiments")
            await pilot.pause()
            assert isinstance(app.screen, ExperimentsScreen)
            app.screen.query_one("#new-experiment-name", Input).value = "new_task"
            app.screen.query_one("#build-new-experiment", Button).scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click("#build-new-experiment")
            await pilot.pause()
            await pilot.click("#nav-stimuli")
            await pilot.pause()
            assert isinstance(app.screen, StimuliScreen)
            app.screen.query_one("#new-stimulus-name", Input).value = "new_patch"
            app.screen.query_one("#build-new-stimulus", Button).scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click("#build-new-stimulus")
            await pilot.pause()
        assert len(seen) == 2
    asyncio.run(scenario())
    assert calls == [("new_task", "experiment"), ("new_patch", "stimulus")]
