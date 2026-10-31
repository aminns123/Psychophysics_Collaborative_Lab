"""Execute the actual opt-in lessons through both supported discovery routes.

Fresh processes keep registry/trust/config isolated from the parent test suite.
The Textual exercise is software UI acceptance, not an independent human trial.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'examples/laboratory_extensions'
LESSONS = ('demolab__lesson1_side', 'demolab__lesson2_strength', 'demolab__lesson3_study')

EXERCISE = r'''
import asyncio, csv, importlib, json, sys
from pathlib import Path
from textual.widgets import Button, Input, Select, Collapsible
from psychophysics_lab import extensions as ext
from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen, ExperimentParametersScreen, ReviewScreen
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
from psychophysics_lab.ui import refresh
from psychophysics_lab.config.local import load_presets
from psychophysics_lab.data.reader import load_run
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run
root, lab, route, identity = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
source=(lab/'experiments'/f'{identity}.py' if route=='external' else root/'src/psychophysics_lab/experiments'/f'{identity}.py')
stimulus_source=lab/'stimulus_library.py' if route=='external' else root/'src/psychophysics_lab/stimulus_library.py'
protected={p:p.read_bytes() for p in [source,stimulus_source,*list((root/'src/psychophysics_lab/ui').glob('*.py')),
                                    root/'src/psychophysics_lab/experiments/_internal/registry.py']}
if route=='external':
    try:ext.configure(root,lab,trusted=False)
    except ValueError:pass
    else:raise AssertionError('Untrusted source must not load')
    ext.configure(root,lab,trusted=True)
    assert not ext.load(root) and ext.status(root,'experiment',identity)=='draft'
    import psychophysics_lab.development as dev
    dev.user_data_root=lambda repo:root.parent/'development'
    if identity.endswith('study'):
        assert dev.execute_user_action(root,'preview','demolab__learning_line',{})==0
        ext.publish(root,'stimulus','demolab__learning_line')
    assert dev.execute_user_action(root,'test',identity,{})==0
    ext.publish(root,'experiment',identity)
    assert ext.status(root,'experiment',identity)=='ready'
spec=get_experiment(identity)
science=importlib.import_module(spec.procedure.__module__)
assert bool(spec.origin_namespace)==(route=='external')
if identity.endswith('study'):
    assert bool(get_stimulus('demolab__learning_line').origin_namespace)==(route=='external')
values=spec.normalise_values({})
methods=('adaptive','constant_stimuli') if 'contrast_method' in values else ('original',)
invalid=[{'stimulus_ms':-1},{'line_width_deg':float('nan')}]
if len(methods)>1:
    invalid += [{'eccentricities_deg':'1,nan'},{'eccentricities_deg':'1,1'},
                {'starting_strength':.6},{'trial_count':1},
                {'contrast_method':'constant_stimuli','fixed_contrasts':'0,.6'},
                {'contrast_method':'constant_stimuli','max_trials':1}]
if identity.endswith('study'):
    invalid += [{'lengths_deg':'0.1,1'},{'edge_deg':.02,'line_width_deg':.02}]
for bad in invalid:
    try:spec.normalise_values(bad)
    except ValueError:pass
    else:raise AssertionError('Invalid scientific inputs accepted: '+str(bad))
condition=science.make_conditions(values)[0]
if len(methods)>1:condition=dict(condition,target=0,contrast=.2)
events=science.trial_events(values,condition)
assert [e.name for e in events]==(['fixation','line','retention','answer'] if identity.endswith('study') else ['fixation','line','answer'])
assert events[0].duration_ms=='fixation_ms' and events[1].duration_ms=='stimulus_ms'
assert spec.session_start.phases[0].key=='SPACE' and len(spec.session_start.phases)==2
if identity.endswith('study'):
    audio=science.trial_events(values|{'audio_cues':1},condition)
    assert audio[1].beep.frequency_hz==550 and audio[-1].beep.frequency_hz==750
opened=[]
import psychophysics_lab.ui.setup as setup
setup.open_source=lambda root,path,line=1,**kwargs:opened.append((Path(path),line))
async def settle(app,pilot):
    for _ in range(100):
        await pilot.pause(.05)
        screen=app.screen
        if screen.is_mounted and all(w.is_mounted for w in screen.query('*')):
            await pilot.pause(.05)
            if app.screen is screen:return
    raise AssertionError('Interface did not settle')

async def scenario(method):
    app=PsyCoLabSetupApp(repo_root=root,data_root=root.parent/'data')
    async with app.run_test(size=(150,50)) as pilot:
        app.query_one('#experiment',Select).value=identity;await settle(app,pilot)
        app.query_one('#configure',Button).press();await settle(app,pilot)
        config=app.screen
        assert type(config) is ExperimentConfigScreen
        assert not config.query(StimulusParametersPanel)
        assert not config.query('#field-stimulus-ms')
        assert all(str(c.title) in {'Universal setup','Local presets'} for c in config.query(Collapsible))
        if method!='original':config.query_one('#field-contrast-method',Select).value=method
        config.query_one('#review',Button).press();await settle(app,pilot)
        review=app.screen
        assert isinstance(review,ReviewScreen) and not review.configuration_error, getattr(review,'configuration_error',None)
        assert {'Conditions','Responses','Trial','Recorded measurements','Saved data'} <= {r[0] for r in review._review_rows}
        assert all('Units not declared' not in r[1] for r in review._review_rows if r[0]=='Recorded measurements')
        row=next(i for i,r in enumerate(review._review_rows) if r[0]=='Recorded measurements' and r[1]=='line_x_deg (degrees)')
        review._open_review_file(row)
        assert opened[-1][0].resolve()==source.resolve() and opened[-1][1]>1
        if identity.endswith('study'):
            # Trial-controlled edge/width correctly link to experiment inputs.
            # The renderer's independent patch extent links to its own class.
            row=next(i for i,r in enumerate(review._review_rows) if r[0]=='target' and r[1]=='Patch extent (degrees)')
            review._open_review_file(row)
            assert opened[-1][0].resolve()==stimulus_source.resolve()
        review._edit_review_parameter(next(i for i,r in enumerate(review._review_rows) if r[1]=='Line exposure (ms)'))
        await settle(app,pilot)
        editor=app.screen;assert type(editor) is ExperimentParametersScreen
        duration=editor.query_one('#field-stimulus-ms',Input)
        # A blank optional field uses its declared default. An invalid supplied
        # value must remain an editable draft and never be silently accepted.
        duration.value='-1';editor.query_one('#review',Button).press();await settle(app,pilot)
        assert app.screen is editor and duration.value=='-1'
        duration.value='125'
        preset_name='lesson_check_'+method
        editor.query_one('#preset-name',Input).value=preset_name
        editor.query_one('#save-preset',Button).press();await settle(app,pilot)
        assert load_presets(app.local_config_root,identity)[preset_name]['stimulus_ms']==125
        duration.value='130';editor.query_one('#config-preset',Select).value=preset_name
        editor.query_one('#load-preset',Button).press();await settle(app,pilot)
        assert duration.value=='125'
        editor.query_one('#review',Button).press();await settle(app,pilot)
        assert app.screen is review and not review.configuration_error
        state=refresh.capture_state(app);refresh.check_refresh(state,root)
        request=review.request
        if method!='original':assert request.experiment_values['contrast_method']==method
    resumed=PsyCoLabSetupApp(repo_root=root,data_root=root.parent/'data',refresh_state=state)
    async with resumed.run_test(size=(150,50)) as pilot:
        await settle(resumed,pilot)
        assert isinstance(resumed.screen,ReviewScreen)
        assert resumed.screen.request.experiment_values==request.experiment_values
        resumed.verify_settings_current(resumed.screen.request)
    outputs=[simulate(repo_root=root,data_root=root.parent/'data',experiment_id=identity,values=request.experiment_values,
        seed=41,observer=TeachingObserver(.65),analyse=False)[0] for _ in range(2)]
    assert outputs[0].trial_log_file.read_bytes()==outputs[1].trial_log_file.read_bytes()
    for result in outputs:
        assert result.status=='completed'
        assert all(c.passed for c in validate_run(result.run_directory)), validate_run(result.run_directory)
        loaded=load_run(result.run_directory)
        assert len(loaded['trials']['trial_index'])==result.accepted_trials
        with result.trial_log_file.open(encoding='utf-8') as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
        assert len(rows[0])==20
        journal=json.loads((result.run_directory/'trial_presentations.json').read_text())['trials']
        assert all(t['measurements']['line_x_deg']!=0 for t in journal)
        assert {t['measurements']['target_side'] for t in journal}=={'left','right'}
        assert all(t['measurements']['requested_exposure_ms']==125 for t in journal)
        durable=[json.loads(line) for line in (result.run_directory/'trial_events.jsonl').read_text().splitlines()]
        assert len(durable)==result.accepted_trials
        for recorded in durable:
            trial=recorded['trial'];measurement=recorded['presentation']['measurements']
            parameters=trial['resolved_stimuli']['target']['parameters']
            assert trial['resolved_stimuli']['target']['stimulus_id']==('demolab__learning_line' if identity.endswith('study') else 'oriented_line')
            assert parameters['intensity']==(.5+measurement['requested_increment'] if method!='original' else .8)
            assert parameters['length_deg']==measurement['line_length_deg']
            assert parameters['width_deg']==measurement['line_width_deg']
            line=next(e for e in trial['events'] if e['name']=='line')
            assert line['stimuli'][0]['x_deg']==measurement['line_x_deg'] and line['duration_ms']==125
            answer=next(e['response'] for e in trial['events'] if e['kind']=='response')
            assert answer['key']==('F','J')[answer['alternative']]
            assert answer['correct']==(answer['alternative']==trial['target'])
        if method=='constant_stimuli':
            assert all(r['staircase_id']==r['reversal_count']=='' for r in rows)
            assert {t['measurements']['requested_increment'] for t in journal}=={0.,.1,.3}
        elif method=='adaptive':
            assert len({r['staircase_id'] for r in rows})==(4 if identity.endswith('study') else 2)
            assert result.accepted_trials==16
        else:assert result.accepted_trials==8
    assert all(p.read_bytes()==content for p,content in protected.items())

for method in methods:asyncio.run(scenario(method))
# Exercise the actual phase player abort path: no swallowed acquisition retry.
from psychophysics_lab.core.trial_execution import VirtualPresentation
from psychophysics_lab.researcher import ParticipantAbort
play=VirtualPresentation.play_phase
for when,expected in [('ready',0),('third_response',2)]:
    seen=[0]
    def interrupted(self,phase,event,**kwargs):
        if when=='ready' and phase.kind=='key_wait':raise ParticipantAbort('Disposable lesson readiness abort')
        if phase.kind=='response':
            seen[0]+=1
            if when=='third_response' and seen[0]==3:raise ParticipantAbort('Disposable lesson third response abort')
        return play(self,phase,event,**kwargs)
    VirtualPresentation.play_phase=interrupted
    try:
        result,_=simulate(repo_root=root,data_root=root.parent/'aborts',experiment_id=identity,values={},seed=41,analyse=False)
        assert result.status=='aborted_by_user' and result.accepted_trials==expected
        assert all(c.passed for c in validate_run(result.run_directory)), validate_run(result.run_directory)
    finally:VirtualPresentation.play_phase=play
if route=='external':
    source.write_bytes(source.read_bytes()+b'\n# deliberate disposable scientific revision\n')
    assert ext.status(root,'experiment',identity)=='draft'
    try:ext.publish(root,'experiment',identity)
    except ValueError:pass
    else:raise AssertionError('Changed source must require successful retest')
print(json.dumps({'route':route,'identity':identity,'methods':methods,'status':'PASS'}))
'''

@pytest.mark.parametrize('route', ['project', 'external'])
@pytest.mark.parametrize('identity', LESSONS)
def test_progressive_lessons_both_routes(tmp_path, route, identity):
    root = tmp_path / 'disposable_project'
    shutil.copytree(ROOT / 'src', root / 'src', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT / 'configs', root / 'configs')
    shutil.copy2(ROOT / 'pyproject.toml', root / 'pyproject.toml')
    lab = tmp_path / 'PsyCoLab_Extensions'
    if route == 'external':
        shutil.copytree(BUNDLE, lab)
        (root/'src/psychophysics_lab/experiments'/f'{identity}.py').write_text('# Decoy, no definition.\n')
    else:
        source = (BUNDLE/'experiments'/f'{identity}.py').read_text(encoding='utf-8')
        source = source.replace(f"'experiments/{identity}.py'", f"'src/psychophysics_lab/experiments/{identity}.py'")
        (root/'src/psychophysics_lab/experiments'/f'{identity}.py').write_text(source, encoding='utf-8')
        stimulus = (BUNDLE/'stimulus_library.py').read_text(encoding='utf-8').replace("source_path='stimulus_library.py'", "source_path='src/psychophysics_lab/stimulus_library.py'")
        with (root/'src/psychophysics_lab/stimulus_library.py').open('a',encoding='utf-8') as stream:
            stream.write('\n'+stimulus)
    env = os.environ | {'PYTHONPATH': os.pathsep.join([str(root/'src'),str(ROOT)]),
        'PSYCOLAB_REPO_ROOT':str(root), 'PSYCOLAB_CONFIG_DIR':str(tmp_path/'private_config'),
        'PYTHONDONTWRITEBYTECODE':'1'}
    result = subprocess.run([sys.executable,'-u','-c',EXERCISE,str(root),str(lab),route,identity],
        cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    (tmp_path/'lesson_acceptance.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    assert result.returncode == 0, result.stdout[-2500:]+'\n'+result.stderr[-6000:]
    assert json.loads(result.stdout.strip().splitlines()[-1])['status']=='PASS'
