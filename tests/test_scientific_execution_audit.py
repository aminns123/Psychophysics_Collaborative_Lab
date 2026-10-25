"""Independent response histories, physical geometry and actual upload-path tests."""
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from psychophysics_lab.adaptive import AdaptiveRun, StaircaseConfig, Step
from psychophysics_lab.config.stimulus_parameters import document_for
from psychophysics_lab.core import presentation as display
from psychophysics_lab.core.timeline import Show, CollectResponse, TrialTimeline, Stimulus
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.stimuli.registry import get_stimulus

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('n_down',range(1,5))
@pytest.mark.parametrize('n_up',range(1,4))
@pytest.mark.parametrize('intro',[0,4])
def test_consecutive_rules_and_reversals_match_independent_response_oracle(n_down,n_up,intro):
    for seed in range(5):
        algorithm=AdaptiveRun({1:StaircaseConfig(n_down,n_up,1000,intro)},1000,starting_values={1:.2})
        value=.2
        correct_streak=wrong_streak=reversals=direction=intro_count=0
        intro_active=bool(intro)
        rng=random.Random(seed)
        for _ in range(100):
            correct=rng.random()<.65
            if correct:
                wrong_streak=0
                correct_streak+=1
                limit=1 if intro_active else n_down
                expected=Step.DOWN if correct_streak==limit else Step.HOLD
                if expected==Step.DOWN: correct_streak=0
            else:
                correct_streak=0
                wrong_streak+=1
                expected=Step.UP if wrong_streak==n_up else Step.HOLD
                if expected==Step.UP: wrong_streak=0
            if intro_active:
                intro_count+=1
                intro_active=correct and intro_count<intro
            proposed=min(.9,value*1.6) if expected==Step.UP else value*.7 if expected==Step.DOWN else value
            movement=(proposed>value)-(proposed<value)
            if movement:
                reversals+=int(bool(direction) and direction!=movement)
                direction=movement
            step,actual=algorithm.respond(1,correct,lambda _:proposed)
            assert step==expected and actual==proposed
            assert algorithm.states[1].reversal_count==reversals
            value=proposed


def test_initial_presentations_count_the_first_reversal_and_legacy_remains_unchanged():
    for initial,expected in [({1:.2},1),(None,0)]:
        algorithm=AdaptiveRun({1:StaircaseConfig(1,1,1)},10,starting_values=initial)
        algorithm.respond(1,True,lambda step:.1)
        algorithm.respond(1,False,lambda step:.2)
        assert algorithm.states[1].reversal_count==expected
        assert (algorithm.status=='completed')==bool(expected)
    # Flat saturated holds never create a direction or a reversal.
    algorithm=AdaptiveRun({1:StaircaseConfig(1,1,3)},10,starting_values={1:.5})
    for correct,value in [(False,.5),(True,.4),(False,.5),(False,.5)]:
        algorithm.respond(1,correct,lambda step:value)
    assert algorithm.states[1].reversal_count==1


@pytest.mark.parametrize('value',[0.,5e-324,1e-320,1e-4,.2,1.])
@pytest.mark.parametrize('down,up',[(.8,1.25),(1.,1.),(1e-6,1e308)])
def test_orientation_updates_respect_direction_and_preserve_hold(value,down,up):
    from psychophysics_lab.experiments.orientation_adaptive import next_contrast
    state={'contrast':value,'down_factor':down,'up_factor':up}
    assert next_contrast(state,{},Step.HOLD)==value
    assert 0<=next_contrast(state,{},Step.DOWN)<=value
    assert value<=next_contrast(state,{},Step.UP)<=1
    if value==1e-4 and down==.8:
        assert next_contrast(state,{},Step.DOWN)==pytest.approx(8e-5)
        assert next_contrast(state,{},Step.UP)==pytest.approx(.000125)


@dataclass
class AlternatingObserver:
    calls:int=0
    def probability_correct(self,condition,state,stimuli):
        self.calls+=1
        return float(self.calls%2==1)


