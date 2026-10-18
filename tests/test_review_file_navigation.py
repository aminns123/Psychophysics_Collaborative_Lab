"""Real source navigation, ordinary JSON editing and atomic review reload."""
import asyncio
import json
from pathlib import Path

import pytest
from textual.coordinate import Coordinate
from textual.widgets import Button,DataTable,Input,Static

from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.config.stimulus_parameters import document_for,resolve_stimuli,snapshot
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.ui.review_files import export_current_json,targets_for_rows
from psychophysics_lab.ui.settings_review import describe_settings,review_rows
from psychophysics_lab.ui.setup import PsyCoLabSetupApp,ExperimentConfigScreen,ReviewScreen
from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel

ROOT=Path(__file__).resolve().parents[1]


def values():
    spec=get_experiment('line_position_baseline')
    return spec.normalise_values({'probe_vertical_offset_deg':.2,'positions_deg':'0',
        'staircases_per_condition':1,'max_trials':3})


async def review(app,pilot,preset=None):
    spec=get_experiment('line_position_baseline')
    screen=ExperimentConfigScreen(data_root=app.data_root,participant_id='FILE_NAV',session_mode='new',
        experiment=spec,monitor_profile_id='legacy_reference_display',defaults=values())
    app.push_screen(screen)
    await pilot.pause()
    if preset:
        next(panel for panel in screen.query(StimulusParametersPanel) if panel.slot=='first').load(preset)
    screen.query_one('#review',Button).press()
    await pilot.pause()
    assert isinstance(app.screen,ReviewScreen)
    return screen,app.screen,app.screen.query_one('#resolved-settings-table',DataTable)


def find_row(table,label,group=None):
    return next(index for index in range(table.row_count)
        if str(table.get_row_at(index)[1]).startswith(label) and (group is None or str(table.get_row_at(index)[0])==group))


async def click_cell(pilot,table,row,column,times=1):
    table.move_cursor(row=row,column=column)
    await pilot.pause()
    area=table._get_cell_region(Coordinate(row,column))
    offset=(area.x-round(table.scroll_x)+table.content_region.x-table.region.x+1,
            area.y-round(table.scroll_y)+table.content_region.y-table.region.y)
    if times==2:
        # Textual 1.0 Pilot mutates its mouse kwargs across double-click chains,
        # accidentally passing Click.chain to MouseDown. Send the two real Click
        # events through the same driver path without that unrelated driver bug.
        from textual.events import Click
        await pilot._post_mouse_events([Click],widget='#resolved-settings-table',offset=offset,button=1,times=2)
    else:
        await pilot.click('#resolved-settings-table',offset=offset)
    await pilot.pause()


def test_default_probe_cell_opens_its_actual_class_definition_without_creating_json(tmp_path,monkeypatch):
    opened=[]
    monkeypatch.setattr('psychophysics_lab.ui.setup.open_source',lambda root,path,line=1,**kwargs:opened.append((path,line)))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(240,65)) as pilot:
            _,screen,table=await review(app,pilot)
            assert len(table.columns)==5 and table.show_cursor and table.cursor_type=='cell'
            row=find_row(table,'Probe length','first')
            assert str(table.get_row_at(row)[4]).endswith('stimulus_library.py')
            assert not (app.local_config_root/'parameter_files').exists()
            await click_cell(pilot,table,row,2)
            assert not opened and table.cursor_coordinate==Coordinate(row,2)
            await pilot.press('enter')
            await pilot.pause()
            assert opened[-1][0]==ROOT/'src/psychophysics_lab/stimulus_library.py'
            assert 'probe_length_deg' in opened[-1][0].read_text(encoding='utf-8').splitlines()[opened[-1][1]-1]
            before=len(opened)
            await click_cell(pilot,table,row,2,times=2)
            assert len(opened)==before+1
            before=len(opened)
            await click_cell(pilot,table,row,4)
            assert len(opened)==before+1
            assert str(opened[-1][0]) in str(screen.query_one('#review-file-location',Static).renderable)
    asyncio.run(scenario())


