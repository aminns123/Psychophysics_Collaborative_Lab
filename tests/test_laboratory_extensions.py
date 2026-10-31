"""Independent source integration, using only disposable directories."""
import asyncio
import hashlib
import json
import os
import shutil
from pathlib import Path
import pytest
from psychophysics_lab import extensions as ext
from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.development import execute_user_action

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = 'demolab__left_right'
STIMULUS = 'demolab__line'


@pytest.fixture
def lab(tmp_path, monkeypatch):
    list_experiments()
    ext.unload()
    root = tmp_path/'PsyCoLab_Extensions'
    shutil.copytree(ROOT/'examples/laboratory_extensions', root)
    monkeypatch.setattr('psychophysics_lab.development.user_data_root',lambda repo:tmp_path/'development_data')
    yield root
    ext.unload()


def enable(lab):
    ext.configure(ROOT, lab, trusted=True)
    assert not ext.load(ROOT)


@pytest.mark.parametrize('identity', ['demolab__left_right','demolab__line_strength'])
def test_event_first_starters_test_ready_and_run_without_ui_edits(lab,tmp_path,identity):
    import sys
    from simulations.run import simulate
    from scripts.validate_run import validate_run
    enable(lab)
    if identity == EXPERIMENT:
        assert execute_user_action(ROOT,'preview',STIMULUS,{})==0
        ext.publish(ROOT,'stimulus',STIMULUS)
    assert execute_user_action(ROOT,'test',identity,{'trial_count':4})==0
    ext.publish(ROOT,'experiment',identity)
    assert ext.status(ROOT,'experiment',identity)=='ready'
    spec=get_experiment(identity)
    module=sys.modules[spec.procedure.__module__]
    assert callable(module.trial_events) and module.make_trial.__wrapped__ is module.trial_events
    methods=('adaptive','constant_stimuli') if identity.endswith('strength') else (None,)
    for method in methods:
        values={'trial_count':4}
        if method:values.update(contrast_method=method,fixed_contrasts='0,.1',fixed_repetitions=2)
        a,_=simulate(repo_root=ROOT,data_root=tmp_path/'starter_runs',experiment_id=identity,values=values,analyse=False)
        assert a.status=='completed'
        trace=json.loads((a.run_directory/'session_events.json').read_text())
        assert trace['status']=='completed' and len(trace['events'])==2
        assert trace['events'][0]['readiness']['key']=='SPACE'
        assert all(s['stimulus_id']=='fixation_cross' for s in trace['resolved_stimuli'].values())
        assert all(c.passed for c in validate_run(a.run_directory))
    assert ext.status(ROOT,'experiment',identity)=='ready'


def test_archived_pre_stage_c_extension_retains_legacy_api_and_empty_opening(lab,tmp_path):
    from simulations.run import simulate
    from scripts.validate_run import validate_run
    source=lab/'experiments'/(EXPERIMENT+'.py')
    source.write_bytes((ROOT/'tests/fixtures/legacy_stage_b_extension.py.txt').read_bytes())
    original=source.read_bytes()
    enable(lab)
    assert execute_user_action(ROOT,'preview',STIMULUS,{})==0
    ext.publish(ROOT,'stimulus',STIMULUS)
    assert execute_user_action(ROOT,'test',EXPERIMENT,{'trial_count':3})==0
    ext.publish(ROOT,'experiment',EXPERIMENT)
    assert not get_experiment(EXPERIMENT).session_start.phases
    a,_=simulate(repo_root=ROOT,data_root=tmp_path/'legacy_runs',experiment_id=EXPERIMENT,
                 values={'trial_count':3},analyse=False)
    assert a.status=='completed' and a.accepted_trials==3
    assert not (a.run_directory/'session_events.json').exists()
    assert all(c.passed for c in validate_run(a.run_directory))
    assert source.read_bytes()==original and ext.status(ROOT,'experiment',EXPERIMENT)=='ready'


