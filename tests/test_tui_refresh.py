"""Refresh preserves setup, applies real saved files, and never launches a run."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys

from textual.widgets import Button, Input, Static

from psychophysics_lab.ui import refresh
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen, ExperimentConfigScreen
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.config.stimulus_parameters import document_for

ROOT = Path(__file__).resolve().parents[1]


async def configure(app, pilot, to_review=True):
    spec = get_experiment('line_position_baseline')
    values = spec.normalise_values({'probe_vertical_offset_deg': .2, 'positions_deg': '0',
                                   'staircases_per_condition': 1, 'max_trials': 3})
    screen = ExperimentConfigScreen(data_root=app.data_root, participant_id='REFRESH', session_mode='new',
        experiment=spec, monitor_profile_id='legacy_reference_display', defaults=values)
    await app.push_screen(screen)
    await pilot.pause()
    if to_review:
        screen.query_one('#review', Button).press()
        await pilot.pause()
        assert isinstance(app.screen, ReviewScreen)
    return screen


def test_refresh_button_returns_handoff_preserving_review_without_running(tmp_path, monkeypatch):
    checked = []
    monkeypatch.setattr(refresh, 'check_refresh', lambda state, root: checked.append((state, root)))
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(220,65)) as pilot:
            await configure(app, pilot)
            app.screen.query_one('#refresh-psycolab', Button).press()
            await app.workers.wait_for_complete()
        assert isinstance(app.return_value, refresh.RefreshRequest)
        assert checked[0][0]['page'] == 'review'
        assert checked[0][0]['request']['participant_id'] == 'REFRESH'
        assert checked[0][0]['overrides']['max_trials'] == 3
        assert 'first' in checked[0][0]['follow_defaults']
        assert not (tmp_path/'data'/'participants').exists()
    asyncio.run(scenario())


def test_f5_failed_check_keeps_configuration_and_unsaved_input(tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError('SyntaxError: missing closing bracket in stimulus_library.py')
    monkeypatch.setattr(refresh, 'check_refresh', fail)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(220,65)) as pilot:
            config = await configure(app, pilot, False)
            config.query_one('#field-probe-vertical-offset-deg', Input).value = '.37'
            await pilot.press('f5')
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.screen is config
            assert config.query_one('#field-probe-vertical-offset-deg', Input).value == '.37'
            assert not config.query_one('#refresh-psycolab', Button).disabled
            assert app.return_value is None
    asyncio.run(scenario())


def test_restores_review_with_updated_class_defaults_and_back_configuration(tmp_path, monkeypatch):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(220,65)) as pilot:
            await configure(app, pilot)
            state = refresh.capture_state(app)
        old = get_stimulus('detection_scene')
        new = replace(old, parameters=tuple(replace(field, default=1.73) if field.key == 'probe_length_deg' else field
                                             for field in old.parameters))
        monkeypatch.setitem(sys.modules['psychophysics_lab.stimuli.registry']._REGISTRY, old.id, new)
        resumed = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data', refresh_state=state)
        async with resumed.run_test(size=(220,65)) as pilot:
            await pilot.pause()
            assert isinstance(resumed.screen, ReviewScreen)
            request = resumed.screen.request
            assert request.stimulus_snapshots['first']['document']['parameters']['probe_length_deg'] == 1.73
            assert request.experiment_values['probe_vertical_offset_deg'] == .2
            assert request.experiment_values['max_trials'] == 3
            resumed.verify_settings_current(request)
            resumed.screen.query_one('#back', Button).press()
            await pilot.pause()
            panel = next(p for p in resumed.screen.query(StimulusParametersPanel) if p.slot == 'first')
            assert panel.current()['document']['parameters']['probe_length_deg'] == 1.73
    asyncio.run(scenario())


def test_saved_json_wins_over_class_defaults_and_is_reloaded(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(220,65)) as pilot:
            config = await configure(app, pilot, False)
            path = tmp_path/'chosen dimensions.json'
            stimulus = get_stimulus('detection_scene')
            path.write_text(json.dumps(document_for(stimulus)), encoding='utf-8')
            next(p for p in config.query(StimulusParametersPanel) if p.slot=='first').load(path)
            config.query_one('#review', Button).press()
            await pilot.pause()
            state = refresh.capture_state(app)
        document = document_for(stimulus)
        document['parameters']['probe_length_deg'] = 2.1
        path.write_text(json.dumps(document), encoding='utf-8')
        prepared = refresh.prepare_state(state, ROOT)
        assert prepared['prepared_request']['stimulus_snapshots']['first']['document']['parameters']['probe_length_deg'] == 2.1
        assert str(path) in prepared['files']
        path.write_text('{broken', encoding='utf-8')
        import pytest
        with pytest.raises(ValueError):
            refresh.prepare_state(state, ROOT)
    asyncio.run(scenario())


def test_repeated_refresh_supervisor_uses_same_handoff_without_nested_processes(tmp_path, monkeypatch):
    monkeypatch.delenv(refresh.STATE_ENV, raising=False)
    calls = []
    def run(args, **kwargs):
        path = Path(kwargs['env'][refresh.STATE_ENV])
        assert path.is_file()
        calls.append((args, kwargs, json.loads(path.read_text(encoding='utf-8'))))
        return subprocess.CompletedProcess(args, refresh.REFRESH_EXIT if len(calls) < 3 else 0)
    monkeypatch.setattr(refresh.subprocess, 'run', run)
    state = {'repo_root':str(ROOT), 'data_root':str(tmp_path/'data')}
    assert refresh.launch_refreshed(refresh.RefreshRequest(state), ROOT) == 0
    assert len(calls)==3
    assert len({c[1]['env'][refresh.STATE_ENV] for c in calls})==1
    assert len({c[1]['env']['PYTHONPYCACHEPREFIX'] for c in calls})==3
    assert not Path(calls[0][1]['env'][refresh.STATE_ENV]).exists()


def test_child_refresh_returns_to_supervisor_and_preserves_error_exit(tmp_path, monkeypatch):
    path = tmp_path/'navigation.json'
    monkeypatch.setenv(refresh.STATE_ENV, str(path))
    monkeypatch.setattr(refresh.subprocess, 'run', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('must not spawn nested child')))
    assert refresh.launch_refreshed(refresh.RefreshRequest({'page':'review'}), ROOT)==refresh.REFRESH_EXIT
    assert json.loads(path.read_text(encoding='utf-8'))=={'page':'review'}
    monkeypatch.delenv(refresh.STATE_ENV)
    monkeypatch.setattr(refresh.subprocess, 'run', lambda args, **kwargs: subprocess.CompletedProcess(args, 1))
    assert refresh.launch_refreshed(refresh.RefreshRequest({'page':'setup'}), ROOT)==1


def test_real_fresh_interpreter_reads_changed_python_and_reports_syntax_error(tmp_path):
    """Edit a disposable source copy, never the researcher's working library."""
    copied = tmp_path/'repo'
    shutil.copytree(ROOT/'src', copied/'src', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'configs', copied/'configs')
    shutil.copyfile(ROOT/'pyproject.toml', copied/'pyproject.toml')
    state = {'repo_root':str(copied), 'data_root':str(tmp_path/'data'), 'source_paths':[]}
    # First check imports and renders the untouched source copy.
    refresh.check_refresh(state, copied)
    source = copied/'src/psychophysics_lab/stimulus_library.py'
    text = source.read_text(encoding='utf-8')
    source.write_text(text+'\nREFRESH_TEST_MARKER = 7391\n', encoding='utf-8')
    env = refresh._environment(copied, tmp_path/'fresh-bytecode')
    result = subprocess.run([sys.executable, '-c',
        'import psychophysics_lab.stimulus_library as s; print(s.REFRESH_TEST_MARKER); print(s.__file__)'],
        cwd=copied, env=env, capture_output=True, text=True, timeout=45)
    assert result.returncode==0, result.stderr
    assert '7391' in result.stdout and str(source) in result.stdout
    # Resolve an actual Review request in the fresh process after changing the
    # stimulus class's declared length, while the test process still has old imports.
    from dataclasses import asdict
    from psychophysics_lab.config.models import SetupRequest
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    spec=get_experiment('line_position_baseline')
    values=spec.normalise_values({'probe_vertical_offset_deg':.2, 'positions_deg':'0', 'max_trials':3})
    stimuli=resolve_stimuli(spec,values,{},repo_root=ROOT)
    # Locate the actual default expression, independent of its value or
    # spelling (.133 and 0.133 are equally valid researcher edits).
    import ast
    call=next(node for node in ast.walk(ast.parse(text)) if isinstance(node,ast.Call)
              and isinstance(node.func,ast.Name) and node.func.id=='ConfigField'
              and node.args and isinstance(node.args[0],ast.Constant)
              and node.args[0].value=='probe_length_deg')
    default=call.args[3]
    assert default.lineno==default.end_lineno
    lines=text.splitlines(keepends=True)
    line=lines[default.lineno-1]
    lines[default.lineno-1]=line[:default.col_offset]+'1.78'+line[default.end_col_offset:]
    source.write_text(''.join(lines),encoding='utf-8')
    state.update(page='review', request=asdict(SetupRequest('REFRESH','new',spec.id,'legacy_reference_display',values,
                                                         data_root=str(tmp_path/'data'))),
        overrides={k:v for k,v in values.items() if v!={f.key:f.default for f in spec.fields}[k]},
        stimuli=stimuli, follow_defaults=list(stimuli), sources={'experiment':None,'stimuli':{}})
    path=tmp_path/'fresh-review.json'
    path.write_text(json.dumps(state),encoding='utf-8')
    script=('import json,sys; from pathlib import Path; from psychophysics_lab.ui.refresh import prepare_state; '
            's=json.loads(Path(sys.argv[1]).read_text()); r=prepare_state(s,Path(s["repo_root"])); '
            'print(r["prepared_request"]["stimulus_snapshots"]["first"]["document"]["parameters"]["probe_length_deg"])')
    result=subprocess.run([sys.executable,'-c',script,str(path)],cwd=copied,
                          env=refresh._environment(copied,tmp_path/'changed-default-bytecode'),capture_output=True,text=True,timeout=45)
    assert result.returncode==0, result.stderr
    assert result.stdout.strip()=='1.78'
    source.write_text(text+'\ndef broken(:\n', encoding='utf-8')
    import pytest
    with pytest.raises(ValueError, match='SyntaxError|invalid syntax'):
        refresh.check_refresh(state, copied)