@pytest.mark.parametrize('identity',['line_position_baseline','line_position_flanker','ellipse_centre','ellipse_major_axis','contrast_sensitivity'])
def test_modern_first_reversal_matches_presented_visual_strength_and_primary_result(tmp_path,monkeypatch,identity):
    from simulations.run import simulate
    from psychophysics_lab.researcher import RunContext
    values={'staircases_per_condition':1,'max_trials':12,'n_down':1,'n_up':1,
        'reversal_termination':1,'threshold_reversals':1,'initial_one_down_limit':0,
        'logUNIT_DW':.1,'logUNIT_UP':.1}
    if identity.startswith('line_'):
        values.update(positions_deg='0',probe_vertical_offset_deg=.5,starting_probe_intensity=.7)
        if identity.endswith('flanker'): values['flanker_cpd']=2.
    elif identity.startswith('ellipse_'):
        values.update(ring_increment=.1,aspect_ratios='1',starting_probe_intensity=.7)
        if identity.endswith('axis'): values.update(positions_deg='0',ring_conditions='ring_only')
    else:
        values.update(frequencies_cpd='2',starting_contrast=.2)
    captured=[]
    original=RunContext.trial
    def capture(run,timeline,**kwargs):
        captured.append((kwargs['target'],kwargs['parameters_by_slot']))
        return original(run,timeline,**kwargs)
    monkeypatch.setattr(RunContext,'trial',capture)
    result,_=simulate(repo_root=ROOT,data_root=tmp_path,experiment_id=identity,values=values,
                      observer=AlternatingObserver(),analyse=False)
    assert result.status=='completed' and result.accepted_trials==2
    with result.trial_log_file.open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream,delimiter='\t'))
    assert [row['reversal'] for row in rows]==['0','1']
    expected=.2*10**(-.1)
    assert float(rows[1]['presented_display_contrast'])==pytest.approx(expected)
    for row,(target,stimuli) in zip(rows,captured):
        strength=float(row['presented_display_contrast'])
        assert float(row['next_display_contrast'])==pytest.approx(strength*10**(-.1 if row['correct']=='1' else .1))
        if identity=='contrast_sensitivity':
            assert stimuli['grating']['contrast']==pytest.approx(strength)
        else:
            assert stimuli['first']['contrast']==pytest.approx(strength)
            if identity.startswith('line_'):
                assert math.copysign(1,stimuli['first']['probe_y_deg'])==(1 if target==0 else -1)
            else:
                assert stimuli['first']['probe_present']==(target==0)
                assert stimuli['second']['probe_present']==(target==1)
    primary=json.loads((result.run_directory/'primary_thresholds.json').read_text(encoding='utf-8'))
    assert next(iter(primary['staircase_thresholds'].values()))==pytest.approx(expected)
    adaptive=json.loads((result.run_directory/'adaptive_session.json').read_text(encoding='utf-8'))
    assert adaptive['reversal_convention']=='starting_presentation'


def fake_display(monkeypatch):
    arrays=[]
    class Texture:
        def __init__(self,array):
            self.array=array.copy()
            arrays.append(self.array)
        def delete(self): pass
    monkeypatch.setitem(sys.modules,'pyglet',SimpleNamespace())
    monkeypatch.setattr(display,'FloatingTexture',Texture)
    presentation=object.__new__(display.Presentation)
    presentation.profile=SimpleNamespace(physical_width_m=.6,physical_height_m=.34,
        viewing_distance_m=.5,geometry_status='unverified')
    presentation.resolution=(2560,1440)
    return presentation,arrays


def test_actual_prepare_preserves_low_contrast_levels_in_float_upload(monkeypatch):
    presentation,arrays=fake_display(monkeypatch)
    stimulus=get_stimulus('teaching_gabor')
    params=document_for(stimulus)['parameters']
    timeline=TrialTimeline((Show('target',slot='target',duration=100),CollectResponse(actions=('negative','positive'))))
    for strength in (.0001,.0002):
        presentation.prepare(timeline,{'target':(stimulus.id,params|{'contrast':strength})})
    assert stimulus.floating_raster
    assert len(arrays)==2 and all(array.dtype==np.float32 for array in arrays)
    assert not np.array_equal(*arrays)
    # PNG conversion remains explicitly 8-bit and is not a precision check.
    assert np.array_equal(display.render_pixels(stimulus,params|{'contrast':.0001}),
                          display.render_pixels(stimulus,params|{'contrast':.0002}))


