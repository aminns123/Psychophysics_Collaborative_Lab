"""All official science against frozen merged Stage B; no participant acquisition."""
import ast
import copy
import csv
import hashlib
import importlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
from psychophysics_lab.researcher import RunContext, TrialTimeline
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run

ROOT=Path(__file__).resolve().parents[1]
BASELINE=json.loads((ROOT/'tests/fixtures/stage_c_baseline_20261027.json').read_text())
OFFICIAL=tuple(item['id'] for item in BASELINE['inventory'])
MIGRATED=tuple(i for i in OFFICIAL if i not in {'contrast_sensitivity','ellipse_major_axis'})
SOFTWARE_CASES=[(i,m) for i in OFFICIAL for m in ('adaptive','constant_stimuli')]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def scientific(value):
    """Only added session-slot provenance is omitted; trial science is retained."""
    if isinstance(value,list):return [scientific(v) for v in value]
    if isinstance(value,dict):return {k:scientific(v) for k,v in value.items() if k!='ready_fixation'}
    return value


def read(folder,name):
    return json.loads((folder/name).read_text(encoding='utf-8'))


def rows(folder):
    with (folder/'trials.tsv').open(encoding='utf-8',newline='') as stream:
        return list(csv.DictReader(stream,delimiter='\t'))


def select_opening(monkeypatch,identity,enabled):
    registry.get_experiment(identity)
    module=importlib.import_module('psychophysics_lab.experiments.'+identity)
    if not enabled:monkeypatch.setattr(module,'SESSION_START',[])
    spec=module.definition()
    monkeypatch.setattr(module,'SPEC',spec)
    monkeypatch.setitem(registry._REGISTRY,identity,spec)
    return module,spec


@pytest.mark.parametrize('enabled',[False,True],ids=['empty-opening','standard-opening'])
@pytest.mark.parametrize('case',BASELINE['cases'],ids=lambda c:f"{c['identity']}-{c['method']}-{c['seed']}")
def test_every_complete_scientific_trace_matches_before_migration(tmp_path,monkeypatch,case,enabled):
    monkeypatch.setattr('psychophysics_lab.analysis.previews.create_run_figures',lambda **kw:None)
    _,spec=select_opening(monkeypatch,case['identity'],enabled)
    a,_=simulate(repo_root=ROOT,data_root=tmp_path,experiment_id=spec.id,values=case['values'],seed=case['seed'],
                 analyse=False,observer=TeachingObserver(accuracy=.65))
    assert (a.status,a.accepted_trials)==(case['status'],case['accepted'])
    assert digest(rows(a.run_directory))==case['rows_sha256']
    for name,expected in case['files_sha256'].items():
        assert digest(scientific(read(a.run_directory,name)))==expected,name
    if enabled:
        opening=read(a.run_directory,'session_events.json')
        assert opening['status']=='completed' and len(opening['events'])==2
        assert opening['events'][0]['readiness']['key']=='SPACE'
        assert opening['events'][0]['readiness']['elapsed_s']==0
        assert opening['events'][1]['virtual_offset_ms']==1000
        assert not any('response' in e for e in opening['events'])
    else:
        assert not (a.run_directory/'session_events.json').exists()
    failures=[(c.name,c.detail) for c in validate_run(a.run_directory) if not c.passed]
    assert not failures,failures


@pytest.mark.parametrize('saved',BASELINE['inventory'],ids=lambda c:c['id'])
def test_defaults_response_meanings_and_safeguards_do_not_drift(saved):
    spec=registry.get_experiment(saved['id'])
    assert digest([dict(f.__dict__) for f in spec.fields])==digest(saved['fields'])
    assert list(spec.calibration_requirements)==saved['calibration']
    assert list(spec.monitor_capabilities)==saved['capabilities']
    assert list(spec.response_paradigm.alternatives)==saved['responses']['alternatives']
    assert list(spec.response_paradigm.keys)==saved['responses']['keys']
    assert dict(spec.scientific_spec)==saved['scientific_spec']


class LegacyPlanSpelling(ast.NodeTransformer):
    def visit_Call(self,node):
        node=self.generic_visit(node)
        if (isinstance(node.func,ast.Name) and node.func.id=='TrialTimeline' and len(node.args)==1
                and isinstance(node.args[0],ast.Call) and isinstance(node.args[0].func,ast.Name)
                and node.args[0].func.id=='trial_events'):
            return ast.Call(func=ast.Name(id='make_trial',ctx=ast.Load()),args=node.args[0].args,keywords=node.args[0].keywords)
        return node


