"""Boundary and failure regressions from the repository reliability audit."""
from types import SimpleNamespace
import math
import json
import pytest

from simulations.scenarios.run import ScenarioRun



def test_plot_failure_closes_matplotlib_figure(tmp_path,monkeypatch):
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from psychophysics_lab.analysis.thresholds import _plot, ConditionThreshold
    before=plt.get_fignums()
    def fail(*args,**kwargs): raise OSError('plot disk fault')
    monkeypatch.setattr(Figure,'savefig',fail)
    with pytest.raises(OSError): _plot((ConditionThreshold('2',1,.1),),tmp_path/'plot.png')
    assert plt.get_fignums()==before

def test_failed_index_replace_preserves_old_catalogue_and_cleans_temp(tmp_path,monkeypatch):
    from psychophysics_lab.data import index
    path=index.upsert_run_index(tmp_path,{'run_uuid':'original'})
    original=path.read_bytes()
    def fail(*args): raise OSError('index replace fault')
    monkeypatch.setattr(index.os,'replace',fail)
    with pytest.raises(OSError): index.upsert_run_index(tmp_path,{'run_uuid':'second'})
    assert path.read_bytes()==original
    assert not list(tmp_path.glob('runs_index.csv.*.tmp'))

def test_spatial_nyquist_boundary_rejected_independently():
    from psychophysics_lab.config.models import MonitorProfile
    from psychophysics_lab.core.geometry_check import GeometryCheckRequest
    from psychophysics_lab.core.display_tests import resolve_test
    p=MonitorProfile('test','Test',.6,.34,60,1)
    maximum_angle=math.degrees(2*math.atan((.6/1920)/2))
    request=GeometryCheckRequest(p.id,'physical_mm',100,test_kind='spatial',spatial_cpd=1/(2*maximum_angle))
    with pytest.raises(ValueError,match='Nyquist'): resolve_test(p,request,(1920,1080))


def test_later_scenario_seed_failure_records_partial_report(tmp_path,monkeypatch):
    from simulations.scenarios.run import run_scenario
    import simulations.run as runtime
    import importlib
    runner=importlib.import_module('simulations.scenarios.run')
    folder=tmp_path/'data'/'synthetic_1'/'test_run'
    folder.mkdir(parents=True)
    manifest=folder/'manifest.json'
    manifest.write_text(json.dumps({'data_kind':'synthetic','participant_id':'synthetic_1'}))
    (folder/'SYNTHETIC_DATA.json').write_text('{}')
    def simulate(**kwargs):
        if kwargs['seed']==2: raise RuntimeError('second seed failed')
        return SimpleNamespace(run_directory=folder,manifest_file=manifest,status='completed',accepted_trials=1),None
    monkeypatch.setattr(runtime,'simulate',simulate)
    monkeypatch.setattr(runner,'_validator_checks',lambda *args:({'name':'fixture','passed':True,'detail':'isolated'},))
    with pytest.raises(RuntimeError,match='second seed failed'):
        run_scenario(experiment_id='legacy_contrast_sensitivity',scenario_id='csf_baseline',data_root=tmp_path/'data',seeds=(1,2))
    report=json.loads((folder/'scenario_report.json').read_text())
    assert report['passed'] is False and report['status']=='error'
    assert report['failed_seed']==2 and report['completed_seed_records']==[1]