def test_refresh_reloads_saved_experiment_json_and_returns_incomplete_configuration(tmp_path):
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(220,65)) as pilot:
            config = await configure(app, pilot, False)
            path = tmp_path/'experiment.json'
            document = {'schema_version':1, 'experiment_id':config.experiment.id,
                        'values':config._field_values()}
            path.write_text(json.dumps(document), encoding='utf-8')
            config.parameter_json_path = path
            state = refresh.capture_state(app)
        document['values']['starting_probe_intensity'] = 1.0
        path.write_text(json.dumps(document), encoding='utf-8')
        resumed = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data', refresh_state=state)
        async with resumed.run_test(size=(220,65)) as pilot:
            await pilot.pause()
            assert isinstance(resumed.screen, ExperimentConfigScreen)
            config = resumed.screen
            assert config._field_values()['starting_probe_intensity'] == 1.0
            assert config.parameter_json_path == path
            config.query_one('#review', Button).press()
            await pilot.pause()
            assert resumed.screen.request.experiment_values['starting_probe_intensity'] == 1.0
    asyncio.run(scenario())


def test_main_dispatches_refresh_without_acquisition_and_resumes_selected_workspace(tmp_path, monkeypatch):
    from psychophysics_lab import app as main_app
    from psychophysics_lab.ui import setup
    state = {'repo_root':str(ROOT), 'data_root':str(tmp_path/'selected workspace'), 'page':'setup'}
    path = tmp_path/'navigation.json'
    path.write_text(json.dumps(state), encoding='utf-8')
    monkeypatch.setenv(refresh.STATE_ENV, str(path))
    calls = []
    def tui(**kwargs):
        calls.append(kwargs)
        return refresh.RefreshRequest(state | {'page':'review'})
    monkeypatch.setattr(setup, 'run_setup_tui', tui)
    assert main_app._main([]) == refresh.REFRESH_EXIT
    assert calls[0]['data_root'] == Path(state['data_root'])
    assert calls[0]['refresh_state'] == state
    assert json.loads(path.read_text(encoding='utf-8'))['page']=='review'
    assert not (Path(state['data_root'])/'participants').exists()