def test_new_local_parameter_has_generic_review_edit_route_and_both_methods(lab,tmp_path):
    """Create a local study by extending the documented shared-method example."""
    from textual.widgets import Button,DataTable,Input,Select
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp,ReviewScreen,ExperimentParametersScreen
    from simulations.run import simulate
    from scripts.validate_run import validate_run
    identity="demolab__line_strength"
    source=lab/"experiments"/(identity+".py")
    text=source.read_text(encoding="utf-8")
    text=text.replace('FIELDS = (', 'FIELDS = (\n    ConfigField("audit_length_deg", "Audit line length", "float", .8, minimum=.1, maximum=3., units="degrees", section="Stimulus conditions", help_text="Full visible line length; changes the vertical extent."),',1)
    text=text.replace('run.stimulus_parameters(intensity=', 'run.stimulus_parameters(length_deg=run.values["audit_length_deg"], intensity=',1)
    text=text.replace('supports_simulation=True,', 'stimulus_parameter_controls={"target":{"length_deg":"audit_length_deg"}}, supports_simulation=True,',1)
    source.write_text(text,encoding="utf-8")
    enable(lab)
    assert execute_user_action(ROOT,"test",identity,{"trial_count":3}) == 0
    ext.publish(ROOT,"experiment",identity)
    assert ext.status(ROOT,"experiment",identity)=="ready"
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"novice_data")
        async with app.run_test(size=(120,45)) as pilot:
            app.query_one("#participant",Input).value="LOCAL_AUDIT"
            app.query_one("#experiment",Select).value=identity
            await pilot.pause()
            app.screen.query_one("#configure",Button).press()
            await pilot.pause()
            app.screen.query_one("#review",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,ReviewScreen)
            review=app.screen
            row=next(i for i,a in enumerate(review._row_authorities)
                     if a["status"]=="Experiment-controlled" and a["field"]=="audit_length_deg")
            review.query_one("#resolved-settings-table",DataTable).move_cursor(row=row)
            review.query_one("#review-edit-value",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,ExperimentParametersScreen)
            widget=app.screen.query_one("#field-audit-length-deg",Input)
            assert widget.has_focus
            widget.value="1.4"
            app.screen.query_one("#review",Button).press()
            await pilot.pause()
            assert float(review.query_one("#resolved-settings-table",DataTable).get_row_at(row)[2])==1.4
    asyncio.run(scenario())
    for method in ("adaptive","constant_stimuli"):
        artifact,_=simulate(repo_root=ROOT,data_root=tmp_path/"synthetic",experiment_id=identity,
            values={"audit_length_deg":1.4,"contrast_method":method,"trial_count":4,
                    "fixed_contrasts":"0,.1","fixed_repetitions":2},analyse=False)
        assert artifact.status=="completed"
        assert not [(c.name,c.detail) for c in validate_run(artifact.run_directory) if not c.passed]
        manifest=json.loads((artifact.run_directory/"manifest.json").read_text(encoding="utf-8"))
        assert manifest["experiment_values"]["audit_length_deg"]==1.4
    old=ext.fingerprint(ROOT)
    source.write_bytes(source.read_bytes()+b"\n# local scientific revision\n")
    assert ext.fingerprint(ROOT)!=old
    assert ext.status(ROOT,"experiment",identity)=="draft"


def ready(lab):
    enable(lab)
    assert execute_user_action(ROOT, 'preview', STIMULUS, {}) == 0
    ext.publish(ROOT, 'stimulus', STIMULUS)
    assert execute_user_action(ROOT, 'test', EXPERIMENT, {'trial_count':3}) == 0
    ext.publish(ROOT, 'experiment', EXPERIMENT)


def test_opt_in_and_builtin_discovery(lab):
    official = {s.id for s in list_experiments()}
    assert ext.configured(ROOT) is None
    with pytest.raises(ValueError,match='trust'):
        ext.configure(ROOT,lab)
    enable(lab)
    assert get_stimulus(STIMULUS).origin_namespace == 'demolab'
    assert EXPERIMENT not in {s.id for s in list_experiments()}
    assert set(official) <= {s.id for s in list_experiments()}
    ext.configure(ROOT)
    assert {s.id for s in list_experiments()} == official
    with pytest.raises(ValueError,match='Unknown stimulus'):
        get_stimulus(STIMULUS)


