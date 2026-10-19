"""Replacement coverage for supported flanker experiments after retired pipelines were removed.

Historic numeric fixtures and executable adapters remain available in old Git
revisions; new experiments use their public authored files and shared stimulus.
"""
import pytest
from types import SimpleNamespace

from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.experiments import line_position_flanker as flanker
from psychophysics_lab.stimulus_library import DetectionScene


@pytest.mark.parametrize("retired", [
    "csf_thesis", "legacy_contrast_sensitivity",
    "base_flanker", "indirect_flanker", "ellipse_2d",
])
def test_retired_experiment_ids_are_not_launchable(retired):
    with pytest.raises(KeyError):
        get_experiment(retired)


def test_supported_flanker_trial_phase_order_and_response_mapping():
    values = flanker.SPEC.normalise_values(flanker.SPEC.field_defaults() | {
        "fixation_ms": 340, "stimulus_ms": 180,
        "flanker_cpd": 3.4, "auditory_cues": False,
    })
    phases = flanker.make_trial(values, {}).resolve(values).phases
    assert [(p.name, p.duration_ms) for p in phases] == [
        ("fixation", 340), ("probe", 180), ("answer", 0)
    ]
    assert phases[-1].actions == ("above", "below")
    assert all(p.beep is None for p in phases)
    assert flanker.interpret_response({"target":0},{"alternative":0,"correct":True})["correct"]
    assert not flanker.interpret_response({"target":1},{"alternative":0,"correct":False})["correct"]


@pytest.mark.parametrize("cpd", [0.25, 1., 3.75, 12.])
def test_flanker_frequency_is_an_independent_researcher_setting(cpd):
    values = flanker.SPEC.normalise_values(
        flanker.SPEC.field_defaults() | {"flanker_cpd":cpd}
    )
    assert values["flanker_cpd"] == cpd
    condition = dict(flanker.make_conditions(values)[0], target=0, contrast=0.01)
    class Run:
        def __init__(self):
            self.values = values
        def stimulus_parameters(self, slot, **kwargs):
            return kwargs
    stimuli = flanker.prepare_stimuli(Run(),condition,{})
    assert stimuli["first"]["flanker_present"] is True
    assert stimuli["first"]["flanker_cpd"] == cpd
    assert stimuli["fixation"]["flanker_present"] is False


def test_flanker_nominal_full_white_probe_allowed_when_spatially_separate():
    from psychophysics_lab.experiments._internal.detection_limits import probe_limit
    import numpy as np
    p = {f.key:f.default for f in DetectionScene.PARAMETERS}
    p |= dict(background=.5, contrast=0., flanker_present=True,
              flanker_cpd=1., probe_x_deg=0., probe_y_deg=1.,
              probe_length_deg=.1, probe_width_deg=.01)
    axis=np.linspace(-7,7,351)
    grid=np.meshgrid(axis,axis)
    maximum,_=probe_limit(p,grid)
    assert maximum==pytest.approx(.5)
    visible=DetectionScene.render(p | {"contrast":maximum},*grid)
    assert visible.min()>=0 and visible.max()<=1
