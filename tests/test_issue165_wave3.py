"""Family source migration against exact accepted develop reference."""
import json
from pathlib import Path
import pytest
from _remaining_wave_equivalence import compare, reference, ROOT
from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
from psychophysics_lab.ui.settings_review import describe_settings
WAVE = 3
NAMES = ('contrast_sensitivity', 'contrast_sensitivity_windowed')
CASES=json.loads((ROOT/'tests/fixtures'/('issue165_wave'+str(WAVE))/'effective_cases.json').read_text())

@pytest.mark.parametrize('case',CASES,ids=lambda c:f"{c['identity']}-{c['method']}-{c['seed']}")
@pytest.mark.parametrize('opening',[False,True])
def test_frozen_complete_trials_and_every_scientific_observation(tmp_path,monkeypatch,case,opening):
    compare(tmp_path,monkeypatch,WAVE,case['identity'],case['method'],case['values'],case['seed'],opening)

@pytest.mark.parametrize('identity',NAMES)
@pytest.mark.parametrize('method',['adaptive','constant_stimuli'])
@pytest.mark.parametrize('ending',['complete','ceiling','ready','trial'])
def test_completion_ceiling_and_interruptions(tmp_path,monkeypatch,identity,method,ending):
    values=dict(contrast_method=method,frequencies_cpd='2',positions_deg='0',aspect_ratios='1',
        ring_conditions='base_only',ring_increment=.03,probe_vertical_offset_deg=.4,flanker_cpd=2.,
        staircases_per_condition=1,n_down=1,n_up=1,reversal_termination=2,threshold_reversals=1,
        max_trials=1 if ending=='ceiling' else 1000,fixed_contrasts='0,.01',fixed_repetitions=3)
    with monkeypatch.context() as patch:
        with reference(patch,WAVE,identity,False) as spec:
            values={k:v for k,v in values.items() if k in spec.field_defaults()}
    # Fixed scheduling correctly rejects a ceiling below its declared schedule;
    # it never silently truncates or changes repetitions.
    if method=='constant_stimuli' and ending=='ceiling':
        for old in (True,False):
            with monkeypatch.context() as patch:
                with reference(patch,WAVE,identity,old) as spec:
                    with pytest.raises(ValueError):spec.normalise_values(values)
        return
    run=compare(tmp_path,monkeypatch,WAVE,identity,method,values,137,
                abort=ending if ending in ('ready','trial') else None)
    if ending=='complete':assert run.status=='completed'
    if ending=='ready':assert run.accepted_trials==0 and run.status=='aborted_by_user'
    if ending=='trial':assert run.accepted_trials==2 and run.status=='aborted_by_user'

@pytest.mark.parametrize('case',CASES,ids=lambda c:f"{c['identity']}-{c['method']}-{c['seed']}")
def test_effective_review_plans_and_all_declared_contracts(monkeypatch,case):
    results=[];specs=[]
    for old in (True,False):
        with monkeypatch.context() as patch:
            with reference(patch,WAVE,case['identity'],old) as spec:
                values=spec.normalise_values(case['values'])
                if case['identity']=='contrast_sensitivity_windowed' and case['method']=='constant_stimuli':
                    # Inherited Review hook calls the Gaussian factory without
                    # circular resolution. Pin this pre-existing error explicitly;
                    # acquisition equivalence above still exercises both modes.
                    # A source-reorganisation PR must not silently repair science
                    # or hide an already broken Review behind a fallback plan.
                    with pytest.raises(KeyError,match='grating_sigma_deg'):
                        describe_settings(spec,values,resolve_stimuli(spec,values,repo_root=ROOT))
                    results.append({'existing_review_error':'grating_sigma_deg'})
                    specs.append(spec)
                    continue
                d=describe_settings(spec,values,resolve_stimuli(spec,values,repo_root=ROOT))
                results.append({k:d[k] for k in ('stimuli','overrides','conditions','resolution','phases','session_phases','phase_inputs','inactive_fields')})
                specs.append(spec)
    assert results[0]==results[1]
    for attr in ('fields','response_paradigm','calibration_requirements','monitor_capabilities',
                 'scientific_spec','stimulus_slots','stimulus_defaults','trial_column_overrides'):
        assert getattr(specs[0],attr)==getattr(specs[1],attr),attr