@pytest.mark.parametrize("method", ["adaptive", "constant_stimuli"])
def test_local_shared_method_example_review_execution_and_validation(lab, tmp_path, method):
    from simulations.run import simulate
    from scripts.validate_run import validate_run
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from psychophysics_lab.ui.settings_review import describe_settings
    identity = "demolab__line_strength"
    enable(lab)
    assert execute_user_action(ROOT, "test", identity, {"trial_count": 4}) == 0
    ext.publish(ROOT, "experiment", identity)
    spec = get_experiment(identity)
    values = spec.normalise_values({"contrast_method": method, "trial_count": 4,
                                  "fixed_contrasts": "0,0.1", "fixed_repetitions": 2})
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    description = describe_settings(spec, values, snapshots)
    assert description["resolution"]["trial_selection_method"] == method
    artifact, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data",
                           experiment_id=identity, values=values, seed=16, analyse=False)
    assert artifact.status == "completed"
    assert artifact.accepted_trials == (8 if method == "constant_stimuli" else 4)
    assert not [c for c in validate_run(artifact.run_directory) if not c.passed]
    if method == "constant_stimuli":
        import csv
        with artifact.trial_log_file.open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        assert all(r["staircase_id"] == r["reversal_count"] == "" for r in rows)
        assert {float(r["stimulus_condition"]) for r in rows} == {1, 2}


def test_real_preview_simulation_provenance_and_offline_read(lab,tmp_path):
    before={p.relative_to(lab).as_posix():p.read_bytes() for p in lab.rglob('*') if p.is_file()}
    ready(lab)
    assert not ext._development
    assert ext.status(ROOT,'experiment',EXPERIMENT)=='ready'
    assert (tmp_path/'development_data/previews'/f'{STIMULUS}.png').is_file()
    from simulations.run import simulate
    artifacts,_=simulate(repo_root=ROOT,data_root=tmp_path/'simulated',experiment_id=EXPERIMENT,values={'trial_count':5},analyse=False)
    assert artifacts.status=='completed'
    run=artifacts.run_directory
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    provenance=manifest['laboratory_extensions']
    assert provenance['namespace']=='demolab'
    assert provenance['experiment_identity']=={'namespace':'demolab','id':EXPERIMENT}
    assert provenance['source_sha256']['stimulus_library.py']==hashlib.sha256((lab/'stimulus_library.py').read_bytes()).hexdigest()
    assert 'presets/left_right.json' in provenance['source_sha256']
    assert str(lab) not in json.dumps(provenance)
    assert manifest['experiment_values']['trial_count']==5
    assert manifest['trial_schema_version']==1
    import csv
    with (run/'trials.tsv').open(encoding='utf-8') as stream:
        rows=list(csv.DictReader(stream,delimiter='\t'))
    assert len(rows)==5 and len(rows[0])==20
    assert [int(row['target_alternative']) for row in rows]==[0,1,0,1,0]
    originals={p.name:p.read_bytes() for p in run.iterdir() if p.is_file()}
    assert before=={p.relative_to(lab).as_posix():p.read_bytes() for p in lab.rglob('*') if p.is_file()}
    ext.configure(ROOT)
    shutil.rmtree(lab)
    from psychophysics_lab.data.reader import load_run
    loaded=load_run(run)
    assert loaded is not None
    assert originals=={p.name:p.read_bytes() for p in run.iterdir() if p.is_file()}
    # All science bytes were untouched by import/testing/Ready/simulation.
    copied=ROOT/'examples/laboratory_extensions'
    assert before=={p.relative_to(copied).as_posix():p.read_bytes() for p in copied.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


@pytest.mark.parametrize('relative',['stimulus_library.py','experiments/demolab__left_right.py','presets/left_right.json'])
def test_modified_source_invalidates_exact_revision(lab,relative):
    enable(lab);ext.load(ROOT,development=True)
    fp=ext.fingerprint(ROOT)
    ext.record_test(ROOT,'experiment',EXPERIMENT,fp)
    ext.publish(ROOT,'experiment',EXPERIMENT)
    path=lab/relative;path.write_bytes(path.read_bytes()+b'\n')
    assert ext.status(ROOT,'experiment',EXPERIMENT)=='draft'
    with pytest.raises(ValueError,match='successful'):
        ext.publish(ROOT,'experiment',EXPERIMENT)
    with pytest.raises(ValueError,match='changed since import'):
        ext.check_run(ROOT,get_experiment(EXPERIMENT),{})


@pytest.mark.parametrize('bad',['../outside.py','C:/private.py','experiments/../../outside.py','experiments\\bad.py'])
def test_source_containment(lab,bad):
    with pytest.raises(ValueError): ext.source_at(lab,bad)


def test_reject_nested_root():
    with pytest.raises(ValueError,match='separate'):
        ext.validate_root(ROOT/'examples/laboratory_extensions',ROOT)


@pytest.mark.skipif(os.name != 'nt', reason='Windows junctions require cmd /c mklink /J')
def test_reject_windows_junction(lab,tmp_path):
    target=tmp_path/'other';target.mkdir()
    import subprocess
    link=lab/'experiments'/'linked'
    result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True)
    assert result.returncode==0,result.stderr
    try:
        ext.configure(ROOT,lab,trusted=True)
        assert 'root' in ext.load(ROOT)
        assert get_experiment('example_experiment')
    finally:
        link.rmdir()