def test_home_refresh_preserves_calibration_input_and_navigation(tmp_path):
    from psychophysics_lab.ui.setup import DisplayCheckScreen
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(220,65)) as pilot:
            app.open_hub_page('display')
            await pilot.pause()
            app.screen._go_to_stage('spatial', remember=False)
            field = next(w for w in app.screen.query(Input) if w.id.startswith('geometry-'))
            field.value = '12.345'
            name = field.id
            state = refresh.capture_state(app)
        resumed = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data', refresh_state=state)
        async with resumed.run_test(size=(220,65)) as pilot:
            await pilot.pause()
            assert isinstance(resumed.screen, DisplayCheckScreen)
            assert resumed.screen.active_calibration_stage=='spatial'
            assert resumed.screen.query_one('#'+name,Input).value=='12.345'
    asyncio.run(scenario())


def test_changes_during_refresh_are_preserved_instead_of_replaced(tmp_path, monkeypatch):
    import threading
    started, finished = threading.Event(), threading.Event()
    def check(*args):
        started.set()
        assert finished.wait(10)
    monkeypatch.setattr(refresh, 'check_refresh', check)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'data')
        async with app.run_test(size=(220,65)) as pilot:
            config = await configure(app, pilot, False)
            app.action_refresh_files()
            assert await asyncio.to_thread(started.wait, 10)
            config.query_one('#field-max-trials',Input).value='17'
            finished.set()
            await app.workers.wait_for_complete()
            assert app.screen is config and app.return_value is None
            assert config.query_one('#field-max-trials',Input).value=='17'
    asyncio.run(scenario())


