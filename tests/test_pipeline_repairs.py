import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.analysis.previews import create_run_figures
from psychophysics_lab.experiments._internal.detection_limits import probe_limit
from psychophysics_lab.stimulus_library import DetectionScene


def saved_run(tmp_path, *, status='completed', kind='human', identity='custom_adaptive', complete=True, reversals=True, repeats=2):
    run=tmp_path/'run_001';run.mkdir()
    (run/'manifest.json').write_text(json.dumps(dict(status=status,data_kind=kind,experiment_id=identity,run_uuid='example')))
    expected={'2':[1], '5':[2,3][:repeats]}
    rule=dict(version=1,value_column='presented_display_contrast',within_staircase='median',across_staircases='arithmetic_mean',retained_reversals=2,units='custom_strength')
    (run/'resolved_experiment.json').write_text(json.dumps(dict(primary_estimator=rule,expected_staircases=expected)))
    rows=[]
    for step,value in enumerate((.001,.02,.08),1):
        for condition,ids in expected.items():
            for i in ids:
                rows.append(dict(trial_index=len(rows)+1,staircase_trial_index=step,staircase_id=i,stimulus_condition=condition,
                                 presented_display_contrast=value*i,next_display_contrast=value*i,reversal=int(reversals),
                                 correct=step%2,staircase_complete=int(step==3 and (complete or i==1))))
    with (run/'trials.tsv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0],delimiter='\t');writer.writeheader();writer.writerows(rows)
    return run


@pytest.mark.parametrize('kind',['human','synthetic'])
@pytest.mark.parametrize('status',['completed','max_trials_reached','aborted_by_user','error'])
@pytest.mark.parametrize('identity',['contrast_sensitivity','csf_thesis','arbitrary_custom_experiment'])
def test_figures_use_data_contract_and_preserve_raw_records(tmp_path,kind,status,identity):
    run=saved_run(tmp_path,kind=kind,status=status,identity=identity,complete=False)
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}
    result=create_run_figures(data_root=tmp_path,run_directory=run)
    assert result['data_kind']==kind
    panels=list((run/'analysis').glob('staircases_condition_*.png'))
    assert len(panels)==2
    for png in panels:
        assert png.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and png.stat().st_size>10000
    assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}
    assert set(result['primary']['condition_thresholds'])==({'2'} if status!='error' else set())
    assert (run/'analysis/threshold_vs_condition.png').exists()==(status!='error')
    assert (run/'analysis/sensitivity_vs_condition.png').exists()==(status!='error')
    summary=json.loads((run/'analysis/staircase_preview.json').read_text())
    assert summary['condition_staircase_counts']=={'2':1,'5':2}
    assert summary['strength_units']=='custom_strength'


@pytest.mark.parametrize('estimator,expected',[('median',.05),('geometric_mean',.04)])
def test_primary_retained_reversals_and_aggregation_are_respected(tmp_path,estimator,expected):
    run=saved_run(tmp_path)
    resolved=json.loads((run/'resolved_experiment.json').read_text())
    resolved['primary_estimator']['within_staircase']=estimator
    (run/'resolved_experiment.json').write_text(json.dumps(resolved))
    result=create_run_figures(data_root=tmp_path,run_directory=run)['primary']
    assert result['condition_thresholds']['2']['threshold']==pytest.approx(expected)
    assert result['condition_thresholds']['5']['threshold']==pytest.approx(2.5*expected)
    assert result['condition_thresholds']['5']['sensitivity']==pytest.approx(1/(2.5*expected))


def test_no_reversals_still_has_staircases_and_explicit_threshold_status(tmp_path):
    run=saved_run(tmp_path,reversals=False,repeats=1)
    result=create_run_figures(data_root=tmp_path,run_directory=run)
    assert result['status']=='staircases_only'
    assert not result['primary']['condition_thresholds']
    assert result['primary']['excluded_staircases']
    assert not (run/'analysis/threshold_vs_condition.png').exists()


def test_nonadaptive_rows_do_not_create_staircase_figures(tmp_path):
    run=saved_run(tmp_path)
    path=run/'trials.tsv'
    with path.open(newline='') as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
    for r in rows:r['staircase_id']=''
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0],delimiter='\t');writer.writeheader();writer.writerows(rows)
    assert create_run_figures(data_root=tmp_path,run_directory=run) is None
    assert not (run/'analysis').exists()


def test_plot_failure_is_recorded_without_changing_manifest(tmp_path,monkeypatch):
    import psychophysics_lab.analysis.previews as previews
    run=saved_run(tmp_path);before=(run/'manifest.json').read_bytes()
    monkeypatch.setattr(previews,'create_staircase_preview',lambda **kwargs: (_ for _ in ()).throw(RuntimeError('injected plot failure')))
    result=create_run_figures(data_root=tmp_path,run_directory=run)
    assert result['status']=='partial' and 'injected plot failure' in result['errors'][0]
    assert (run/'manifest.json').read_bytes()==before
    assert json.loads((run/'analysis/analysis_status.json').read_text())['errors']


@pytest.mark.parametrize('background',[.01,.2,.5,.9])
def test_remote_flanker_does_not_reduce_probe_headroom(background):
    p={f.key:f.default for f in DetectionScene.PARAMETERS}|dict(background=background,flanker_present=True,probe_x_deg=0,probe_y_deg=1,probe_length_deg=.1,probe_width_deg=.02)
    axis=np.linspace(-7,7,701);grid=np.meshgrid(axis,axis)
    bound,_=probe_limit(p,grid)
    assert bound==1-background
    pixels=DetectionScene.render(p|{'contrast':bound},*grid)
    assert pixels.min()>=0 and pixels.max()<=1


def test_real_overlap_reduces_bound_and_hold_is_safe():
    p={f.key:f.default for f in DetectionScene.PARAMETERS}|dict(background=.2,flanker_present=True,flanker_cpd=1,probe_x_deg=-2.75,probe_y_deg=1,probe_length_deg=.1,probe_width_deg=.1)
    axis=np.linspace(-7,7,701);grid=np.meshgrid(axis,axis)
    bound,position=probe_limit(p,grid)
    assert bound==pytest.approx(.8-.009*np.sin(2*np.pi*.24))
    assert position[0]==pytest.approx(-2.76,abs=.021)
    pixels=DetectionScene.render(p|{'contrast':bound},*grid)
    assert pixels.max()<=1
    assert DetectionScene.render(p|{'contrast':.8},*grid).max()>1


def test_absent_ring_ignores_geometry_and_increment():
    p={f.key:f.default for f in DetectionScene.PARAMETERS}|dict(ring_present=False,ring_radius_deg=.17,aspect_ratio=.5,ring_increment=1.,background=.9)
    DetectionScene.validate(p)
    DetectionScene.validate(p|{'probe_present':False})


def test_public_identity_and_retired_identifiers():
    from psychophysics_lab.experiments import get_experiment,list_experiments
    assert get_experiment('contrast_sensitivity').id=='contrast_sensitivity'
    assert all('thesis' not in s.id and not s.historical for s in list_experiments())
    for identity in ('csf_thesis','legacy_contrast_sensitivity','base_flanker','indirect_flanker','ellipse_2d'):
        with pytest.raises(KeyError):get_experiment(identity)
