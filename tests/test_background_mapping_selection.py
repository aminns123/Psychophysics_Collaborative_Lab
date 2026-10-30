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
from psychophysics_lab.experiments.contrast_sensitivity import SPEC as CSF_SPEC
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentParametersScreen


def measured(*, kind='genuine', endpoint=True):
    p=fixture_profile(observations=False)
    points=[(0,.2),(.25,18),(.25,20),(.5,100)] + ([(1,500)] if endpoint else [])
    dataset=merge_observations(load_active(config_root(ROOT),p),
        [observation(i,l,kind=kind) for i,l in points],mode='replace_all',confirmed=True)
    return save_active(config_root(ROOT),p,dataset,expected_version=0)[0]


def selected_values():
    # Historical stored mapping fields remain readable as provenance; they
    # are not required inputs to the current generic CSF configuration.
    return values() | {'Background_Screen_intensity':.25,'Background_Luminance':19,
                       'Max_monitor_Luminance':500,'starting_probe_intensity':.55}


def editor_for(p, data, defaults=None):
    return ExperimentParametersScreen(data_root=data,participant_id='H001',session_mode='new',
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
    request=SetupRequest('H001','new',CSF_SPEC.id,p.id,CSF_SPEC.field_defaults())
    validate_setup(request,CSF_SPEC,p,mode='simulation')
    with pytest.raises(ValueError): validate_setup(request,CSF_SPEC,p)
    assert not p.has_verified_luminance_mapping and not p.qualified_experiments



def test_stale_physical_mapping_is_not_trusted_for_photometry():
    p=measured()
    changed=replace(p,viewing_distance_m=2)
    with pytest.raises(ValueError,match='stale'):
        mapping_choices(config_root(ROOT),changed)
    evidence=background_provenance(config_root(ROOT),changed,selected_values())
    assert evidence['mapping_state']=='profile_only_test'
    assert evidence['selection_basis']=='profile_summary_unverified'
    assert not evidence['physically_verified_mapping']


@pytest.mark.parametrize('endpoint',[True,False])

def test_unverified_profile_summary_is_available_for_tests_if_active_dataset_stale(endpoint):
    p = measured(kind='synthetic', endpoint=endpoint)
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



def test_current_csf_digital_background_is_independent_of_photometer_pair_selection():
    fields={f.key:f for f in CSF_SPEC.fields}
    assert "background_intensity" in fields
    assert fields["background_intensity"].units.startswith("digital intensity")
    assert "Background_Luminance" not in fields
    assert "Background_Screen_intensity" not in fields
    # The photometer observations remain available on the monitor profile,
    # without requiring that every public experiment has a linked luminance pair.
    p=measured()
    rows,_,_=mapping_choices(config_root(ROOT),p)
    assert rows[1]["luminance_cdm2"]==19


def test_current_config_editor_allows_researcher_selected_background(tmp_path):
    p=measured()
    defaults=CSF_SPEC.field_defaults()
    screen=editor_for(p,tmp_path,defaults)
    assert CSF_SPEC.normalise_values(defaults | {"background_intensity":.4})["background_intensity"]==.4
    assert "background_intensity" in {f.key for f in screen.experiment.fields}