def test_refresh_error_popup_excludes_unrelated_nonblocking_source_warning(tmp_path, monkeypatch):
    import pytest
    warning = (
        "contributions.py:86: RuntimeWarning: Invalid or untested published "
        "components were NOT loaded: experiment:new_probe_vertical_line_stimulus"
    )
    fatal = (
        "ValueError: Grating outer edge (multiples of sigma) "
        "(grating-cutoff-sigmas) = 0.5 is outside its permitted range [1.0, 5.0]."
    )
    def fail(args, **kwargs):
        return subprocess.CompletedProcess(
            args, 1, stdout="",
            stderr=warning + "\n" +
                   refresh.CHECK_ERROR_PREFIX + json.dumps(fatal) + "\n",
        )
    monkeypatch.setattr(refresh.subprocess, "run", fail)
    with pytest.raises(ValueError) as caught:
        refresh.check_refresh({"page": "setup"}, ROOT)
    assert str(caught.value) == fatal
    assert "new_probe_vertical_line_stimulus" not in str(caught.value)


def test_refresh_does_not_fail_on_unrelated_published_component_warning(tmp_path, monkeypatch):
    def success(args, **kwargs):
        return subprocess.CompletedProcess(
            args, 0, stdout="",
            stderr="contributions.py:86: RuntimeWarning: Invalid unrelated source was NOT loaded",
        )
    monkeypatch.setattr(refresh.subprocess, "run", success)
    refresh.check_refresh({"page": "setup"}, ROOT)