@pytest.mark.parametrize('width,height,distance,resolution',[(.6,.34,.5,(2560,1440)),(.52,.29,.75,(1920,1080))])
@pytest.mark.parametrize('centre',[(0,0),(15,0),(-15,0),(0,5),(0,-5),(10,5)])
def test_off_axis_aperture_edges_match_independent_flat_screen_equations(width,height,distance,resolution,centre):
    profile=SimpleNamespace(physical_width_m=width,physical_height_m=height,viewing_distance_m=distance,
                            geometry_status='unverified')
    stimulus=get_stimulus('detection_scene')
    params=document_for(stimulus)['parameters']|{'size_deg':8.}
    placement=Stimulus('target',*centre)
    pixels=display.validate_geometry(profile,resolution,stimulus,params,placement=placement)
    origin=display.placement_pixels(profile,resolution,pixels,placement,extent_deg=8.)
    for midpoint,start,count,extent,limit in zip(centre,origin,pixels,(width,height),resolution):
        pitch=extent/limit
        for pixel,expected in [(start,midpoint-4),(start+count,midpoint+4)]:
            angle=math.degrees(math.atan((pixel-limit/2)*pitch/distance))
            assert abs(angle-expected)<=math.degrees(math.atan(pitch/distance))


def test_actual_prepare_keeps_requested_target_near_off_axis_aperture_edge(monkeypatch):
    presentation,arrays=fake_display(monkeypatch)
    stimulus=get_stimulus('detection_scene')
    params=document_for(stimulus)['parameters']|{'size_deg':8.,'probe_x_deg':3.9,
        'probe_y_deg':1.,'probe_width_deg':.05,'probe_length_deg':.5,'contrast':.1}
    timeline=TrialTimeline((Show('probe',stimuli=(Stimulus('target',15,0),),duration=100),
                            CollectResponse(actions=('left','right'))))
    for present in (False,True):
        presentation.prepare(timeline,{'target':(stimulus.id,params|{'probe_present':present})})
    assert np.any(arrays[1]>arrays[0])  # Old aperture ended at local +3.67°.
    geometry=presentation._phase_geometry['probe'][0]
    assert geometry['requested_centre_deg']==[15,0]
    assert geometry['requested_extent_deg']==8.
    assert geometry['raster_px'][0]>298


@pytest.mark.parametrize('background',[0.,.5,.9])
@pytest.mark.parametrize('length,width',[(.133,.013),(1.2,.1)])
def test_requested_probe_intensity_size_and_position_match_independent_area(background,length,width):
    stimulus=get_stimulus('detection_scene')
    params=document_for(stimulus)['parameters']|{'size_deg':4.,'probe_x_deg':1.,'probe_y_deg':.5,
        'probe_length_deg':length,'probe_width_deg':width,'background':background,'contrast':.05}
    first=display.render_values(stimulus,params,pixels=(512,512))
    absent=display.render_values(stimulus,params|{'probe_present':False},pixels=(512,512))
    delta=first-absent
    axis=(np.arange(512)+.5-256)*4/512
    x,y=np.meshgrid(axis,axis)
    assert delta.sum()*(4/512)**2==pytest.approx(length*width*.05,rel=1e-10)
    assert float((delta*x).sum()/delta.sum())==pytest.approx(1.,abs=4/512)
    assert float((delta*y).sum()/delta.sum())==pytest.approx(.5,abs=4/512)
    assert first.min()>=0 and first.max()<=1


@pytest.mark.parametrize('value',[0.,5e-324,1e-320,sys.float_info.min,1e-12,.2,1.])
@pytest.mark.parametrize('exponent',[-1000.,-.3,-.000001,0.,.000001,.3,1000.])
def test_bounded_log_updates_preserve_direction_even_at_numeric_extremes(value,exponent):
    from psychophysics_lab.adaptive.steps import bounded_log_step
    updated=bounded_log_step(value,exponent,maximum=1.)
    assert math.isfinite(updated) and 0<=updated<=1
    if exponent<0: assert updated<=value
    elif exponent>0: assert updated>=value
    else: assert updated==value


