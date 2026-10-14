"""Isolated calibration/presentation fixtures; no proof of physical instruments."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import sys
from types import ModuleType
import pytest
from textual.widgets import Button,Input,Select,Static,Checkbox
from test_calibration_review_completion import ROOT,fixture_profile,values,revisions
from psychophysics_lab.config.local import config_root,save_profile,content_hash
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest,photometry_is_test_data
from psychophysics_lab.config.calibration_dataset import (load_active,save_active,merge_observations,observation,summary,import_observations,active_directory,physical_snapshot)
from psychophysics_lab.config.calibration_templates import example_luminance_document
from psychophysics_lab.config.calibration_review import save_verification
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.config.input_constraints import experiment_constraints
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC
from psychophysics_lab.ui.setup import PsyCoLabSetupApp,ExperimentConfigScreen,ReviewScreen
from psychophysics_lab.ui.luminance_data import LuminanceDataScreen
from psychophysics_lab.core.presentation_testing import PresentationTestRequest,run_presentation_test,MARKER


def profile(verified=False):
    p=fixture_profile(verified=verified)
    return load_monitor_profiles(ROOT)[p.id]


def raw_dataset(p):
    dataset=load_active(config_root(ROOT),p)
    return dataset


def test_save_restart_noop_and_history_do_not_duplicate_active_files():
    p=profile(); data=raw_dataset(p)
    p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    active=active_directory(config_root(ROOT),p)/'luminance.json'
    before=active.read_bytes(); stat=active.stat().st_mtime_ns; revision=p.revision
    p2,data2=save_active(config_root(ROOT),p,load_active(config_root(ROOT),p),expected_version=1)
    assert p2.revision==revision and data2==saved and active.read_bytes()==before
    assert active.stat().st_mtime_ns==stat
    assert len(list(active.parent.glob('luminance*.json')))==1
    assert load_active(config_root(ROOT),load_monitor_profiles(ROOT)[p.id])==saved


def test_repetitions_new_intensity_statistics_and_single_sd():
    p=profile(); data=raw_dataset(p)
    rows=[observation(.5,value,kind='genuine') for value in (48,49,50)]
    data=merge_observations(data,rows,mode='replace_selected',selected_command=.5,confirmed=True)
    result=next(r for r in summary(data) if r['screen_intensity']==.5)
    assert result['n']==3 and result['luminance_cdm2']==49 and result['sample_sd_cdm2']==1
    data=merge_observations(data,[observation(.6,70)],mode='append')
    assert len(summary(data))==6 and next(r for r in summary(data) if r['screen_intensity']==.6)['sample_sd_cdm2'] is None
    p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    assert len(saved['observations'])==8 and not p.has_verified_luminance_mapping


@pytest.mark.parametrize('mode',['replace_selected','replace_all'])
def test_replacement_requires_confirmation_and_preserves_history(mode):
    p=profile(); p,saved=save_active(config_root(ROOT),p,raw_dataset(p),expected_version=0)
    with pytest.raises(ValueError,match='Confirm replacement'):
        merge_observations(saved,[observation(.5,50)],mode=mode,selected_command=.5)
    edited=merge_observations(saved,[observation(.5,50)],mode=mode,selected_command=.5,confirmed=True)
    p,new=save_active(config_root(ROOT),p,edited,expected_version=saved['version'])
    history=active_directory(config_root(ROOT),p)/'.history'
    assert any(json.loads(f.read_text())['observations']==saved['observations'] for f in history.glob('*.json'))
    assert new['observations']!=saved['observations']


def test_stale_dataset_and_profile_revisions_rejected():
    p=profile(); data=raw_dataset(p); p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    with pytest.raises(ValueError,match='dataset changed'):
        save_active(config_root(ROOT),p,saved,expected_version=0)
    updated=save_profile(config_root(ROOT),replace(p,notes='concurrent update'),expected_revision=p.revision)
    edited=deepcopy(saved); edited['notes']='stale'
    with pytest.raises(ValueError,match='Profile changed'):
        save_active(config_root(ROOT),p,edited,expected_version=saved['version'])
    assert load_active(config_root(ROOT),updated)==saved


def test_notes_preserve_verification_but_new_raw_readings_invalidate():
    p=profile(verified=True); p,saved=save_active(config_root(ROOT),p,raw_dataset(p),expected_version=0)
    assert p.has_verified_luminance_mapping
    notes=deepcopy(saved); notes['notes']='Only optional notes'
    p,saved=save_active(config_root(ROOT),p,notes,expected_version=saved['version'])
    assert p.has_verified_luminance_mapping
    # Same mean, different raw evidence still requires new verification.
    edited=merge_observations(saved,[observation(.5,49),observation(.5,49)],mode='replace_selected',selected_command=.5,confirmed=True)
    p,new=save_active(config_root(ROOT),p,edited,expected_version=saved['version'])
    assert not p.has_verified_luminance_mapping and not p.qualified_experiments


def test_synthetic_provenance_cannot_be_erased_by_method_edit():
    p=profile(); data=merge_observations(raw_dataset(p),[observation(.5,49,kind='synthetic')],mode='replace_selected',selected_command=.5,confirmed=True)
    data['method']='used photo meter, results are fake but are test pilot'
    p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    assert all(r['data_kind']=='synthetic' for r in saved['observations'])
    edited=deepcopy(saved); edited['method']='Actual meter description'
    p,saved=save_active(config_root(ROOT),p,edited,expected_version=saved['version'])
    assert photometry_is_test_data(p)
    with pytest.raises(ValueError,match='Fake/synthetic'):
        save_verification(p,config_root(ROOT),geometry_status=p.geometry_status,calibration_status='verified',timing_status=p.timing_status,calibration_method=p.calibration_method,reviewed=True)
    with pytest.raises(ValueError,match='Human acquisition blocked'):
        validate_setup(SetupRequest('H001','new',CSF_SPEC.id,p.id,values()),CSF_SPEC,p)


def test_same_import_twice_preserves_observations_and_checks_raw_mean(tmp_path):
    p=profile(); document=example_luminance_document(p)
    document['measurements']=[{'screen_intensity':.25,'luminance_cdm2':10,'readings_cdm2':[9,10,11]}, {'screen_intensity':1.,'luminance_cdm2':200,'readings_cdm2':[199,201]}]
    document['photometer_model_and_method']='fake pilot fixture'
    path=tmp_path/'pilot.json'; path.write_text(json.dumps(document))
    rows,metadata=import_observations(path,p,config_root(ROOT))
    data=merge_observations(raw_dataset(p),rows,mode='replace_all',confirmed=True)
    data['method']=metadata['calibration_method']
    p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    again=merge_observations(saved,rows,mode='merge')
    assert again['observations']==saved['observations'] and len(again['observations'])==5
    p2,new=save_active(config_root(ROOT),p,again,expected_version=saved['version'])
    assert p2==p and new==saved
    document['measurements'][0]['luminance_cdm2']=99; path.write_text(json.dumps(document))
    with pytest.raises(ValueError,match='mean contradicts'):
        import_observations(path,p,config_root(ROOT))


def test_changed_physical_snapshot_requires_confirmed_new_dataset():
    p=profile(); p,saved=save_active(config_root(ROOT),p,raw_dataset(p),expected_version=0)
    p=save_profile(config_root(ROOT),replace(p,viewing_distance_m=2.),expected_revision=p.revision)
    with pytest.raises(ValueError,match='Physical display configuration changed'):
        save_active(config_root(ROOT),p,saved,expected_version=saved['version'])
    replacement=merge_observations(saved,[observation(.5,49)],mode='replace_all',confirmed=True)
    replacement['physical_snapshot']=physical_snapshot(p)
    p,new=save_active(config_root(ROOT),p,replacement,expected_version=saved['version'])
    assert len(new['observations'])==1 and not p.has_verified_luminance_mapping


@pytest.mark.parametrize('key,bad',[('n_down',0),('logUNIT_UP',0),('max_trials',0),('number_conditions',3),('timeAB',0),('Background_Luminance',201)])
def test_dynamic_constraint_errors_follow_authoritative_validators(key,bad):
    p=profile(); reports,errors=experiment_constraints(CSF_SPEC,p,values()|{key:bad})
    assert errors or reports[key]['error']


def test_linked_background_and_live_range_preserve_starting_probe(tmp_path):
    p=profile()
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'human')
        async with app.run_test(size=(100,30)) as pilot:
            editor=ExperimentConfigScreen(data_root=tmp_path/'human',participant_id='H001',session_mode='new',experiment=CSF_SPEC,monitor_profile_id=p.id,defaults=values())
            app.push_screen(editor); await pilot.pause()
            editor.query_one('#background-mapping',Select).value='1'; await pilot.pause()
            assert float(editor.query_one('#field-Background-Screen-intensity',Input).value)==.25
            assert float(editor.query_one('#field-Background-Luminance',Input).value)==10
            assert float(editor.query_one('#field-starting-probe-intensity',Input).value)==.75
            assert '0.250–0.625' in str(editor.query_one('#domain-starting-probe-intensity',Static).render())
            assert editor.query_one('#field-starting-probe-intensity',Input).has_class('invalid-input')
            editor.query_one('#field-starting-probe-intensity',Input).value='.55'; await pilot.pause()
            assert not editor.query_one('#field-starting-probe-intensity',Input).has_class('invalid-input')
            editor.query_one('#review',Button).press(); await pilot.pause()
            assert app.screen.request.experiment_values['Background_Luminance']==10
    asyncio.run(scenario())


def test_luminance_editor_save_discard_restart_and_noop(tmp_path):
    p=profile()
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'human')
        async with app.run_test(size=(80,24)) as pilot:
            app.push_screen(LuminanceDataScreen(p)); await pilot.pause()
            screen=app.screen
            screen.query_one('#dataset-readings',Input).value='48,49,50'
            screen.query_one('#dataset-mode',Select).value='replace_selected'
            screen.query_one('#dataset-confirm',Checkbox).value=True
            screen.query_one('#dataset-add',Button).press(); await pilot.pause()
            assert '3 | 49 | 1' in str(screen.query_one('#dataset-statistics',Static).render())
            screen.query_one('#dataset-save',Button).press(); await pilot.pause()
            assert 'saved' in str(screen.query_one('#dataset-feedback',Static).render()).lower()
            screen.query_one('#dataset-save',Button).press(); await pilot.pause()
            assert 'No changes to save' in str(screen.query_one('#dataset-feedback',Static).render())
            screen.query_one('#dataset-notes',Input).value='Unsaved discard'
            screen.query_one('#dataset-back',Button).press(); await pilot.pause()
        saved=load_active(config_root(ROOT),load_monitor_profiles(ROOT)[p.id])
        assert saved['notes']!='Unsaved discard' and next(r for r in summary(saved) if r['screen_intensity']==.5)['n']==3
    asyncio.run(scenario())


def test_actual_pipeline_presentation_output_is_isolated_and_human_stays_blocked(tmp_path,monkeypatch):
    p=profile(); p=save_profile(config_root(ROOT),replace(p,calibration_method='fake pilot'),expected_revision=p.revision)
    monkeypatch.setattr('psychophysics_lab.core.display.preflight_fullscreen_display',lambda p:None)
    from psychophysics_lab.data.trials import TrialLog
    runtime=ModuleType(CSF_SPEC.legacy_module)
    def fake(conditions,parameters,response,state):
        TrialLog(__import__('pathlib').Path(response).parent/'trials.tsv').append({'trial_index':1,'staircase_id':0,'staircase_trial_index':1,'stimulus_condition':2.,'presented_display_contrast':.5,'next_display_contrast':.3,'correct':1,'reversal':0})
    runtime.run_experiment=fake; monkeypatch.setitem(sys.modules,CSF_SPEC.legacy_module,runtime)
    human=tmp_path/'human'; human.mkdir(); sentinel=human/'existing.tsv'; sentinel.write_bytes(b'KEEP')
    request=SetupRequest('H001','new',CSF_SPEC.id,p.id,values(),str(human))
    result=run_presentation_test(PresentationTestRequest(request),repo_root=ROOT)
    manifest=json.loads(result.manifest_file.read_text()); context=json.loads((result.run_directory/'trial_context.json').read_text())
    assert result.accepted_trials==1 and manifest['data_kind']==context['data_kind']=='uncalibrated_presentation_test'
    assert (result.run_directory/'UNCALIBRATED_TEST_DATA.json').exists()
    assert manifest['participant_id'].startswith('presentation_test_')
    assert not result.run_directory.is_relative_to(human) and sentinel.read_bytes()==b'KEEP'
    assert not (human/'workspace_state.json').exists()
    async def inspect():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=human)
        async with app.run_test() as pilot:
            app.query_one('#nav-data',Button).press(); await pilot.pause()
            app.screen.query_one('#inspect-presentation-manifest',Button).press(); await pilot.pause()
            from psychophysics_lab.ui.setup import CodeViewScreen
            assert isinstance(app.screen,CodeViewScreen)
            assert app.data_root==human
    asyncio.run(inspect())
    from psychophysics_lab.paths import resolve_data_root
    with pytest.raises(ValueError,match='Presentation-test folders'):
        resolve_data_root(result.run_directory,ROOT)
    from psychophysics_lab.core.runner import run_request
    with pytest.raises(ValueError,match='Human acquisition blocked'):
        run_request(request,repo_root=ROOT,data_root=human)


def test_presentation_still_rejects_unsafe_start_without_output(tmp_path,monkeypatch):
    p=profile(); monkeypatch.setattr('psychophysics_lab.core.display.preflight_fullscreen_display',lambda p:None)
    unsafe=values()|{'Background_Screen_intensity':.25,'starting_probe_intensity':1.}
    test_root=config_root(ROOT).parent/'psycolab_presentation_tests'
    before={str(f):f.read_bytes() for f in test_root.rglob('*') if f.is_file()} if test_root.exists() else {}
    with pytest.raises(ValueError,match='Grating command may clip'):
        run_presentation_test(PresentationTestRequest(SetupRequest('H001','new',CSF_SPEC.id,p.id,unsafe)),repo_root=ROOT)
    after={str(f):f.read_bytes() for f in test_root.rglob('*') if f.is_file()} if test_root.exists() else {}
    assert after==before


def test_legacy_summary_is_not_invented_raw_repetition():
    p=profile(); data=raw_dataset(p)
    assert summary(data)[0]['n'] is None and summary(data)[0]['sample_sd_cdm2'] is None
    with pytest.raises(ValueError,match='unknown repetition counts'):
        merge_observations(data,[observation(.5,50)],mode='merge')


def test_interrupted_active_write_recovers_committed_raw_snapshot(monkeypatch):
    import psychophysics_lab.config.calibration_dataset as module
    p=profile(); data=merge_observations(raw_dataset(p),[observation(.5,48),observation(.5,50)],mode='replace_selected',selected_command=.5,confirmed=True)
    original=module.atomic_write_json
    def fail(path,payload):
        if path.name=='luminance.json': raise OSError('fixture interrupted active replace')
        return original(path,payload)
    monkeypatch.setattr(module,'atomic_write_json',fail)
    with pytest.raises(OSError,match='interrupted'):
        save_active(config_root(ROOT),p,data,expected_version=0)
    current=load_monitor_profiles(ROOT)[p.id]
    assert not current.has_verified_luminance_mapping
    recovered=load_active(config_root(ROOT),current)
    assert recovered['_needs_recovery'] and next(r for r in summary(recovered) if r['screen_intensity']==.5)['n']==2
    monkeypatch.setattr(module,'atomic_write_json',original)
    revision=current.revision
    current,saved=save_active(config_root(ROOT),current,recovered,expected_version=recovered['version'])
    assert current.revision==revision and '_needs_recovery' not in saved
    assert load_active(config_root(ROOT),current)==saved


def test_raw_session_and_single_command_import_keep_actual_repetitions(tmp_path):
    from psychophysics_lab.core.luminance_session import LocalLuminanceSession,LuminanceSessionRequest
    p=profile()
    session=LocalLuminanceSession(config_root(ROOT),p,LuminanceSessionRequest(p.id))
    session.record(.5,'48'); session.record(.5,'50'); session.finish()
    rows,metadata=import_observations(session.session_file,p,config_root(ROOT))
    assert len(rows)==2 and all(r['recorded_utc'] for r in rows)
    data=merge_observations(raw_dataset(p),rows,mode='replace_selected',selected_command=.5,confirmed=True)
    assert next(r for r in summary(data) if r['screen_intensity']==.5)['sample_sd_cdm2']==pytest.approx(2**.5)


def test_export_reimport_keeps_ids_and_optional_timestamps(tmp_path):
    p=profile(); rows=[observation(.25,10,recorded_utc='2026-10-13T12:00:00Z'),observation(1,200)]
    data=merge_observations(raw_dataset(p),rows,mode='replace_all',confirmed=True)
    document=example_luminance_document(p); document['measurements']=summary(data)
    path=tmp_path/'export.json'; path.write_text(json.dumps(document))
    imported,_=import_observations(path,p,config_root(ROOT))
    assert [r['observation_id'] for r in imported]==[r['observation_id'] for r in rows]
    assert imported[0]['recorded_utc']==rows[0]['recorded_utc']
    assert merge_observations(data,imported)['observations']==rows


def test_legacy_profile_mean_edit_updates_active_record_and_retains_raw_history():
    from psychophysics_lab.config.models import LuminanceCalibrationPoint
    p=profile(); data=merge_observations(raw_dataset(p),[observation(.5,48),observation(.5,50)],mode='replace_selected',selected_command=.5,confirmed=True)
    p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    points=tuple(LuminanceCalibrationPoint(r.screen_intensity,51 if r.screen_intensity==.5 else r.luminance_cdm2) for r in p.luminance_calibration)
    p=save_profile(config_root(ROOT),replace(p,luminance_calibration=points),expected_revision=p.revision)
    active=load_active(config_root(ROOT),p)
    assert next(r for r in summary(active) if r['screen_intensity']==.5)['luminance_cdm2']==51
    assert all(r.get('source')=='legacy_summary_only' for r in active['observations'])
    assert not p.has_verified_luminance_mapping
    assert any(json.loads(f.read_text()).get('observations')==saved['observations'] for f in (active_directory(config_root(ROOT),p)/'.history').glob('*.json'))


def test_legacy_optional_note_edit_syncs_active_without_invalidating():
    p=profile(verified=True); p,saved=save_active(config_root(ROOT),p,raw_dataset(p),expected_version=0)
    p=save_profile(config_root(ROOT),replace(p,calibration_notes='Optional edited note'),expected_revision=p.revision)
    active=load_active(config_root(ROOT),p)
    assert active['notes']=='Optional edited note' and active['observations']==saved['observations']
    assert p.has_verified_luminance_mapping


def test_older_fake_method_cannot_be_converted_by_verification_metadata_only():
    p=profile(); p=save_profile(config_root(ROOT),replace(p,calibration_method='used photo meter, results are fake but are test pilot'),expected_revision=p.revision)
    with pytest.raises(ValueError,match='Fake/synthetic'):
        save_verification(p,config_root(ROOT),geometry_status=p.geometry_status,calibration_status='verified',timing_status=p.timing_status,calibration_method='Actual meter',reviewed=True)
    p=save_profile(config_root(ROOT),replace(p,calibration_method='Actual meter'),expected_revision=p.revision)
    assert p.luminance_data_kind=='synthetic' and not p.has_verified_luminance_mapping


def test_switching_monitor_rebuilds_mapping_and_retains_invalid_pair_for_correction(tmp_path):
    from psychophysics_lab.config.models import LuminanceCalibrationPoint
    p=profile(verified=True)
    second=save_profile(config_root(ROOT),replace(p,id='second_lab',revision=0,profile_uuid='',
        luminance_calibration=(LuminanceCalibrationPoint(0,.2),LuminanceCalibrationPoint(.5,60),LuminanceCalibrationPoint(1,300))),expected_revision=0)
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'human')
        async with app.run_test() as pilot:
            editor=ExperimentConfigScreen(data_root=tmp_path/'human',participant_id='H001',session_mode='new',experiment=CSF_SPEC,monitor_profile_id=p.id,defaults=values())
            app.push_screen(editor); await pilot.pause()
            editor._apply_display(second.id); await pilot.pause()
            assert editor.query_one('#background-mapping',Select).value=='confirm'
            with pytest.raises(ValueError, match='Display or mapping changed'):
                editor._collect()
            assert float(editor.query_one('#field-Background-Luminance',Input).value)==49
            assert editor.query_one('#field-Background-Luminance',Input).has_class('invalid-input')
            editor.query_one('#background-mapping',Select).value='1'; await pilot.pause()
            assert float(editor.query_one('#field-Background-Luminance',Input).value)==60
            assert float(editor.query_one('#field-Max-monitor-Luminance',Input).value)==300
            editor.query_one('#review',Button).press(); await pilot.pause()
            assert app.screen.request.monitor_profile_id==second.id and app.screen.request.experiment_values['Background_Luminance']==60
    asyncio.run(scenario())


def test_genuine_active_observations_and_instrument_verify_in_one_reviewed_action():
    p=profile(); data=merge_observations(raw_dataset(p),[observation(.25,10,kind='genuine'),observation(.5,49,kind='genuine'),observation(1,200,kind='genuine')],mode='replace_all',confirmed=True)
    data['method']=''
    p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    updated=save_verification(p,config_root(ROOT),geometry_status=p.geometry_status,calibration_status='verified',timing_status=p.timing_status,calibration_method='Actual laboratory meter',reviewed=True)
    assert updated.has_verified_luminance_mapping and not updated.qualified_experiments
    assert load_active(config_root(ROOT),updated)['method']=='Actual laboratory meter'


def test_unchanged_older_fake_profile_is_noop_and_still_cannot_be_relabelled():
    legacy=replace(profile(),id='older_fake_profile',revision=1,calibration_method='fake pilot')
    raw=legacy.to_dict(); raw.pop('luminance_data_kind'); raw.pop('luminance_source_hash')
    folder=config_root(ROOT)/'profiles'/legacy.id; folder.mkdir()
    (folder/'revision_000001.json').write_text(json.dumps(raw))
    old=load_monitor_profiles(ROOT)[legacy.id]
    unchanged=save_profile(config_root(ROOT),old,expected_revision=old.revision)
    assert unchanged==old and len(list(folder.glob('revision_*.json')))==1
    changed=save_profile(config_root(ROOT),replace(old,calibration_method='Actual meter'),expected_revision=old.revision)
    assert changed.luminance_data_kind=='synthetic' and not changed.has_verified_luminance_mapping


def test_focused_verification_returns_with_current_instrument_and_noop_save(tmp_path):
    p=profile(); data=merge_observations(raw_dataset(p),[observation(.25,10,kind='genuine'),observation(.5,49,kind='genuine'),observation(1,200,kind='genuine')],mode='replace_all',confirmed=True)
    p,saved=save_active(config_root(ROOT),p,data,expected_version=0)
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'human')
        async with app.run_test() as pilot:
            screen=LuminanceDataScreen(p,experiment_id=CSF_SPEC.id); app.push_screen(screen); await pilot.pause()
            screen.query_one('#dataset-verify',Button).press(); await pilot.pause()
            app.screen.query_one('#verification-calibration_status',Select).value='verified'
            app.screen.query_one('#verification-method',Input).value='Actual laboratory meter'
            app.screen.query_one('#verification-reviewed',Checkbox).value=True
            app.screen.query_one('#verification-save',Button).press(); await pilot.pause()
            assert app.screen is screen and screen.profile.has_verified_luminance_mapping
            assert screen.query_one('#dataset-method',Input).value=='Actual laboratory meter'
            revision=screen.profile.revision
            screen.query_one('#dataset-save',Button).press(); await pilot.pause()
            assert screen.profile.revision==revision and 'No changes to save' in str(screen.query_one('#dataset-feedback',Static).render())
    asyncio.run(scenario())


def test_invalid_low_probe_still_shows_current_allowed_range():
    p=profile(); reports,errors=experiment_constraints(CSF_SPEC,p,values()|{'Background_Screen_intensity':.25,'starting_probe_intensity':.1})
    assert '0.250–0.625' in reports['starting_probe_intensity']['domain']
    assert reports['starting_probe_intensity']['error']


def test_changed_older_file_adds_only_new_observations(tmp_path):
    p=profile(); document=example_luminance_document(p)
    document['measurements']=[{'screen_intensity':.25,'luminance_cdm2':10,'readings_cdm2':[9,10,11]}]
    path=tmp_path/'growing.json'; path.write_text(json.dumps(document))
    rows,_=import_observations(path,p,config_root(ROOT))
    data=merge_observations(raw_dataset(p),rows,mode='replace_selected',selected_command=.25,confirmed=True)
    document['measurements'][0].update(luminance_cdm2=10.5,readings_cdm2=[9,10,11,12]); path.write_text(json.dumps(document))
    new,_=import_observations(path,p,config_root(ROOT))
    data=merge_observations(data,new)
    result=next(r for r in summary(data) if r['screen_intensity']==.25)
    assert result['n']==4 and result['luminance_cdm2']==10.5


def test_outer_app_presentation_failure_reports_only_to_test_root(tmp_path,monkeypatch):
    import psychophysics_lab.app as launcher
    from psychophysics_lab.ui import setup
    from psychophysics_lab.core import presentation_testing
    root=tmp_path/'repo'; root.mkdir(); human=tmp_path/'human'; human.mkdir()
    sentinel=human/'real.tsv'; sentinel.write_bytes(b'KEEP')
    test_root=config_root(ROOT).parent/'psycolab_presentation_tests'; test_root.mkdir(exist_ok=True)
    (test_root/MARKER).write_text(json.dumps({'human_acquisition_allowed':False,'data_kind':'uncalibrated_presentation_test'}))
    action=PresentationTestRequest(SetupRequest('H001','new',CSF_SPEC.id,'fixture',values()))
    calls=[]; prompts=[]
    def tui(**kwargs):
        prompts.append(kwargs); return action if len(prompts)==1 else None
    def fail(*args,**kwargs): raise RuntimeError('mocked presentation failure')
    monkeypatch.setattr(launcher,'find_repo_root',lambda:root)
    monkeypatch.setattr(launcher,'default_data_root',lambda _:human)
    monkeypatch.setattr(launcher,'preferred_data_root',lambda _r,default:default)
    monkeypatch.setattr(setup,'run_setup_tui',tui)
    monkeypatch.setattr(presentation_testing,'run_presentation_test',fail)
    monkeypatch.setattr(launcher,'write_crash_report',lambda *args,**kwargs:calls.append(kwargs) or test_root/'fixture.log')
    assert launcher._main([])==0
    assert calls[0]['data_root']==test_root and calls[0]['phase']=='uncalibrated_presentation_test'
    assert 'failed' in prompts[1]['simulation_summary'] and sentinel.read_bytes()==b'KEEP'


def test_manifest_does_not_certify_legacy_fake_verified_flag(tmp_path):
    from psychophysics_lab.core.runner import _manifest_payload
    p=replace(profile(),calibration_status='verified',calibration_method='fake pilot')
    request=SetupRequest('presentation_test_fixture','new',CSF_SPEC.id,p.id,values())
    manifest=_manifest_payload(request=request,setup={},profile=p.to_dict(),run_dir=tmp_path/'run_001',data_root=tmp_path,repo_root=ROOT,grouping_parts=(),run_uuid='fixture',status='configured')
    assert manifest['calibration']['has_encoded_luminance_mapping']
    assert not manifest['calibration']['has_verified_luminance_mapping']
