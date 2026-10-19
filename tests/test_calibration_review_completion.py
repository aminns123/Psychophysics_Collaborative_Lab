"""Researcher completion/review workflows; all evidence is isolated fixture data."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import pytest
from textual.widgets import Button, Checkbox, Input, Select, Static

from psychophysics_lab.config.local import config_root, save_profile, content_hash, preferences
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import LuminanceCalibrationPoint, SetupRequest
from psychophysics_lab.config.calibration_progress import calibration_progress
from psychophysics_lab.config.calibration_review import qualify_experiment, save_verification
from psychophysics_lab.config.preflight import validate_setup, qualification_checks
from psychophysics_lab.config.calibration_workflow import import_and_save_luminance
from psychophysics_lab.config.calibration_templates import example_luminance_document
from psychophysics_lab.experiments.contrast_sensitivity import SPEC as CSF_SPEC
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, DisplayCheckScreen
from psychophysics_lab.ui.calibration_review import PhysicalVerificationScreen, ExperimentQualificationScreen

ROOT=Path(__file__).resolve().parents[1]

def fixture_profile(*, verified=False, observations=True):
    root=config_root(ROOT)
    reference=load_monitor_profiles(ROOT)['legacy_reference_display']
    p=save_profile(root,replace(reference,id='review_lab',origin='local',
        expected_resolution_px=(1920,1080),display_binding={'device_id':'FIXTURE','index':0,'x':0,'y':0,'width':1920,'height':1080},
        measurement_sources={key:'manual' for key in ('physical_width_m','physical_height_m','viewing_distance_m')},
        luminance_calibration=tuple(LuminanceCalibrationPoint(command,luminance) for command,luminance in zip((0,.25,.5,.75,1),(.3,10,49,100,200))),
        calibration_method='Laboratory meter fixture' if verified else '',
        geometry_status='verified' if verified else 'manual_unverified',
        calibration_status='verified' if verified else 'manual_unverified',
        timing_status='verified' if verified else 'manual_unverified',qualified_experiments=()))
    if observations:
        for kind in ('size','spatial','temporal_binary'):
            folder=root/'diagnostics'/'display_geometry'/p.id/kind
            folder.mkdir(parents=True)
            (folder/'geometry_check.json').write_text(json.dumps({'status':'completed','monitor_profile':p.to_dict(),'monitor_profile_sha256':content_hash(p.to_dict()),'request':{'test_kind':kind},'measurement':{'measured_length_mm':100.,'error_percent':0.} if kind=='size' else {}}),encoding='utf-8')
            if kind == 'spatial':
                from dataclasses import asdict
                from uuid import uuid4
                from psychophysics_lab.core.geometry_check import GeometryCheckRequest
                from psychophysics_lab.core.display_tests import resolve_test
                from psychophysics_lab.config.spatial_observation import record_observation
                report = folder/'geometry_check.json'
                payload = json.loads(report.read_text())
                request = GeometryCheckRequest(p.id, 'visual_angle_deg', 5, test_kind='spatial')
                bar, plan = resolve_test(p, request, (1920,1080))
                payload.update(diagnostic_uuid=str(uuid4()), actual_fullscreen_resolution_px=[1920,1080],
                               request=asdict(request), resolved_test=plan, resolved_bar=bar.to_dict())
                report.write_text(json.dumps(payload), encoding='utf-8')
                record_observation(root, report, p, assessment='consistent', abnormality='none')
    return p

def values():
    return CSF_SPEC.field_defaults() | {'background_intensity': .5, 'starting_contrast': .1}

def revisions(p):
    return list((config_root(ROOT)/'profiles'/p.id).glob('revision_*.json'))

@pytest.mark.parametrize('size',[(80,24),(120,40)])
def test_finish_completed_measurements_without_qualification_returns_to_experiment(tmp_path,size):
    p=fixture_profile()
    initial=[file.read_bytes() for file in revisions(p)]
    assert calibration_progress(p,config_root(ROOT))['review']['completed']
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=size) as pilot:
            app.query_one('#nav-display',Button).press()
            await pilot.pause()
            screen=app.screen
            screen.query_one('#cal-stage-review',Button).press()
            await pilot.pause()
            assert screen.query_one('#cal-stage-review',Button).variant=='success'
            assert '5 intensity / cd/m² pairs saved' in str(screen.query_one('#calibration-review-detail',Static).render())
            assert 'Physical verification pending' in str(screen.query_one('#calibration-review-detail',Static).render())
            assert await pilot.click('#calibration-finish')  # visible even at 80×24
            await pilot.pause()
            assert len(app.screen_stack)==1
            assert app.query_one('#monitor-profile',Select).value==p.id
            assert 'preflight' in str(app.query_one('#setup-status',Static).render())
    asyncio.run(scenario())
    assert load_monitor_profiles(ROOT)[p.id]==p
    assert [file.read_bytes() for file in revisions(p)]==initial
    assert preferences(config_root(ROOT))['active_monitor_profile_id']==p.id
    assert not p.qualified_experiments and not p.has_verified_luminance_mapping
    with pytest.raises(ValueError,match='Physical photometry'):
        validate_setup(SetupRequest('fixture_subject','new',CSF_SPEC.id,p.id,values()),CSF_SPEC,p)
    validate_setup(SetupRequest('fixture_subject','new',CSF_SPEC.id,p.id,values()),CSF_SPEC,p,mode='simulation')

def test_incomplete_setup_can_also_finish_without_profile_save(tmp_path):
    p=fixture_profile(observations=False)
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            app.query_one('#nav-display',Button).press()
            await pilot.pause()
            app.screen.query_one('#cal-stage-review',Button).press()
            await pilot.pause()
            assert await pilot.click('#calibration-finish')
            await pilot.pause()
            assert len(app.screen_stack)==1
            assert 'Incomplete observations' in str(app.query_one('#setup-status',Static).render())
    asyncio.run(scenario())
    assert len(revisions(p))==1

def test_general_editor_noop_save_does_not_create_revision_or_advance(tmp_path):
    p=fixture_profile()
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            app.query_one('#nav-display',Button).press()
            await pilot.pause()
            review=app.screen
            review.query_one('#cal-stage-review',Button).press()
            await pilot.pause()
            review.query_one('#edit-review-profile',Button).press()
            await pilot.pause()
            app.screen.query_one('#profile-save',Button).press()
            await pilot.pause()
            assert app.screen is review and review.active_calibration_stage=='review'
            assert app.monitor_profiles[p.id]==p
    asyncio.run(scenario())
    assert len(revisions(p))==1

def test_verification_requires_deliberate_review_preserves_observations_and_returns(tmp_path):
    p=fixture_profile()
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one('#nav-display',Button).press()
            await pilot.pause()
            review=app.screen
            review.query_one('#cal-stage-review',Button).press()
            await pilot.pause()
            review.query_one('#review-physical-verification',Button).press()
            await pilot.pause()
            assert isinstance(app.screen,PhysicalVerificationScreen)
            focused=app.screen
            focused.query_one('#verification-geometry_status',Select).value='verified'
            focused.query_one('#verification-save',Button).press()
            await pilot.pause()
            assert app.screen is focused
            assert 'Confirm independent' in str(focused.query_one('#verification-feedback',Static).render())
            focused.query_one('#verification-reviewed',Checkbox).value=True
            focused.query_one('#verification-save',Button).press()
            await pilot.pause()
            assert app.screen is review and review.active_calibration_stage=='review'
            assert 'Manually declared verified' in str(review.query_one('#calibration-review-detail',Static).render())
    asyncio.run(scenario())
    updated=load_monitor_profiles(ROOT)[p.id]
    assert updated.geometry_status=='verified' and updated.luminance_calibration==p.luminance_calibration
    assert not updated.has_verified_luminance_mapping and not updated.qualified_experiments
    assert calibration_progress(updated,config_root(ROOT))['geometry']['measurement_recorded']

def test_registry_qualification_failure_is_explained_and_no_save(tmp_path):
    p=fixture_profile()
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            app.query_one('#nav-display',Button).press()
            await pilot.pause()
            review=app.screen
            review.query_one('#review-qualification',Button).press()
            await pilot.pause()
            assert isinstance(app.screen,ExperimentQualificationScreen)
            assert app.screen.query_one('#qualification-save',Button).disabled
            assert 'BLOCKED' in str(app.screen.query_one('#qualification-checks',Static).render())
            app.screen.query_one('#qualification-back',Button).press()
            await pilot.pause()
            assert app.screen is review
    asyncio.run(scenario())
    assert len(revisions(p))==1
    with pytest.raises(ValueError,match='cannot be qualified'):
        qualify_experiment(p,config_root(ROOT),CSF_SPEC,reviewed=True)

def test_explicit_qualified_experiment_and_restart(tmp_path):
    p=fixture_profile(verified=True)
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            app.query_one('#nav-display',Button).press()
            await pilot.pause()
            review=app.screen
            review.query_one('#review-qualification',Button).press()
            await pilot.pause()
            focused=app.screen
            assert focused.query_one('#qualification-experiment',Select).value==CSF_SPEC.id
            assert not focused.query_one('#qualification-save',Button).disabled
            focused.query_one('#qualification-reviewed',Checkbox).value=True
            focused.query_one('#qualification-save',Button).press()
            await pilot.pause()
            assert app.screen is review
        restart=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with restart.run_test() as pilot:
            assert restart.query_one('#monitor-profile',Select).value==p.id
            assert CSF_SPEC.id in restart.monitor_profiles[p.id].qualified_experiments
    asyncio.run(scenario())
    updated=load_monitor_profiles(ROOT)[p.id]
    assert len(revisions(p))==2 and updated.luminance_calibration==p.luminance_calibration
    validate_setup(SetupRequest('fixture_subject','new',CSF_SPEC.id,p.id,values()),CSF_SPEC,updated)
    unchanged=qualify_experiment(updated,config_root(ROOT),CSF_SPEC,reviewed=True)
    assert unchanged==updated and len(revisions(p))==2

def test_compatible_older_luminance_reimport_retains_measurements_and_review(tmp_path):
    p=fixture_profile(verified=True)
    document=example_luminance_document(p)
    document.update(photometer_model_and_method=p.calibration_method,measurement_date='',notes='',measurements=p.to_dict()['luminance_calibration'])
    path=tmp_path/'earlier.json'
    path.write_text(json.dumps(document))
    updated=save_profile(config_root(ROOT),replace(p,notes='Metadata only'),expected_revision=p.revision)
    imported,warnings=import_and_save_luminance(updated,config_root(ROOT),str(path))
    assert imported==updated and len(revisions(p))==2
    assert any('Reused' in warning for warning in warnings)
    assert calibration_progress(imported,config_root(ROOT))['geometry']['measurement_recorded']

def test_fake_photometry_cannot_be_verified_or_qualify_human():
    p=fixture_profile(verified=True)
    fake=replace(p,calibration_method='fake_photometer',qualified_experiments=(CSF_SPEC.id,))
    assert calibration_progress(fake,config_root(ROOT))['luminance']['completed']
    assert not fake.has_verified_luminance_mapping
    assert not all(check['passed'] for check in qualification_checks(CSF_SPEC,fake))
    with pytest.raises(ValueError,match='Fake/synthetic'):
        save_verification(p,config_root(ROOT),geometry_status='verified',calibration_status='verified',timing_status='verified',calibration_method='fake_photometer',reviewed=True)
    with pytest.raises(ValueError,match='Physical photometry'):
        validate_setup(SetupRequest('fixture_subject','new',CSF_SPEC.id,fake.id,values()),CSF_SPEC,fake)

def test_stale_verification_and_physical_changes_do_not_keep_qualification():
    p=fixture_profile(verified=True)
    qualified=qualify_experiment(p,config_root(ROOT),CSF_SPEC,reviewed=True)
    with pytest.raises(ValueError,match='Profile changed'):
        save_verification(p,config_root(ROOT),geometry_status=p.geometry_status,calibration_status=p.calibration_status,timing_status=p.timing_status,calibration_method=p.calibration_method,reviewed=False)
    changed=save_profile(config_root(ROOT),replace(qualified,viewing_distance_m=2.),expected_revision=qualified.revision)
    assert not changed.qualified_experiments and changed.geometry_status!='verified'
    assert not calibration_progress(changed,config_root(ROOT))['geometry']['completed']


def test_changing_timing_does_not_require_unrelated_old_ruler_entry():
    p=fixture_profile(verified=True,observations=False)
    updated=save_verification(p,config_root(ROOT),geometry_status=p.geometry_status,
        calibration_status=p.calibration_status,timing_status='manual_unverified',
        calibration_method=p.calibration_method,reviewed=False)
    assert updated.timing_status=='manual_unverified'
    assert updated.geometry_status==p.geometry_status
    assert updated.luminance_calibration==p.luminance_calibration


def test_verification_explains_fake_saved_photometry_without_requiring_new_test_data():
    from psychophysics_lab.config.calibration_review import luminance_verification_guidance
    p = fixture_profile(verified=False)
    fake = replace(p, calibration_method='photometer fake',
                   calibration_status='manual_unverified')
    message = luminance_verification_guidance(fake, config_root(ROOT))
    assert 'saved digital-command' in message
    assert 'does NOT require repeating unchanged measurements' in message
    assert 'TEST/SYNTHETIC' in message
    assert 'simulation' in message
    assert not fake.has_verified_luminance_mapping


def test_verification_identifies_changed_physical_fields_and_preserves_raw_file():
    from psychophysics_lab.config.calibration_review import luminance_verification_guidance
    from psychophysics_lab.config.calibration_dataset import active_directory, load_active
    p = fixture_profile(verified=False)
    raw = load_active(config_root(ROOT), p)
    path = active_directory(config_root(ROOT), p) / 'luminance.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw), encoding='utf-8')
    original = path.read_bytes()
    changed = replace(p, viewing_distance_m=p.viewing_distance_m + .1)
    message = luminance_verification_guidance(changed, config_root(ROOT))
    assert 'viewing distance' in message
    assert 'does not match this physical setup' in message
    assert 'editing notes' in message
    assert path.read_bytes() == original


def test_verification_screen_explains_saved_test_data_and_can_open_editor(tmp_path):
    from psychophysics_lab.ui.calibration_review import PhysicalVerificationScreen
    from psychophysics_lab.ui.luminance_data import LuminanceDataScreen
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp
    p = fixture_profile(verified=False)
    # Use a persisted test-data method, as the real TUI reloads the saved
    # profile on resume rather than trusting unsaved in-memory decorations.
    fake = save_profile(
        config_root(ROOT), replace(p, calibration_method='photometer fake'),
        expected_revision=p.revision,
    )
    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / 'data')
        async with app.run_test(size=(110, 40)) as pilot:
            screen = PhysicalVerificationScreen(
                fake, experiment_id='legacy_contrast_sensitivity'
            )
            await app.push_screen(screen)
            await pilot.pause()
            text = str(screen.query_one('#verification-luminance-guidance', Static).render())
            assert 'TEST/SYNTHETIC' in text
            screen.query_one('#verification-open-luminance', Button).press()
            await pilot.pause()
            assert isinstance(app.screen, LuminanceDataScreen)
            app.pop_screen()
            await pilot.pause()
            assert app.screen is screen
    asyncio.run(scenario())


def test_calibration_luminance_editor_button_handles_unreadable_active_json(tmp_path):
    """Damaged active data must not crash when researcher clicks its editor."""
    from psychophysics_lab.config.calibration_dataset import active_directory
    from psychophysics_lab.ui.setup import DisplayCheckScreen, PsyCoLabSetupApp
    p = fixture_profile(verified=False)
    path = active_directory(config_root(ROOT), p) / 'luminance.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{broken json', encoding='utf-8')
    original = path.read_bytes()

    async def scenario():
        app = PsyCoLabSetupApp(include_historical=True, repo_root=ROOT, data_root=tmp_path / 'data')
        async with app.run_test(size=(110, 40)) as pilot:
            app.open_hub_page('display')
            await pilot.pause()
            page = app.screen
            assert isinstance(page, DisplayCheckScreen)
            page.query_one('#geometry-monitor', Select).value = p.id
            page.query_one('#open-active-luminance', Button).press()
            await pilot.pause()
            assert app.screen is page
            assert 'Cannot open the active luminance dataset' in str(
                page.query_one('#geometry-status', Static).render()
            )
    asyncio.run(scenario())
    assert path.read_bytes() == original


def test_save_one_geometry_does_not_force_fake_photometry_or_timing(tmp_path):
    from psychophysics_lab.config.calibration_review import save_one_verification
    p=fixture_profile()
    fake=save_profile(config_root(ROOT),replace(p,calibration_method='photometer fake'),
                      expected_revision=p.revision)
    previous_calibration=fake.calibration_status
    previous_timing=fake.timing_status
    with pytest.raises(ValueError,match='Confirm independent'):
        save_one_verification(fake,config_root(ROOT),category='geometry_status',
                              status='verified',reviewed=False)
    changed=save_one_verification(fake,config_root(ROOT),category='geometry_status',
                                  status='verified',reviewed=True)
    assert changed.geometry_status=='verified'
    assert changed.calibration_status==previous_calibration
    assert changed.timing_status==previous_timing
    assert not changed.has_verified_luminance_mapping
    assert changed.luminance_calibration==fake.luminance_calibration
    assert changed.revision==fake.revision+1
    again=save_one_verification(changed,config_root(ROOT),category='geometry_status',
                                status='verified',reviewed=False)
    assert again.revision==changed.revision
    with pytest.raises(ValueError,match='Fake/synthetic'):
        save_one_verification(changed,config_root(ROOT),category='calibration_status',
                              status='verified',reviewed=True)


def test_simple_verification_ui_saves_category_and_keeps_others(tmp_path):
    from psychophysics_lab.ui.calibration_review import PhysicalVerificationScreen
    p=fixture_profile()
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(125,48)) as pilot:
            page=PhysicalVerificationScreen(p,experiment_id=CSF_SPEC.id)
            await app.push_screen(page)
            await pilot.pause()
            assert page.query_one('#verification-category',Select).value=='geometry_status'
            assert page.query_one('#verification-panel-geometry_status').display
            assert not page.query_one('#verification-panel-calibration_status').display
            page.query_one('#verification-geometry_status',Select).value='verified'
            page.query_one('#verification-save-category',Button).press()
            await pilot.pause()
            assert 'Confirm independent' in str(page.query_one('#verification-feedback',Static).render())
            page.query_one('#verification-reviewed',Checkbox).value=True
            page.query_one('#verification-save-category',Button).press()
            await pilot.pause()
            assert app.screen is page
            assert page.profile.geometry_status=='verified'
            assert page.profile.calibration_status==p.calibration_status
            assert page.profile.timing_status==p.timing_status
            assert 'Other categories unchanged' in str(page.query_one('#verification-feedback',Static).render())
            page.query_one('#verification-category',Select).value='calibration_status'
            await pilot.pause()
            assert not page.query_one('#verification-panel-geometry_status').display
            assert page.query_one('#verification-panel-calibration_status').display
            assert not page.query_one('#verification-reviewed',Checkbox).value
    asyncio.run(scenario())


def test_synthetic_photometry_has_no_yes_verified_selection(tmp_path):
    from psychophysics_lab.ui.calibration_review import PhysicalVerificationScreen
    p=fixture_profile()
    fake=save_profile(config_root(ROOT),replace(p,calibration_method='photometer fake'),
                      expected_revision=p.revision)
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(125,48)) as pilot:
            page=PhysicalVerificationScreen(fake,experiment_id=CSF_SPEC.id,
                                            focus_category='calibration_status')
            await app.push_screen(page)
            await pilot.pause()
            assert page.query_one('#verification-category',Select).value=='calibration_status'
            photo=page.query_one('#verification-calibration_status',Select)
            assert 'verified' not in [value for _,value in photo._options]
            assert 'TEST VALUES' in str(page.query_one('#verification-category-guidance',Static).render())
    asyncio.run(scenario())
