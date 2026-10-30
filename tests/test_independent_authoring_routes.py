"""Independent authoring through project discovery and trusted external folders.

The same original laboratory science/stimulus is installed into disposable
copies through both supported source layouts. No registry/TUI edits or imports
from official experiments are used.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/review_temporal_lab'

# Executed in a genuinely fresh interpreter against a disposable source copy.
EXERCISE=r'''
import asyncio, csv, hashlib, json, sys
import importlib
from pathlib import Path
from textual.widgets import Button, Input, Select, Collapsible, Static
from psychophysics_lab import extensions as ext
from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ExperimentParametersScreen, ReviewScreen
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
from psychophysics_lab.ui.stimulus_editor import StimulusValueEditor
from psychophysics_lab.ui import refresh
from psychophysics_lab.config.local import load_presets
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.data.reader import load_run
from simulations.run import simulate
from scripts.validate_run import validate_run
root,lab,route,method=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3],sys.argv[4]
identity='auditlab__ring_order'
source=(lab/'experiments'/f'{identity}.py' if route=='external' else root/'src/psychophysics_lab/experiments'/f'{identity}.py')
stimulus_source=lab/'stimulus_library.py' if route=='external' else root/'src/psychophysics_lab/stimulus_library.py'
protected={p:p.read_bytes() for p in [source,stimulus_source,*list((root/'src/psychophysics_lab/ui').glob('*.py')),
                                   root/'src/psychophysics_lab/experiments/_internal/registry.py']}
def rejects(call,needle):
    try: call()
    except (ValueError,KeyError) as error: assert needle.lower() in str(error).lower(), str(error)
    else: raise AssertionError('Required safeguard did not reject operation: '+needle)
if route=='external':
    rejects(lambda:ext.configure(root,lab,trusted=False),'trust')
    ext.configure(root,lab,trusted=True)
    assert not ext.load(root)
    assert ext.status(root,'experiment',identity)=='draft'
    rejects(lambda:ext.publish(root,'experiment',identity),'successful')
    rejects(lambda:simulate(repo_root=root,data_root=root.parent/'saved_data',experiment_id=identity,values={},analyse=False),'Unknown experiment')
    import psychophysics_lab.development as dev
    dev.user_data_root=lambda repo:root.parent/'private-development'
    assert dev.execute_user_action(root,'preview','auditlab__annulus',{})==0
    ext.publish(root,'stimulus','auditlab__annulus')
    assert dev.execute_user_action(root,'test',identity,{})==0
    ext.publish(root,'experiment',identity)
    assert ext.status(root,'experiment',identity)=='ready' and not ext._development
spec=get_experiment(identity)
stimulus=get_stimulus('auditlab__annulus')
science=importlib.import_module(spec.procedure.__module__)
settings=spec.normalise_values({})
for target in (0,1):
    events=science.trial_events(settings,{'gap_ms':20,'target':target})
    cue=next(event for event in events if event.name=='cue')
    assert cue.instructions=='CUE' and cue.duration_ms==10
    assert all(event.instructions!='CUE' for event in events if event.name!='cue')
    order=[event.name for event in events]
    assert (order.index('annulus')<order.index('cue'))==(target==0)
assert bool(spec.origin_namespace)==(route=='external')
assert bool(stimulus.origin_namespace)==(route=='external')
opened=[]
import psychophysics_lab.ui.setup as setup
setup.open_source=lambda root,path,line=1,**kwargs:opened.append((Path(path),line))
async def settle(app,pilot):
    for _ in range(100):
        await pilot.pause(.05)
        screen=app.screen
        if screen.is_mounted and all(w.is_mounted for w in screen.query('*')):
            await pilot.pause(.05)
            if app.screen is screen: return
    raise AssertionError('Interface did not settle')
async def scenario():
    app=PsyCoLabSetupApp(repo_root=root,data_root=root.parent/'saved_data')
    async with app.run_test(size=(150,50)) as pilot:
        app.query_one('#experiment',Select).value=identity
        await settle(app,pilot)
        app.query_one('#configure',Button).press(); await settle(app,pilot)
        config=app.screen
        assert type(config) is ExperimentConfigScreen, (type(config).__name__, [(w.id,str(w.render())) for w in config.query(Static)])
        assert not config.query(StimulusParametersPanel)
        assert not config.query('#field-cue-gaps-ms')
        assert all(str(c.title) in {'Universal setup','Local presets'} for c in config.query(Collapsible))
        config.query_one('#field-contrast-method',Select).value=method
        config.query_one('#review',Button).press(); await settle(app,pilot)
        review=app.screen
        assert isinstance(review,ReviewScreen) and not review.configuration_error, (type(review).__name__, getattr(review,"configuration_error",None))
        assert {'Conditions','Responses','Trial','Recorded measurements','Saved data','ring'} <= {r[0] for r in review._review_rows}
        assert any(r[1]=='Cue gaps (ms)' for r in review._review_rows)
        assert any('before_cue' in r[2] and 'after_cue' in r[2] for r in review._review_rows)
        measurement=next(i for i,r in enumerate(review._review_rows) if r[0]=='Recorded measurements' and r[1]=='cue_gap_ms (ms)')
        review._open_review_file(measurement)
        assert opened[-1][0].resolve()==source.resolve()
        assert opened[-1][1]>1
        row=next(i for i,r in enumerate(review._review_rows) if r[0]=='ring' and r[1]=='Annulus radius (degrees)')
        review._open_review_file(row)
        assert opened[-1][0].resolve()==stimulus_source.resolve()
        review._edit_review_parameter(row); await settle(app,pilot)
        assert isinstance(app.screen,StimulusValueEditor)
        radius=app.screen.query_one('#stimulus-value-1',Input)
        assert radius.has_focus
        radius.value='-1'
        app.screen.query_one('#stimulus-value-name',Input).value='annulus_preset'
        app.screen.query_one('#stimulus-values-save',Button).press(); await settle(app,pilot)
        assert isinstance(app.screen,StimulusValueEditor) and radius.value=='-1'
        radius.value='.4'
        app.screen.query_one('#stimulus-values-save',Button).press(); await settle(app,pilot)
        editor=app.screen
        assert type(editor) is ExperimentParametersScreen
        gaps=editor.query_one('#field-cue-gaps-ms',Input)
        flash=editor.query_one('#field-flash-ms',Input)
        flash.value=''
        gaps.value='15,nan'
        editor.query_one('#review',Button).press(); await settle(app,pilot)
        assert app.screen is editor and flash.value=='' and gaps.value=='15,nan'
        assert review.request.experiment_values['cue_gaps_ms']=='20,40'
        flash.value='35'; gaps.value='15,35'
        editor.query_one('#field-fixed-repetitions',Input).value='2'
        editor.query_one('#preset-name',Input).value='temporal_preset'
        editor.query_one('#save-preset',Button).press(); await settle(app,pilot)
        presets=load_presets(app.local_config_root,identity)
        assert presets['temporal_preset']['cue_gaps_ms']=='15,35'
        gaps.value='25,45'
        editor.query_one('#config-preset',Select).value='temporal_preset'
        editor.query_one('#load-preset',Button).press(); await settle(app,pilot)
        assert gaps.value=='15,35'
        editor.query_one('#review',Button).press(); await settle(app,pilot)
        assert app.screen is review and not review.configuration_error
        assert review.request.stimulus_snapshots['ring']['document']['parameters']['radius_deg']==.4
        assert review.request.experiment_values['flash_ms']==35
        state=refresh.capture_state(app)
        # Uses the actual fresh-interpreter checker and configured trust/Ready records.
        refresh.check_refresh(state,root)
        request=review.request
        rejects(lambda:validate_setup(request,spec,app.monitor_profiles[request.monitor_profile_id]),'Human acquisition blocked')
    resumed=PsyCoLabSetupApp(repo_root=root,data_root=root.parent/'saved_data',refresh_state=state)
    async with resumed.run_test(size=(150,50)) as pilot:
        await settle(resumed,pilot)
        assert isinstance(resumed.screen,ReviewScreen)
        restored=resumed.screen.request
        assert restored.experiment_values==request.experiment_values
        assert restored.stimulus_snapshots==request.stimulus_snapshots
        resumed.verify_settings_current(restored)
    outputs=[simulate(repo_root=root,data_root=root.parent/'saved_data',experiment_id=identity,values=restored.experiment_values,
                      stimulus_snapshots=restored.stimulus_snapshots,seed=29,analyse=False)[0] for _ in range(2)]
    assert outputs[0].trial_log_file.read_bytes()==outputs[1].trial_log_file.read_bytes()
    for result in outputs:
        assert result.status=='completed' and result.accepted_trials==(8 if method=='constant_stimuli' else 4)
        assert all(c.passed for c in validate_run(result.run_directory))
        loaded=load_run(result.run_directory)
        assert len(loaded['trials']['trial_index'])==result.accepted_trials
        with result.trial_log_file.open(encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream,delimiter='\t'))
        assert len(rows[0])==20 and {float(r['stimulus_condition']) for r in rows}=={15,35}
        journal=json.loads((result.run_directory/'trial_presentations.json').read_text())['trials']
        assert all(t['measurements']['annulus_radius_deg']==.4 and t['measurements']['requested_flash_ms']==35 for t in journal)
        assert {t['measurements']['target_order'] for t in journal}=={0,1}
        if method=='constant_stimuli':
            assert all(r['staircase_id']==r['reversal_count']=='' for r in rows)
        else:
            assert all(r['staircase_id']!='' for r in rows)
        manifest=json.loads((result.run_directory/'manifest.json').read_text())
        if route=='external':
            assert manifest['laboratory_extensions']['namespace']=='auditlab'
            assert manifest['laboratory_extensions']['source_sha256']['stimulus_library.py']==hashlib.sha256(stimulus_source.read_bytes()).hexdigest()
    assert all(path.read_bytes()==original for path,original in protected.items())
    if route=='external':
        # Deliberate source change is confined to the disposable lab, after proving no unexpected writes.
        source.write_bytes(source.read_bytes()+b'\n# deliberate acceptance-test source revision\n')
        assert ext.status(root,'experiment',identity)=='draft'
        rejects(lambda:simulate(repo_root=root,data_root=root.parent/'saved_data',experiment_id=identity,values={},analyse=False),'changed')
        rejects(lambda:ext.publish(root,'experiment',identity),'successful')
        ext.configure(root)
        assert identity not in {s.id for s in list_experiments()}
    print(json.dumps({'route':route,'method':method,'status':'PASS','source':str(source),'stimulus_source':str(stimulus_source)}))
asyncio.run(scenario())
'''

@pytest.mark.parametrize('route',['project','external'])
@pytest.mark.parametrize('method',['adaptive','constant_stimuli'])
def test_independent_science_both_source_routes_and_methods(tmp_path,route,method):
    root=tmp_path/'disposable_project'
    shutil.copytree(ROOT/'src',root/'src',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'configs',root/'configs')
    shutil.copy2(ROOT/'pyproject.toml',root/'pyproject.toml')
    lab=tmp_path/'PsyCoLab_Extensions'
    if route=='external':
        shutil.copytree(FIXTURE,lab)
        # A same-named decoy must never become the external source link target.
        (root/'src/psychophysics_lab/experiments/auditlab__ring_order.py').write_text('# Same filename, no definition.\n',encoding='utf-8')
    else:
        source=(FIXTURE/'experiments/auditlab__ring_order.py').read_text(encoding='utf-8-sig')
        source=source.replace("'experiments/auditlab__ring_order.py'","'src/psychophysics_lab/experiments/auditlab__ring_order.py'")
        (root/'src/psychophysics_lab/experiments/auditlab__ring_order.py').write_text(source,encoding='utf-8')
        stimulus=(FIXTURE/'stimulus_library.py').read_text(encoding='utf-8-sig').replace("source_path='stimulus_library.py'","source_path='src/psychophysics_lab/stimulus_library.py'")
        with (root/'src/psychophysics_lab/stimulus_library.py').open('a',encoding='utf-8') as stream:
            stream.write('\n'+stimulus)
    env=os.environ|{'PYTHONPATH':os.pathsep.join([str(root/'src'),str(ROOT)]),
                    'PSYCOLAB_REPO_ROOT':str(root),'PSYCOLAB_CONFIG_DIR':str(tmp_path/'private_config'),
                    'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run([sys.executable,'-u','-c',EXERCISE,str(root),str(lab),route,method],
                          cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    (tmp_path/'independent_acceptance.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    assert result.returncode==0, result.stdout[-3000:]+'\n'+result.stderr[-5000:]
    assert json.loads(result.stdout.strip().splitlines()[-1])['status']=='PASS'
