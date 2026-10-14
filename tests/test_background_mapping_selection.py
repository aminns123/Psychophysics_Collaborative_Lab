"""Background selection uses active means, retains raw data and records provenance."""
import asyncio
from dataclasses import replace
import json

import pytest
from textual.widgets import Button, Input, Select, Static

from test_calibration_review_completion import ROOT, fixture_profile, values
from psychophysics_lab.config.local import config_root, save_profile, save_preset
from psychophysics_lab.config.calibration_dataset import load_active, save_active, merge_observations, observation, active_directory
from psychophysics_lab.config.background_mapping import mapping_choices, configuration_mapping_choices, background_provenance
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen


def measured(*, kind='genuine', endpoint=True):
    p=fixture_profile(observations=False)
    points=[(0,.2),(.25,18),(.25,20),(.5,100)] + ([(1,500)] if endpoint else [])
    dataset=merge_observations(load_active(config_root(ROOT),p),
        [observation(i,l,kind=kind) for i,l in points],mode='replace_all',confirmed=True)
    return save_active(config_root(ROOT),p,dataset,expected_version=0)[0]


def selected_values():
    return values() | {'Background_Screen_intensity':.25,'Background_Luminance':19,
                       'Max_monitor_Luminance':500,'starting_probe_intensity':.55}


def editor_for(p, data, defaults=None):
    return ExperimentConfigScreen(data_root=data,participant_id='H001',session_mode='new',
        experiment=CSF_SPEC,monitor_profile_id=p.id,defaults=defaults or selected_values())


def test_mapping_uses_one_mean_per_intensity_and_keeps_repetitions():
    p=measured(); path=active_directory(config_root(ROOT),p)/'luminance.json'; before=path.read_bytes()
    rows,dataset,state=mapping_choices(config_root(ROOT),p)
    assert len(rows)==4 and len(dataset['observations'])==5
    assert rows[1]['luminance_cdm2']==19 and rows[1]['n']==2
    assert rows[1]['readings_cdm2']==[18,20]
    evidence=background_provenance(config_root(ROOT),p,selected_values())
    assert evidence['selection_basis']=='exact_saved_mean_pair'
    assert evidence['saved_mapping_row']==rows[1]
    assert evidence['luminance_source_hash']==p.luminance_source_hash
    assert not evidence['interpolated'] and not evidence['physically_verified_mapping']
    assert path.read_bytes()==before


def test_synthetic_means_are_selectable_but_not_human_qualification():
    p=measured(kind='synthetic')
    rows,_,state=mapping_choices(config_root(ROOT),p)
    assert len(rows)==4 and 'SYNTHETIC' in state
    request=SetupRequest('H001','new',CSF_SPEC.id,p.id,selected_values())
    validate_setup(request,CSF_SPEC,p,mode='simulation')
    with pytest.raises(ValueError): validate_setup(request,CSF_SPEC,p)
    assert not p.has_verified_luminance_mapping and not p.qualified_experiments


def test_stale_physical_mapping_is_not_offered():
    p=measured()
    changed=replace(p,viewing_distance_m=2)
    with pytest.raises(ValueError,match='stale'):
        mapping_choices(config_root(ROOT),changed)
    evidence=background_provenance(config_root(ROOT),changed,selected_values())
    assert evidence['mapping_state']=='unavailable'


@pytest.mark.parametrize('endpoint',[True,False])
def test_tui_pair_updates_both_values_and_only_real_endpoint(tmp_path,endpoint):
    p=measured(endpoint=endpoint)
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            editor=editor_for(p,tmp_path/'data',selected_values()|{'Max_monitor_Luminance':700})
            await app.push_screen(editor); await pilot.pause()
            assert editor.query_one('#background-mapping',Select).value=='1'
            editor.query_one('#background-mapping',Select).value='2'; await pilot.pause()
            assert float(editor.query_one('#field-Background-Screen-intensity',Input).value)==.5
            assert float(editor.query_one('#field-Background-Luminance',Input).value)==100
            assert float(editor.query_one('#field-Max-monitor-Luminance',Input).value)==(500 if endpoint else 700)
            assert float(editor.query_one('#field-starting-probe-intensity',Input).value)==.55
            # The measured command-1.0 endpoint is a maximum, not a valid
            # background command (< 1); it remains available for Max L.
            assert all(point['screen_intensity'] < 1 for point in editor._mapping_rows)
            assert any(point['screen_intensity'] == 1 for point in editor._all_mapping_rows) == endpoint
            assert 'Digital intensity 0.5' in str(editor.query_one('#mapping-provenance',Static).render())
    asyncio.run(scenario())


