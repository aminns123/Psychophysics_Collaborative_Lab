"""One-file authoring, backward compatibility and simple PhD-style beep tests."""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.core.timeline import Beep, Show, CollectResponse, TrialTimeline
from psychophysics_lab.core.trial_execution import VirtualPresentation, execute_timeline
from psychophysics_lab.core.presentation import Response
from psychophysics_lab.stimulus_library import (
    FixationCross, VerticalLineProbe, ExampleWhiteLine, TeachingGabor, ComposedScene,
    ResearcherVerticalLine
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("identity,klass", [
    ("fixation_cross", FixationCross), ("vertical_line_probe", VerticalLineProbe),
    ("example_stimulus", ExampleWhiteLine), ("teaching_gabor", TeachingGabor),
    ("composed_scene", ComposedScene),
    ("new_probe_vertical_line", ResearcherVerticalLine),
])
def test_registered_stimulus_science_is_in_one_file(identity, klass):
    from psychophysics_lab.stimuli.registry import get_stimulus
    # Historical researcher modules can be excluded by the published-source
    # fingerprint gate. Their class definitions are still testable without
    # bypassing the gate or silently marking an untested revision Ready.
    spec = klass.SPEC if identity == "new_probe_vertical_line" else get_stimulus(identity)
    assert spec is klass.SPEC
    assert spec.source_path == "src/psychophysics_lab/stimulus_library.py"
    assert callable(klass.render)
    default = json.loads((ROOT / spec.default_config).read_text())["parameters"]
    points = np.linspace(-0.2, .2, 9)
    x, y = np.meshgrid(points, points)
    np.testing.assert_array_equal(spec.render(default, x, y), klass.render(default, x, y))


def test_beep_is_optional_and_validated():
    normal = Show("silent", slot="probe", duration=200)
    assert "beep" not in normal.to_dict()
    cue = Beep(450, 30)
    first = Show("fixation", slot="probe", duration=100, beep=cue)
    second = CollectResponse(actions=("left", "right"), beep=Beep(550, 40))
    assert first.to_dict()["beep_trigger"] == "display_onset"
    assert second.to_dict()["beep_trigger"] == "accepted_response"
    with pytest.raises(ValueError):
        Beep(10, 30)
    with pytest.raises(TypeError):
        Show("bad", duration=100, beep="beep")


def test_virtual_audio_is_recorded_but_never_played(monkeypatch):
    from psychophysics_lab.core import tone
    monkeypatch.setattr(tone, "request_beep", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("real audio")))
    timeline = TrialTimeline((
        Show("blank_tone", duration=50, beep=Beep(450, 20)),
        CollectResponse(actions=("left", "right"), beep=Beep(550, 30)),
    ))
    events = []
    backend = VirtualPresentation(Response(0, "F", .25))
    execute_timeline(timeline, backend, events, lambda *a: None)
    assert [e["audio"]["trigger"] for e in events] == ["display_onset", "accepted_response"]
    assert events[0]["audio"]["virtual_request_ms"] == 0
    assert events[1]["audio"]["virtual_request_ms"] == 300
    assert all("no sound generated" in event["audio"]["output"] for event in events)


def test_beep_is_in_scientific_api():
    from psychophysics_lab.researcher import Beep as PublicBeep
    assert PublicBeep is Beep


def test_only_one_authoritative_stimulus_python_file():
    for name in ("fixation_cross", "vertical_line_probe", "example_stimulus",
                 "teaching_gabor", "composed_scene", "new_probe_vertical_line"):
        assert not (ROOT / "src/psychophysics_lab/stimuli" / (name + ".py")).exists()
    assert (ROOT / "src/psychophysics_lab/stimulus_library.py").is_file()


def test_phd_beep_uses_no_audio_when_not_requested():
    from psychophysics_lab.core.timeline import Phase
    assert Show("stim", duration=40).beep is None
    assert CollectResponse(actions=("yes", "no")).beep is None


def test_legacy_timeline_json_beep_is_explicit(tmp_path):
    from psychophysics_lab.core.timeline import load_timeline
    document = {"schema_version": 1, "phases": [
        {"name": "fixation", "kind": "show", "slot": "target", "duration_ms": 100,
         "beep": {"frequency_hz": 450, "duration_ms": 35}},
        {"name": "answer", "kind": "response", "slot": "target", "duration_ms": 0,
         "beep": {"frequency_hz": 550, "duration_ms": 35}},
    ]}
    file = tmp_path / "timeline.json"
    file.write_text(json.dumps(document))
    timeline = load_timeline(file, slots={"target"})
    assert [phase.beep.frequency_hz for phase in timeline.phases] == [450, 550]
    document["phases"][0]["beep"] = {"frequency_hz": 0, "duration_ms": 20}
    file.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="frequency"):
        load_timeline(file, slots={"target"})


def test_new_single_file_class_is_discoverable_and_needs_no_json(monkeypatch):
    from dataclasses import replace
    from psychophysics_lab.stimulus_library import LibraryStimulus, library_stimulus_specs
    from psychophysics_lab.experiments.spec import ConfigField
    from psychophysics_lab.stimuli import registry as stimuli
    from psychophysics_lab.stimuli.registry import StimulusSpec
    from psychophysics_lab.experiments.registry import get_experiment
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli

    class MyNewLine(LibraryStimulus):
        PARAMETERS = (ConfigField("size_deg", "Patch diameter", "float",
                                  1.0, minimum=0.1),)

        @staticmethod
        def render(parameters, x_deg, y_deg):
            return np.full_like(x_deg, .5, dtype=float)

        SPEC = StimulusSpec(
            "one_file_test_line", "My one-file line", "Test-only renderer",
            "src/psychophysics_lab/stimulus_library.py", parameters=PARAMETERS,
            family="simple_line", render=render.__func__, default_config="",
            calibration_requirements=("geometry",),
        )

    assert MyNewLine.SPEC in library_stimulus_specs()
    monkeypatch.setitem(stimuli._REGISTRY, MyNewLine.SPEC.id, MyNewLine.SPEC)
    experiment = replace(get_experiment("example_experiment"),
                         stimulus_defaults={"target": MyNewLine.SPEC.id})
    resolved = resolve_stimuli(experiment, experiment.field_defaults(), repo_root=ROOT)
    assert resolved["target"]["file_identity"] == "library_defaults"
    assert resolved["target"]["document"]["parameters"] == {"size_deg": 1.0}
