"""Accepting saved test readings is navigation, never an evidence mutation."""
import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.config.calibration_dataset import load_active, observation, save_active
from psychophysics_lab.config.calibration_progress import calibration_progress
from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.models import LuminanceCalibrationPoint, SetupRequest
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.preflight import human_blockers
from psychophysics_lab.experiments.contrast_sensitivity import CSF_SPEC
from psychophysics_lab.ui.luminance_data import LuminanceDataScreen
from psychophysics_lab.ui.setup import DisplayCheckScreen, PsyCoLabSetupApp, ReviewScreen

ROOT = Path(__file__).resolve().parents[1]


def saved_test_profile(*, active=True, empty=False):
    root = config_root(ROOT)
    reference = load_monitor_profiles(ROOT)['legacy_reference_display']
    points = () if empty else tuple(LuminanceCalibrationPoint(x, y) for x, y in
                                    ((.1, 9.66667), (.25, 80.3333), (.5, 249.667), (1., 499.667)))
    profile = save_profile(root, replace(reference, id='acceptance_test', origin='local',
        luminance_calibration=points, calibration_method='synthetic test values',
        luminance_data_kind='synthetic', calibration_status='manual_unverified',
        qualified_experiments=()))
    if active:
        draft = load_active(root, profile)
        draft['observations'] = [observation(p.screen_intensity, p.luminance_cdm2 + offset,
                                            kind='synthetic') for p in points for offset in (-.5, 0, .5)]
        profile, _ = save_active(root, profile, draft, expected_version=0)
    return root, profile


def evidence(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in (root/'profiles').rglob('*') if p.is_file()}


@pytest.mark.parametrize('size', [(80, 24), (120, 44)])
def test_researcher_accepts_existing_mapping_once_without_rewriting_readings(tmp_path, size):
    root, profile = saved_test_profile()
    before = evidence(root)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'participants')
        async with app.run_test(size=size) as pilot:
            app.query_one('#run-intent', Select).value = 'human'
            app.display_guide_target_profile_id = profile.id
            app.query_one('#nav-display', Button).press()
            await pilot.pause()
            calibration = app.screen
            calibration._go_to_stage('luminance')
            calibration.query_one('#open-active-luminance', Button).press()
            await pilot.pause()
            assert await pilot.click('#dataset-accept')
            await pilot.pause()
            assert app.screen is calibration
            assert calibration.active_calibration_stage == 'timing'
            assert app.run_intent == 'human'
            assert calibration._profile().has_accepted_luminance_mapping
            assert not calibration._profile().has_verified_luminance_mapping
            snapshot = evidence(root)
            calibration.query_one('#open-active-luminance', Button).press()
            await pilot.pause()
            app.screen.query_one('#dataset-accept', Button).press()
            await pilot.pause()
            assert evidence(root) == snapshot
    asyncio.run(scenario())
    after = evidence(root)
    for path, payload in before.items():
        if '/.history/' in path or '/revision_' in path or path.endswith('/luminance.json'):
            assert after[path] == payload
    current = load_monitor_profiles(ROOT)[profile.id]
    assert current.revision == profile.revision + 1
    assert current.luminance_calibration == profile.luminance_calibration
    assert current.has_accepted_luminance_mapping
    assert not current.has_verified_luminance_mapping
    assert current.luminance_data_kind == 'synthetic'
    assert not current.qualified_experiments
    assert human_blockers(CSF_SPEC, current, CSF_SPEC.field_defaults())


def test_stale_physical_configuration_blocks_acceptance(tmp_path):
    root, profile = saved_test_profile()
    changed = save_profile(root, replace(profile, viewing_distance_m=profile.viewing_distance_m+.1),
                           expected_revision=profile.revision)
    before = evidence(root)
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'participants')
        async with app.run_test() as pilot:
            await app.push_screen(LuminanceDataScreen(changed))
            await pilot.pause()
            app.screen.query_one('#dataset-accept', Button).press()
            await pilot.pause()
            assert 'different physical display configuration' in str(
                app.screen.query_one('#dataset-feedback', Static).render())
    asyncio.run(scenario())
    assert evidence(root) == before