@pytest.mark.skipif(os.name != 'posix', reason='Native POSIX symlink containment')
def test_reject_posix_symlink(lab,tmp_path):
    target=tmp_path/'other';target.mkdir()
    outside=target/'outside.py'
    original=b'raise AssertionError("External symlink source must not execute")\n'
    outside.write_bytes(original)
    link=lab/'experiments'/'linked'
    link.symlink_to(target,target_is_directory=True)
    try:
        with pytest.raises(ValueError,match='Symlink/junction'):
            ext.source_at(lab,'experiments/linked/outside.py')
        ext.configure(ROOT,lab,trusted=True)
        errors=ext.load(ROOT)
        assert 'Symlink/junction' in errors['root']
        assert get_experiment('example_experiment')
        assert outside.read_bytes()==original
    finally:
        link.unlink()


@pytest.mark.parametrize('replacement',[
    'import missing_dependency_issue80\nSPEC = None\n',
    'this is invalid Python !!!\n',
])
def test_import_failures_do_not_break_official_registry(lab,replacement):
    (lab/'experiments'/f'{EXPERIMENT}.py').write_text(replacement,encoding='utf-8')
    ext.configure(ROOT,lab,trusted=True)
    assert ext.load(ROOT,development=True)
    assert get_experiment('example_experiment')


def test_collision_never_overwrites_official_stimulus(lab):
    original=get_stimulus('example_stimulus')
    path=lab/'stimulus_library.py'
    path.write_text(path.read_text(encoding='utf-8').replace(STIMULUS,'example_stimulus'),encoding='utf-8')
    ext.configure(ROOT,lab,trusted=True)
    assert ext.load(ROOT)
    assert get_stimulus('example_stimulus') is original


def test_draft_cannot_run_outside_explicit_development(lab,tmp_path):
    enable(lab);ext.load(ROOT,development=True)
    from simulations.run import simulate
    with pytest.raises(ValueError,match='not software Ready'):
        simulate(repo_root=ROOT,data_root=tmp_path/'simulation',experiment_id=EXPERIMENT,analyse=False)


def test_missing_root_and_source_inspection(lab):
    enable(lab)
    from psychophysics_lab.ui.editor import editor_command
    command=editor_command(ROOT,lab/'stimulus_library.py',executable='notepad.exe')
    assert command[-1]==str(lab/'stimulus_library.py')
    shutil.rmtree(lab)
    assert ext.load(ROOT)
    assert get_experiment('example_experiment')


def test_framework_relocation_keeps_extension_identity(lab,tmp_path):
    enable(lab)
    original=ext.source_hashes(ROOT)
    relocated=tmp_path/'framework-new';relocated.mkdir()
    assert ext.configured(relocated)==ext.configured(ROOT)
    assert ext.source_hashes(relocated)==original