def test_preset_link_edits_dimensions_and_reloads_values_used_by_actual_run(tmp_path,monkeypatch):
    from simulations.run import simulate
    from psychophysics_lab.researcher import RunContext
    stimulus=get_stimulus('detection_scene')
    path=tmp_path/'chosen probe.json'
    document=document_for(stimulus)
    path.write_text(json.dumps(document),encoding='utf-8')
    opened=[]
    monkeypatch.setattr('psychophysics_lab.ui.editor.open_parameter_file',lambda root,path,*args,**kwargs:opened.append((path,kwargs)))
    launch={}
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(240,65)) as pilot:
            parent,screen,table=await review(app,pilot,path)
            row=find_row(table,'Probe length','first')
            assert str(table.get_row_at(row)[4])==str(path)
            table.move_cursor(row=row,column=2)
            table.focus()
            await pilot.press('enter')
            await pilot.pause()
            assert opened[-1][0]==path and opened[-1][1]['allow_external_existing']
            changed=document_for(stimulus,document['parameters']|{'probe_length_deg':1.2,'probe_width_deg':.04})
            path.write_text(json.dumps(changed),encoding='utf-8')
            with pytest.raises(ValueError,match='Review again'):
                app.verify_settings_current(screen.request)
            screen.query_one('#review-reload-files',Button).press()
            await pilot.pause()
            app.verify_settings_current(screen.request)
            assert str(table.get_row_at(find_row(table,'Probe length','first'))[2])=='1.2'
            assert screen.request.stimulus_snapshots['first']['document']['parameters']['probe_width_deg']==.04
            launch['request']=screen.request
            screen.query_one('#back',Button).press()
            await pilot.pause()
            assert app.screen is parent
            panel=next(p for p in parent.query(StimulusParametersPanel) if p.slot=='first')
            assert panel.current()['document']['parameters']['probe_length_deg']==1.2
    asyncio.run(scenario())
    seen=[]
    original=RunContext.trial
    def capture(run,*args,**kwargs):
        seen.append(kwargs['parameters_by_slot']['first'])
        return original(run,*args,**kwargs)
    monkeypatch.setattr(RunContext,'trial',capture)
    request=launch['request']
    result,_=simulate(repo_root=ROOT,data_root=tmp_path/'runs',experiment_id=request.experiment_id,
        values=request.experiment_values,stimulus_snapshots=request.stimulus_snapshots,analyse=False)
    assert result.accepted_trials==3
    assert len(seen)==3 and all(p['probe_length_deg']==1.2 and p['probe_width_deg']==.04 for p in seen)


def test_unsaved_values_export_only_on_explicit_open_and_invalid_reload_is_atomic(tmp_path,monkeypatch):
    opened=[]
    monkeypatch.setattr('psychophysics_lab.ui.editor.open_parameter_file',lambda root,path,*args,**kwargs:opened.append(path))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(240,65)) as pilot:
            _,screen,table=await review(app,pilot)
            row=find_row(table,'Starting probe intensity','Experiment')
            assert 'Unsaved' in str(table.get_row_at(row)[4])
            table.move_cursor(row=row,column=2)
            table.focus()
            await pilot.press('enter')
            await pilot.pause()
            path=opened[-1]
            assert path.is_file() and str(table.get_row_at(row)[4])==str(path)
            document=json.loads(path.read_text(encoding='utf-8'))
            assert document['values']==screen.request.experiment_values
            original=screen.request
            path.write_text('{',encoding='utf-8')
            screen.query_one('#review-reload-files',Button).press()
            await pilot.pause()
            assert screen.request==original
            with pytest.raises(ValueError):
                app.verify_settings_current(screen.request)
            document['values']['starting_probe_intensity']=1.
            path.write_text(json.dumps(document),encoding='utf-8')
            screen.query_one('#review-reload-files',Button).press()
            await pilot.pause()
            assert screen.request.experiment_values['starting_probe_intensity']==1.
            app.verify_settings_current(screen.request)
    asyncio.run(scenario())


def test_export_preserves_an_existing_different_user_document(tmp_path):
    from psychophysics_lab.ui.parameter_files import working_path
    spec=get_experiment('line_position_baseline')
    first={'schema_version':1,'experiment_id':spec.id,'values':values()}
    original=export_current_json(tmp_path,spec,first)
    before=original.read_bytes()
    changed=first|{'values':values()|{'starting_probe_intensity':1.}}
    second=export_current_json(tmp_path,spec,changed)
    assert second!=original and original.read_bytes()==before
    assert json.loads(second.read_text(encoding='utf-8'))['values']['starting_probe_intensity']==1.