@pytest.mark.parametrize('identity',OFFICIAL)
def test_scientific_function_bodies_and_readable_six_section_contract(identity):
    module=importlib.import_module('psychophysics_lab.experiments.'+identity)
    source=Path(module.__file__).read_text(encoding='utf-8')
    sections=('PARAMETERS','SESSION START','TRIAL EVENTS','SCIENTIFIC RULES','STOPPING AND RESULTS','FRAMEWORK REGISTRATION')
    positions=[source.index(f'# {i}. {s}') for i,s in enumerate(sections,1)]
    assert positions==sorted(positions)
    functions={n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    assert positions[2]<source.index('def trial_events')<positions[3]
    for name,expected in BASELINE['functions'][identity].items():
        if name in {'make_trial','trial_events','procedure','definition'}:continue
        node=LegacyPlanSpelling().visit(copy.deepcopy(functions[name]))
        assert digest(ast.dump(node,include_attributes=False))==expected,name
    assert module.make_trial.__wrapped__ is module.trial_events
    for event in module.SPEC.session_start.phases:
        assert event.slot=='ready_fixation'
    assert module.SPEC.stimulus_slots['ready_fixation'] in {'fixation','gaussian_fixation'}


@pytest.mark.parametrize('identity,method',SOFTWARE_CASES)
def test_real_software_phase_player_keeps_first_trial_and_complete_state(tmp_path,monkeypatch,identity,method):
    from test_stage_b_event_first import software_window
    from psychophysics_lab.config.monitor import load_monitor_profiles
    outputs=[]
    for enabled in (False,True):
        with monkeypatch.context() as patch:
            module=importlib.import_module('psychophysics_lab.experiments.'+identity)
            spec=module.SPEC if enabled else replace(module.SPEC,session_start=[])
            display=software_window(patch)
            profile=replace(load_monitor_profiles(ROOT)['legacy_reference_display'],expected_resolution_px=display.resolution)
            selected=dict(contrast_method=method,max_trials=8,trial_count=4,frequencies_cpd='2',positions_deg='0',
                aspect_ratios='1',ring_conditions='base_only',ring_increment=.03,flanker_cpd=2.,probe_vertical_offset_deg=.4,
                staircases_per_condition=1,fixed_contrasts='0,.01',fixed_repetitions=2,fixation_ms=1,stimulus_ms=1,grating_ms=1,isi_ms=1,interval_ms=1)
            values=spec.normalise_values({k:v for k,v in selected.items() if k in spec.field_defaults()})
            folder=tmp_path/str(enabled);folder.mkdir()
            run=RunContext(values,profile,spec,folder,seed=53,data_kind='uncalibrated_presentation_test',
                           stimulus_snapshots=resolve_stimuli(spec,values,repo_root=ROOT))
            try:spec.procedure(run)
            finally:run.close()
            expected=4 if method=='constant_stimuli' or identity in {'orientation_task','orientation_adaptive','probe_above_below','example_experiment'} else 8
            assert run.accepted_trials==expected
            outputs.append(dict(
                rows=[{k:v for k,v in row.items() if k not in {'recorded_utc','event_time_s'}} for row in rows(folder)],
                trials=[{key:t[key] for key in ('trial_index','condition','target','plan','resolved_stimuli','initial_state','final_state','status')}
                        for t in read(folder,'trial_actions.json')['trials']],
                adaptive=read(folder,'adaptive_history.json') if (folder/'adaptive_history.json').exists() else None,
                primary=read(folder,'primary_thresholds.json') if (folder/'primary_thresholds.json').exists() else None))
            if enabled:
                trace=read(folder,'session_events.json')
                assert trace['status']=='completed' and len(trace['events'])==2
                for selected_stimulus in trace['resolved_stimuli'].values():
                    assert selected_stimulus['stimulus_id'] in {'gaussian_fixation','fixation_cross'}
            else:assert not (folder/'session_events.json').exists()
    assert outputs[0]==outputs[1]


@pytest.mark.parametrize('identity',OFFICIAL)
def test_escape_at_readiness_is_zero_response_abort_for_every_official(tmp_path,monkeypatch,identity):
    from test_stage_b_event_first import software_window
    from psychophysics_lab.config.local import config_root,save_profile
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.config.models import SetupRequest
    from psychophysics_lab.core.presentation_testing import PresentationTestRequest,run_presentation_test
    monkeypatch.setattr('psychophysics_lab.core.display.preflight_fullscreen_display',lambda p:None)
    display=software_window(monkeypatch,escape=True)
    profile=save_profile(config_root(ROOT),replace(load_monitor_profiles(ROOT)['legacy_reference_display'],
        id='stage_c_display',origin='local',expected_resolution_px=display.resolution,
        display_binding={'index':0,'x':0,'y':0,'width':1000,'height':600}))
    spec=registry.get_experiment(identity)
    chosen={'ring_increment':.03,'flanker_cpd':2.,'probe_vertical_offset_deg':.4,'frequencies_cpd':'2'}
    values=spec.normalise_values({k:v for k,v in chosen.items() if k in spec.field_defaults()})
    a=run_presentation_test(PresentationTestRequest(SetupRequest('TEST','new',identity,profile.id,values),trial_limit=2),repo_root=ROOT)
    assert a.status=='aborted_by_user' and a.accepted_trials==0 and not rows(a.run_directory)
    assert read(a.run_directory,'session_events.json')['status']=='aborted'
    assert all(c.passed for c in validate_run(a.run_directory))


@pytest.mark.parametrize('identity',OFFICIAL)
def test_generic_review_and_execution_share_the_new_function(tmp_path,monkeypatch,identity):
    from psychophysics_lab.ui.settings_review import describe_settings
    module=importlib.import_module('psychophysics_lab.experiments.'+identity)
    original=module.trial_events
    def edited(settings,condition):
        events=original(settings,condition)
        return [replace(events[0],duration_ms=17)]+events[1:]
    monkeypatch.setattr(module,'trial_events',edited)
    monkeypatch.setattr(module,'make_trial',lambda *a: (_ for _ in ()).throw(AssertionError('legacy plan used')))
    selected=dict(max_trials=2,trial_count=2,ring_increment=.03,probe_vertical_offset_deg=.4,flanker_cpd=2.)
    spec=registry.get_experiment(identity)
    values=spec.normalise_values({k:v for k,v in selected.items() if k in spec.field_defaults()})
    description=describe_settings(spec,values,resolve_stimuli(spec,values,repo_root=ROOT))
    assert description['trial_event_function']=='trial_events' and description['phases'][0]['duration_ms']==17
    a,_=simulate(repo_root=ROOT,data_root=tmp_path,experiment_id=identity,values=values,analyse=False)
    assert all(t['plan']['phases'][0]['duration_ms']==17 for t in read(a.run_directory,'trial_actions.json')['trials'])