def test_tui_catalogue_review_and_source_navigation(lab,tmp_path):
    ready(lab)
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp,ExperimentConfigScreen,ReviewScreen,_source_inventory
    from textual.widgets import Select,Button,Input,Static
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(120,40)) as pilot:
            app.query_one('#participant',Input).value='EXTENSION_TEST'
            app.query_one('#experiment',Select).value=EXPERIMENT
            app.query_one('#configure',Button).press();await pilot.pause()
            assert isinstance(app.screen,ExperimentConfigScreen)
            app.screen.query_one('#review',Button).press();await pilot.pause()
            assert isinstance(app.screen,ReviewScreen)
            assert any(path==lab/'experiments'/f'{EXPERIMENT}.py' for _,path in _source_inventory(ROOT,get_experiment(EXPERIMENT)))
            app.open_hub_page('experiments');await pilot.pause()
            assert 'demolab' in str(app.screen.query_one('#extensions-status',Static).render())
            app.open_hub_page('stimuli');await pilot.pause()
            # The bundle now has two independent stimulus classes. Select the
            # established reference explicitly; catalogue sort order is not a
            # scientific or source-navigation contract.
            app.screen.query_one('#author-component',Select).value=STIMULUS
            await pilot.pause()
            assert app.screen.query_one('#author-component',Select).value==STIMULUS
    asyncio.run(scenario())


def test_authoring_optional_json_opens_external_declared_preset(lab, tmp_path, monkeypatch):
    """The Build Experiments JSON button must not assume framework config paths."""
    ready(lab)
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    from textual.widgets import Select, Button
    opened = []

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / "data")
        async with app.run_test(size=(120, 40)) as pilot:
            monkeypatch.setattr(app, "inspect_source", lambda path: opened.append(Path(path)))
            app.open_hub_page("experiments")
            await pilot.pause()
            app.screen.query_one("#author-component", Select).value = EXPERIMENT
            app.screen.query_one("#author-json", Button).press()
            await pilot.pause()

    asyncio.run(scenario())
    assert opened == [lab / "presets" / "left_right.json"]


def test_relative_helper_uses_current_bytes_and_is_fingerprinted(lab):
    import os, sys
    helper=lab/'experiments/helper.py';helper.write_text('VALUE = 1\n',encoding='utf-8')
    path=lab/'experiments'/f'{EXPERIMENT}.py'
    path.write_text('from .helper import VALUE\n'+path.read_text(encoding='utf-8'),encoding='utf-8')
    enable(lab);ext.load(ROOT,development=True)
    assert sys.modules['_psycolab_lab_demolab.experiments.helper'].VALUE==1
    original_time=helper.stat().st_mtime_ns
    ext.unload()
    helper.write_text('VALUE = 2\n',encoding='utf-8')
    os.utime(helper,ns=(original_time,original_time))
    assert not ext.load(ROOT,development=True)
    assert sys.modules['_psycolab_lab_demolab.experiments.helper'].VALUE==2
    assert 'experiments/helper.py' in ext.source_hashes(ROOT)


def test_duplicate_external_stimuli_are_rolled_back(lab):
    path=lab/'stimulus_library.py'
    path.write_text(path.read_text(encoding='utf-8')+'\nclass DuplicateLine(LaboratoryLine):\n    pass\n',encoding='utf-8')
    ext.configure(ROOT,lab,trusted=True)
    assert 'Duplicate' in str(ext.load(ROOT))
    with pytest.raises(ValueError,match='Unknown stimulus'):
        get_stimulus(STIMULUS)


def test_saved_ready_state_requires_same_sources_on_restart(lab):
    enable(lab);ext.load(ROOT,development=True)
    ext.record_test(ROOT,'experiment',EXPERIMENT,ext.fingerprint(ROOT))
    ext.publish(ROOT,'experiment',EXPERIMENT)
    ext.unload();assert not ext.load(ROOT)
    assert get_experiment(EXPERIMENT)
    ext.unload()
    path=lab/'stimulus_library.py';path.write_bytes(path.read_bytes()+b'\n')
    assert not ext.load(ROOT)
    with pytest.raises(KeyError): get_experiment(EXPERIMENT)


def test_software_ready_does_not_qualify_physical_display(lab,tmp_path,monkeypatch):
    ready(lab)
    from psychophysics_lab.core.runner import run_request
    from psychophysics_lab.config.models import SetupRequest
    called=[]
    monkeypatch.setattr('psychophysics_lab.core.display.preflight_fullscreen_display',lambda *a:called.append(a))
    spec=get_experiment(EXPERIMENT)
    with pytest.raises(ValueError,match='Human acquisition blocked'):
        run_request(SetupRequest('H001','new',EXPERIMENT,'legacy_reference_display',spec.field_defaults()),repo_root=ROOT,data_root=tmp_path/'human')
    assert not called
    assert not (tmp_path/'human').exists()