def test_display_confirmation_and_explicit_manual_survive_restart(tmp_path):
    p=measured()
    second=save_profile(config_root(ROOT),replace(p,id='second_display',profile_uuid='',revision=0,luminance_source_hash=''))
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            editor=editor_for(p,tmp_path/'data'); await app.push_screen(editor); await pilot.pause()
            editor._apply_display(second.id); await pilot.pause()
            assert editor.query_one('#background-mapping',Select).value=='confirm'
            assert float(editor.query_one('#field-Background-Luminance',Input).value)==19
            with pytest.raises(ValueError,match='changed'): editor._collect()
        restart=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with restart.run_test() as pilot:
            editor=editor_for(second,tmp_path/'data'); await restart.push_screen(editor); await pilot.pause()
            assert editor.query_one('#background-mapping',Select).value=='confirm'
            editor.query_one('#background-mapping',Select).value='manual'; await pilot.pause()
            assert editor._collect()['Background_Luminance']==19
            editor._save_calibration_draft()
        last=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with last.run_test() as pilot:
            editor=editor_for(second,tmp_path/'data'); await last.push_screen(editor); await pilot.pause()
            assert editor.query_one('#background-mapping',Select).value=='manual'
            assert editor._collect()['Background_Luminance']==19
    asyncio.run(scenario())


def test_preset_restores_exact_saved_pair_without_mutating_calibration(tmp_path):
    p=measured(); path=active_directory(config_root(ROOT),p)/'luminance.json'; before=path.read_bytes()
    save_preset(config_root(ROOT),'mean_background',CSF_SPEC.id,selected_values())
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            editor=editor_for(p,tmp_path/'data',values()); await app.push_screen(editor); await pilot.pause()
            editor.query_one('#config-preset',Select).value='mean_background'
            editor.query_one('#load-preset',Button).press(); await pilot.pause()
            assert editor.query_one('#background-mapping',Select).value=='1'
            assert editor._collect()['Background_Luminance']==19
    asyncio.run(scenario())
    assert path.read_bytes()==before


def test_run_snapshots_keep_exact_pair_mean_provenance_and_monitor(tmp_path):
    from simulations.run import simulate
    p=measured(kind='synthetic')
    result,_=simulate(workspace=tmp_path/'data',seed=3,repo_root=ROOT,analyse=False,
        monitor_profile_id=p.id,values=selected_values()|{'max_trials':1})
    manifest=json.loads(result.manifest_file.read_text())
    config=json.loads((result.run_directory/'experiment_config.json').read_text())
    profile=json.loads((result.run_directory/'monitor_profile.json').read_text())
    assert manifest['background_mapping']==config['background_mapping']
    evidence=manifest['background_mapping']
    assert evidence['screen_intensity']==.25 and evidence['luminance_cdm2']==19
    assert evidence['saved_mapping_row']['n']==2
    assert evidence['profile_uuid']==profile['profile_uuid']
    assert evidence['luminance_source_hash']==profile['luminance_source_hash']
    assert manifest['data_kind']=='synthetic' and not evidence['physically_verified_mapping']


def test_unverified_profile_summary_is_available_for_tests_if_active_dataset_stale():
    p = measured(kind='synthetic')
    changed = replace(p, viewing_distance_m=p.viewing_distance_m + 0.1)
    with pytest.raises(ValueError, match='stale'):
        mapping_choices(config_root(ROOT), changed)
    rows, dataset, message, source = configuration_mapping_choices(config_root(ROOT), changed)
    assert source == 'profile_only' and dataset is None
    assert len(rows) == len(changed.luminance_calibration)
    assert rows[1]['screen_intensity'] == .25
    assert rows[1]['luminance_cdm2'] == 19
    assert all(row['summary_only'] for row in rows)
    assert 'TEST VALUES' in message and 'NOT physically verified'.lower() in message.lower()
    assert not changed.has_verified_luminance_mapping
    provenance = background_provenance(config_root(ROOT), changed, selected_values())
    assert provenance['selection_basis'] == 'profile_summary_unverified'
    assert provenance['mapping_state'] == 'profile_only_test'
    assert not provenance['physically_verified_mapping']


def test_verified_profile_must_not_offer_stale_untrusted_raw_mapping():
    p = measured(kind='genuine')
    verified = replace(p, calibration_status='verified', calibration_method='Laboratory photometer')
    assert verified.has_verified_luminance_mapping
    changed = replace(verified, viewing_distance_m=verified.viewing_distance_m + 0.1)
    rows, dataset, message, source = configuration_mapping_choices(config_root(ROOT), changed)
    assert rows == [] and dataset is None and source == 'unavailable'
    assert 'repair' in message.lower()


def test_background_dropdown_is_adjacent_to_fields_and_locks_linked_pair(tmp_path):
    p = measured()
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path / 'data')
        async with app.run_test() as pilot:
            editor = editor_for(p, tmp_path / 'data')
            await app.push_screen(editor)
            await pilot.pause()
            picker = editor.query_one('#background-mapping', Select)
            luminance = editor.query_one('#field-Background-Luminance', Input)
            intensity = editor.query_one('#field-Background-Screen-intensity', Input)
            assert picker.value == '1'
            assert luminance.disabled and intensity.disabled
            assert editor.query_one('#edit-background-calibration', Button)
            picker.value = '2'
            await pilot.pause()
            assert float(luminance.value) == 100
            assert float(intensity.value) == .5
            assert luminance.disabled and intensity.disabled
            picker.value = 'manual'
            await pilot.pause()
            assert not luminance.disabled and not intensity.disabled
            luminance.value = '90'
            await pilot.pause()
            assert picker.value == 'manual'
            assert float(intensity.value) == .5
    asyncio.run(scenario())