def test_trial_controlled_and_derived_cells_point_to_code_not_an_ineffective_preset():
    spec=get_experiment('line_position_baseline')
    selected=resolve_stimuli(spec,values(),repo_root=ROOT)
    description=describe_settings(spec,values(),selected)
    rows=review_rows(spec,values(),selected,description,refresh_hz=60)
    targets=targets_for_rows(spec,selected,description,rows,{'experiment':None,'stimuli':{}},ROOT)
    for index,row in enumerate(rows):
        if row[0]=='first' and row[1].startswith('Probe x'):
            assert targets[index]['path']==ROOT/'src/psychophysics_lab/experiments/line_position_baseline.py'
            assert 'Trial-controlled' in targets[index]['note']
        if row[0]=='Contrast' and row[1]=='Relative digital contrast':
            assert targets[index]['path'].name=='settings_review.py'
            assert 'Derived' in targets[index]['note']
        if row[0]=='Trial' and row[1]=='probe duration':
            assert targets[index]['kind']=='experiment_json' and targets[index]['key']=='stimulus_ms'


def test_old_frozen_snapshot_is_not_mislabelled_as_current_class_defaults():
    spec=get_experiment('line_position_baseline')
    selected=resolve_stimuli(spec,values(),repo_root=ROOT)
    stimulus=get_stimulus('detection_scene')
    selected['first']=snapshot(document_for(stimulus,selected['first']['document']['parameters']|{'probe_length_deg':.8}),
        file_identity='library_defaults')
    description=describe_settings(spec,values(),selected)
    rows=review_rows(spec,values(),selected,description)
    targets=targets_for_rows(spec,selected,description,rows,{'experiment':None,'stimuli':{}},ROOT)
    index=next(index for index,row in enumerate(rows) if row[0]=='first' and row[1].startswith('Probe length'))
    assert targets[index]['path'] is None and targets[index]['kind']=='stimulus_json'


def test_default_experiment_json_is_linked_without_an_unnecessary_copy(tmp_path):
    async def scenario():
        spec=get_experiment('example_experiment')
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(240,65)) as pilot:
            screen=ExperimentConfigScreen(data_root=tmp_path/'data',participant_id='SOURCE_JSON',session_mode='new',
                experiment=spec,monitor_profile_id='legacy_reference_display',defaults=spec.field_defaults())
            app.push_screen(screen)
            await pilot.pause()
            screen.query_one('#review',Button).press()
            await pilot.pause()
            table=app.screen.query_one('#resolved-settings-table',DataTable)
            row=find_row(table,'Number of trials','Experiment')
            assert str(table.get_row_at(row)[4])==str(ROOT/spec.default_config)
            assert not (app.local_config_root/'parameter_files').exists()
    asyncio.run(scenario())


def test_python_changes_require_a_fresh_process_not_a_silent_json_reload(tmp_path,monkeypatch):
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(240,65)) as pilot:
            _,screen,_=await review(app,pilot)
            source=str((ROOT/'src/psychophysics_lab/stimulus_library.py').resolve())
            monkeypatch.setitem(app.loaded_source_hashes,source,'different-loaded-code')
            before=screen.request
            screen.query_one('#review-reload-files',Button).press()
            await pilot.pause()
            assert screen.request==before
            assert 'Restart PsyCoLab' in str(screen.query_one('#review-status',Static).renderable)
    asyncio.run(scenario())


def test_missing_optional_source_metadata_does_not_make_review_a_gatekeeper(monkeypatch):
    from dataclasses import replace
    import psychophysics_lab.ui.review_files as links
    spec=replace(get_experiment('line_position_baseline'),source_paths=())
    monkeypatch.setattr(links.inspect,'getsourcefile',lambda _:None)
    selected=resolve_stimuli(spec,values(),repo_root=ROOT)
    description=describe_settings(spec,values(),selected)
    rows=review_rows(spec,values(),selected,description)
    targets=targets_for_rows(spec,selected,description,rows,{'experiment':None,'stimuli':{}},ROOT)
    assert len(targets)==len(rows)
    assert any(target['kind']=='unavailable' for target in targets)
    assert any(target['kind']=='experiment_json' for target in targets)