def test_unsupported_readiness_file_is_not_rewritten(lab):
    enable(lab)
    path=ext._records_path(ROOT);path.parent.mkdir(parents=True,exist_ok=True)
    before=b'{"schema_version": 99, "components": {}}'
    path.write_bytes(before)
    with pytest.raises(ValueError,match='Unsupported'):
        ext.publish(ROOT,'experiment',EXPERIMENT)
    assert path.read_bytes()==before


def test_config_root_or_data_cannot_overlap_extensions(lab):
    with pytest.raises(ValueError,match='separate'):
        ext.configure(ROOT,lab,trusted=True,data_root=lab/'data')
    with pytest.raises(ValueError,match='absolute'):
        ext.configure(ROOT,'relative_extensions',trusted=True)


def test_cli_enable_disable_reuses_local_preferences(lab):
    from psychophysics_lab.app import _main
    assert _main(['--extensions-enable',str(lab),'--trust-extension-code'])==0
    assert ext.configured(ROOT)[0]==lab
    assert _main(['--extensions-disable'])==0
    assert ext.configured(ROOT) is None


def test_external_review_opens_actual_python_and_preset(lab,tmp_path,monkeypatch):
    ready(lab)
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp,ExperimentParametersScreen
    from textual.widgets import Button
    calls=[]
    monkeypatch.setattr('psychophysics_lab.ui.setup.open_source',lambda root,path,**kwargs:calls.append(path))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(120,40)) as pilot:
            spec=get_experiment(EXPERIMENT)
            app.push_screen(ExperimentParametersScreen(data_root=app.data_root,participant_id='TEST',session_mode='new',experiment=spec,monitor_profile_id='legacy_reference_display',defaults=spec.field_defaults()))
            await pilot.pause();app.screen.query_one('#review',Button).press();await pilot.pause()
            screen=app.screen
            assert screen._file_sources['experiment']==lab/'presets/left_right.json'
            row=next(i for i,t in enumerate(screen._file_targets) if t['kind']=='python' and t['path']==lab/'experiments'/f'{EXPERIMENT}.py')
            screen._open_review_file(row)
            await pilot.pause()
            assert calls[-1]==lab/'experiments'/f'{EXPERIMENT}.py'
    asyncio.run(scenario())



def test_external_adaptive_procedure_keeps_presented_contrast_and_reversals(lab,tmp_path,monkeypatch):
    """Same scientific source and response history, through the same real runner."""
    from dataclasses import dataclass
    import csv
    from simulations.run import simulate
    @dataclass
    class AlternatingObserver:
        calls:int=0
        def probability_correct(self,condition,state,stimuli):
            self.calls+=1
            return float(self.calls%2==1)
    source=(ROOT/'src/psychophysics_lab/experiments/contrast_sensitivity.py').read_text(encoding='utf-8')
    source=source.replace('def definition(identity="contrast_sensitivity"):', 'def definition(identity="demolab__adaptive"):')
    source=source.replace('data_directory_name="contrast_sensitivity"','data_directory_name="demolab__adaptive"')
    source=source.replace('"src/psychophysics_lab/experiments/contrast_sensitivity.py"','"experiments/demolab__adaptive.py"')
    (lab/'experiments/demolab__adaptive.py').write_text(source,encoding='utf-8')
    enable(lab);assert not ext.load(ROOT,development=True)
    monkeypatch.setattr(ext,'_development',True)
    values={'staircases_per_condition':1,'max_trials':12,'n_down':1,'n_up':1,
        'reversal_termination':1,'threshold_reversals':1,'initial_one_down_limit':0,
        'logUNIT_DW':.1,'logUNIT_UP':.1,'frequencies_cpd':'2','starting_contrast':.2}
    outputs=[]
    for identity in ('contrast_sensitivity','demolab__adaptive'):
        result,_=simulate(repo_root=ROOT,data_root=tmp_path/'data',experiment_id=identity,values=values,observer=AlternatingObserver(),analyse=False)
        assert result.status=='completed' and result.accepted_trials==2
        with result.trial_log_file.open(encoding='utf-8',newline='') as stream:
            outputs.append(list(csv.DictReader(stream,delimiter='\t')))
    assert outputs[0]==outputs[1]
    assert [row['reversal'] for row in outputs[1]]==['0','1']