@pytest.mark.parametrize('edit', ['metadata', 'typed_readings', 'added_readings'])
def test_accept_requires_explicit_resolution_of_real_unsaved_edits(tmp_path, edit):
    root, profile = saved_test_profile()
    before = evidence(root)

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'participants')
        async with app.run_test() as pilot:
            await app.push_screen(LuminanceDataScreen(profile))
            await pilot.pause()
            page = app.screen
            if edit == 'metadata':
                page.query_one('#dataset-notes', Input).value = 'Unsaved note'
            else:
                page.query_one('#dataset-readings', Input).value = '250'
                if edit == 'added_readings':
                    page.query_one('#dataset-add', Button).press()
            await pilot.pause()
            for button in ('dataset-keep-test',):
                page.query_one('#'+button, Button).press()
                await pilot.pause()
                assert app.screen is page
                assert 'Unsaved edits remain' in str(page.query_one('#dataset-feedback', Static).render())
            assert page.query_one('#dataset-discard', Button).display
            page.query_one('#dataset-discard', Button).press()
            await pilot.pause()
            assert page.draft == page.saved
            assert not page._has_unsaved_changes() and not page._has_pending_readings()
            page.query_one('#dataset-keep-test', Button).press()
            await pilot.pause()
            assert len(app.screen_stack) == 1
            assert app.query_one('#run-intent', Select).value == 'test'
            assert app.query_one('#monitor-profile', Select).value == profile.id

    asyncio.run(scenario())
    assert evidence(root) == before


@pytest.mark.parametrize('active', [False, True])
def test_unchanged_save_does_not_migrate_or_revise_dataset(tmp_path, active):
    root, profile = saved_test_profile(active=active)
    before = evidence(root)

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'participants')
        async with app.run_test() as pilot:
            await app.push_screen(LuminanceDataScreen(profile))
            await pilot.pause()
            app.screen.query_one('#dataset-save', Button).press()
            await pilot.pause()
            assert 'No changes to save' in str(app.screen.query_one('#dataset-feedback', Static).render())

    asyncio.run(scenario())
    assert evidence(root) == before


def test_no_saved_values_cannot_be_accepted(tmp_path):
    root, profile = saved_test_profile(active=False, empty=True)
    before = evidence(root)

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'participants')
        async with app.run_test() as pilot:
            await app.push_screen(LuminanceDataScreen(profile))
            await pilot.pause()
            assert app.screen.query_one('#dataset-accept', Button).disabled
            assert app.screen.query_one('#dataset-keep-test', Button).disabled
            assert not calibration_progress(profile, root)['luminance']['completed']

    asyncio.run(scenario())
    assert evidence(root) == before


def test_accept_returns_to_existing_experiment_review_preserving_human_mode(tmp_path):
    root, profile = saved_test_profile()
    before = evidence(root)
    values = CSF_SPEC.normalise_values(CSF_SPEC.field_defaults() | {
        'Max_monitor_Luminance': 499.667, 'Background_Luminance': 249.667,
        'Background_Screen_intensity': .5})
    request = SetupRequest('test_subject', 'new', CSF_SPEC.id, profile.id,
                           values, str(tmp_path/'participants'))

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path/'participants')
        async with app.run_test(size=(120, 44)) as pilot:
            app.run_intent = 'human'
            await app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            review = app.screen
            review.resolve_requirement('luminance')
            await pilot.pause()
            assert 'Review' in str(app.screen.query_one('#dataset-accept', Button).label)
            app.screen.query_one('#dataset-accept', Button).press()
            await pilot.pause()
            assert app.screen is review
            assert review.request.experiment_values == request.experiment_values
            assert review.query_one('#review-run-intent', Select).value == 'human'
            assert not next(row for row in review.readiness_report['requirements'] if row['key']=='luminance')['passed']
            assert not review.readiness_report['human_ready']

    asyncio.run(scenario())
    after=evidence(root)
    for path,payload in before.items():
        if '/.history/' in path or '/revision_' in path or path.endswith('/luminance.json'):
            assert after[path] == payload
    current=load_monitor_profiles(ROOT)[profile.id]
    assert current.has_accepted_luminance_mapping
    assert not current.has_verified_luminance_mapping
    assert human_blockers(CSF_SPEC,current,request.experiment_values)