@pytest.mark.parametrize('threshold',[5e-324,.02,1e308])
def test_virtual_observer_is_monotonic_across_its_valid_numeric_range(threshold):
    from simulations.psychometric import PsychometricObserver
    observer=PsychometricObserver(threshold=threshold)
    probabilities=[observer.probability(value) for value in (0.,5e-324,1e-320,.0001,.02,1.,1e308)]
    assert all(math.isfinite(p) and .5<=p<=.98 for p in probabilities)
    assert probabilities==sorted(probabilities)
    assert observer.probability(threshold)==pytest.approx(observer.threshold_probability)


@pytest.mark.parametrize('identity',['line_position_baseline','line_position_flanker','ellipse_centre','ellipse_major_axis','contrast_sensitivity'])
def test_step_accuracy_metadata_uses_a_stable_ratio_for_large_finite_steps(identity):
    from psychophysics_lab.ui.settings_review import _PlanningContext
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    spec=get_experiment(identity)
    raw={'logUNIT_UP':1e308,'logUNIT_DW':1e308,'n_down':4,'n_up':1}
    if identity.startswith('line_'):
        raw.update(positions_deg='0',probe_vertical_offset_deg=.5)
        if identity.endswith('flanker'):raw['flanker_cpd']=2.
    elif identity.startswith('ellipse_'):raw.update(ring_increment=.1)
    values=spec.normalise_values(raw)
    run=_PlanningContext(values,None,spec,Path(),synthetic=True,
        stimulus_snapshots=resolve_stimuli(spec,values,repo_root=ROOT))
    module=sys.modules[spec.procedure.__module__]
    module.initialise_experiment(run,module.make_conditions(values))
    assert run.resolution['asymptotic_accuracy_target']==pytest.approx(.5**.25)
    from simulations.recovery import operating_point
    assert operating_point(4,1,1e308,1e308)==pytest.approx(.5**.25)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 0.0, -0.1, True, "0.3"])
@pytest.mark.parametrize("step_name", ["log_up", "log_down"])
def test_recovery_operating_point_rejects_invalid_step_values(step_name, bad):
    from simulations.recovery import operating_point
    settings = {"n_down": 4, "n_up": 1, "log_up": .36, "log_down": .30294}
    settings[step_name] = bad
    with pytest.raises(ValueError, match="finite positive"):
        operating_point(**settings)


@pytest.mark.parametrize("n_down,n_up", [(True,1), (2,True), (2,1.0), (2,2), (0,1), (2.5,1)])
def test_recovery_operating_point_requires_integer_n_down_one_up(n_down, n_up):
    from simulations.recovery import operating_point
    with pytest.raises(ValueError):
        operating_point(n_down,n_up,.36,.30294)


@pytest.mark.parametrize("invalid", [
    {"seeds": True}, {"seeds": 2.5}, {"seeds": 1},
    {"reversal_limit": 0}, {"reversal_limit": float("inf")},
    {"retained": 0}, {"retained": 11}, {"retained": True},
    {"repeats": 0}, {"repeats": 1.5},
    {"ceiling": 0}, {"ceiling": float("nan")},
    {"threshold": float("nan")}, {"threshold": float("inf")},
    {"lapse": float("nan")}, {"lapse": 1.0},
    {"maximum": float("inf")}, {"maximum": 0.0},
])
def test_recovery_rejects_invalid_settings_before_running_any_seed(invalid):
    from simulations.recovery import recover
    with pytest.raises(ValueError):
        recover(**invalid)


def test_recovery_operating_point_unchanged_for_normal_and_large_finite_steps():
    from simulations.recovery import operating_point
    import math
    usual = operating_point(4,1,.36,.30294)
    expected = (.36 / (.36 + .30294)) ** .25
    assert usual == pytest.approx(expected)
    assert operating_point(4,1,1e308,1e308) == pytest.approx(.5 ** .25)
    assert math.isfinite(usual)