def test_framework_update_and_relocation_preserve_science_config_and_data(lab,tmp_path):
    import subprocess
    enable(lab)
    config=ext.config_root(ROOT)
    evidence=config/'profiles/measurement.json';evidence.parent.mkdir();evidence.write_text('{"measured": true}',encoding='utf-8')
    data=tmp_path/'archive';data.mkdir();(data/'trials.tsv').write_text('original observations',encoding='utf-8')
    def snapshot():
        return {str(p):p.read_bytes() for root in (lab,config,data) for p in root.rglob('*') if p.is_file()}
    before=snapshot()
    checkout=tmp_path/'framework';checkout.mkdir()
    def git(*args):
        subprocess.run(['git','-C',str(checkout),*args],check=True,capture_output=True)
    git('init');git('config','user.name','Extension test');git('config','user.email','test@example.invalid')
    tracked=checkout/'framework.txt';tracked.write_text('revision one',encoding='utf-8')
    git('add','.');git('commit','-m','initial')
    tracked.write_text('revision two',encoding='utf-8');git('add','.');git('commit','-m','framework update')
    relocated=tmp_path/'framework-relocated'
    checkout.rename(relocated)
    assert ext.configured(relocated)==ext.configured(ROOT)
    assert snapshot()==before



@pytest.mark.parametrize("relative", [
    "core/presentation.py",
    "core/scene_primitives.py",
    "core/trial_execution.py",
    "core/timeline.py",
    "core/runner.py",
    "analysis/primary.py",
    "data/trials.py",
    "methods/contrast.py",
    "methods/probe.py",
    "methods/teaching.py",
])
def test_shared_execution_update_invalidates_lab_ready_status_without_touching_real_code(
    tmp_path, monkeypatch, relative
):
    """Fingerprints include scientific execution dependencies, not just library code."""
    # Use a complete isolated COPY of the framework tree: no real source,
    # local preferences or acquired data can be modified by this test.
    checkout = tmp_path / "copied_checkout"
    framework = checkout / "src" / "psychophysics_lab"
    shutil.copytree(ROOT / "src" / "psychophysics_lab", framework)
    monkeypatch.setattr(ext, "source_hashes", lambda _: {"stimulus_library.py": "test-copy"})
    readiness = tmp_path / "isolated_config" / "extension_readiness.json"
    readiness.parent.mkdir(parents=True)
    monkeypatch.setattr(ext, "_records_path", lambda _: readiness)

    previous = ext.fingerprint(checkout)
    key = "experiment:demolab__left_right"
    readiness.write_text(json.dumps({
        "schema_version": 1,
        "components": {key: {"fingerprint": previous, "ready": True}},
    }), encoding="utf-8")
    assert ext.status(checkout, "experiment", EXPERIMENT) == "ready"

    copied_file = framework / relative
    copied_file.write_bytes(copied_file.read_bytes() + b"\n# copied-source-change\n")

    assert ext.fingerprint(checkout) != previous
    assert ext.status(checkout, "experiment", EXPERIMENT) == "draft"
    with pytest.raises(ValueError, match="successful --dev-preview or --dev-test"):
        ext.publish(checkout, "experiment", EXPERIMENT)


def test_framework_fingerprint_ignores_location_and_docs(tmp_path, monkeypatch):
    """Moving identical source or editing prose cannot silently change scientific bytes."""
    first = tmp_path / "first_checkout" / "src" / "psychophysics_lab"
    second = tmp_path / "second_checkout" / "src" / "psychophysics_lab"
    shutil.copytree(ROOT / "src" / "psychophysics_lab", first)
    shutil.copytree(first, second)
    monkeypatch.setattr(ext, "source_hashes", lambda _: {"manifest": "identical"})
    assert ext.fingerprint(first.parents[1]) == ext.fingerprint(second.parents[1])
    (second.parents[1] / "README.md").write_text("Changed prose only", encoding="utf-8")
    assert ext.fingerprint(first.parents[1]) == ext.fingerprint(second.parents[1])
