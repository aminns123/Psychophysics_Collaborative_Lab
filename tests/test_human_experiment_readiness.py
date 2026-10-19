"""Isolated software evidence: these fixtures never certify laboratory hardware."""
import asyncio
import ast
from dataclasses import replace
from types import SimpleNamespace
import pytest
from textual.widgets import Button, Checkbox, Input, Select, Static
from test_calibration_review_completion import ROOT, fixture_profile, values, revisions
from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.config.human_readiness import experiment_readiness
from psychophysics_lab.config.calibration_review import qualify_experiment
from psychophysics_lab.experiments.contrast_sensitivity import SPEC as CSF_SPEC
from psychophysics_lab.stimulus_library import ContrastSensitivityGrating
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen, ExperimentConfigScreen, DisplayCheckScreen
from psychophysics_lab.ui.calibration_review import PhysicalVerificationScreen, ExperimentQualificationScreen


def request(p, v=None):
    return validate_setup(SetupRequest('fixture_subject','new',CSF_SPEC.id,p.id,v or values()),CSF_SPEC,p,mode='configuration')


@pytest.mark.parametrize("background,expected",[(.1,.2),(.25,.5),(.5,1.),(.75,.5),(.9,.2)])
def test_active_grating_gamut_depends_on_selected_background(background,expected):
    from psychophysics_lab.experiments import contrast_sensitivity as csf
    # Use the actual representable digital headroom: e.g. 2*(1-.9) is
    # slightly below literal .2 in binary floating point.
    limit=2*min(background,1-background)
    settings = csf.SPEC.normalise_values(csf.SPEC.field_defaults() | {
        "background_intensity": background, "starting_contrast": limit
    })
    assert csf.maximum_contrast(settings,{}) == pytest.approx(expected)
    ContrastSensitivityGrating.validate({
        "background": background, "contrast": limit
    })
    with pytest.raises(ValueError, match="digital range"):
        ContrastSensitivityGrating.validate({"background":background,"contrast":limit+.01})


@pytest.mark.parametrize("bad",[float("nan"), float("inf"), -0.1])
def test_active_grating_rejects_invalid_selected_contrast(bad):
    from psychophysics_lab.experiments.contrast_sensitivity import SPEC
    with pytest.raises(ValueError):
        SPEC.normalise_values(SPEC.field_defaults() | {"starting_contrast":bad})


def test_completed_setup_is_not_human_verification_and_fake_pairs_remain_test_data():
    p=fixture_profile()
    report=experiment_readiness(request(p),CSF_SPEC,p,repo_root=ROOT)
    rows={r['key']:r for r in report['requirements']}
    assert rows['setup']['passed'] and not rows['luminance']['passed']
    assert not report['human_ready'] and report['simulation_available']
    fake=save_profile(config_root(ROOT),replace(p,calibration_method='fake_photometer'),expected_revision=p.revision)
    report=experiment_readiness(request(fake),CSF_SPEC,fake,repo_root=ROOT)
    row=next(r for r in report['requirements'] if r['key']=='luminance')
    assert '5 intensity/luminance pairs' in row['detail'] and 'synthetic/test data' in row['detail']
    assert row['stage']=='luminance' and not report['human_ready'] and report['simulation_available']
    with pytest.raises(ValueError,match='cannot be qualified'):
        qualify_experiment(fake,config_root(ROOT),CSF_SPEC,reviewed=True,values=values())


def test_verification_then_qualification_refresh_same_review_and_restart(tmp_path):
    p=fixture_profile()
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test(size=(100,30)) as pilot:
            review=ReviewScreen(request=request(p)); app.push_screen(review); await pilot.pause()
            original_hash=review.request.monitor_profile_hash
            review.resolve_requirement('qualification'); await pilot.pause()
            assert isinstance(app.screen,ExperimentQualificationScreen)
            assert app.screen.query_one('#qualification-save',Button).disabled
            assert 'BLOCKED' in str(app.screen.query_one('#qualification-checks',Static).render())
            app.screen.query_one('#qualification-back',Button).press(); await pilot.pause()
            review.resolve_requirement('luminance'); await pilot.pause()
            # The pair table already exists; the missing check is physical
            # verification, so open it directly (no redundant editor hop).
            assert isinstance(app.screen,PhysicalVerificationScreen)
            for key in ('geometry_status','calibration_status','timing_status'):
                app.screen.query_one('#verification-'+key,Select).value='verified'
            app.screen.query_one('#verification-method',Input).value='Laboratory meter fixture'
            app.screen.query_one('#verification-reviewed',Checkbox).value=True
            app.screen.query_one('#verification-save',Button).press(); await pilot.pause()
            assert app.screen is review
            assert review.request.monitor_profile_hash!=original_hash
            assert all(r['passed'] for r in review.readiness_report['requirements'] if r['key'] in ('geometry','luminance','timing'))
            assert not review.readiness_report['human_ready']
            review.resolve_requirement('qualification'); await pilot.pause()
            assert not app.screen.query_one('#qualification-save',Button).disabled
            app.screen.query_one('#qualification-reviewed',Checkbox).value=True
            app.screen.query_one('#qualification-save',Button).press(); await pilot.pause()
            assert app.screen is review
            # A photometrically verified monitor and explicit local
            # qualification do not waive the separate protocol-level blocker.
            assert not review.readiness_report['human_ready']
            assert any(r['key']=='protocol' and not r['passed'] for r in review.readiness_report['requirements'])
        restart=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        assert restart.config_drafts[('fixture_subject',CSF_SPEC.id,p.id)]==values()
        saved=restart.monitor_profiles[p.id]
        assert CSF_SPEC.id in saved.qualified_experiments and saved.has_verified_luminance_mapping
    asyncio.run(scenario())
    assert len(revisions(p))==3


def test_csf_background_and_starting_contrast_round_trip_through_review(tmp_path):
    p=fixture_profile()
    selected=values() | {"background_intensity": .25, "starting_contrast": .25}
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(100,30)) as pilot:
            original=ExperimentConfigScreen(data_root=tmp_path/"data",
                participant_id="fixture_subject",session_mode="new",
                experiment=CSF_SPEC,monitor_profile_id=p.id,defaults=selected)
            app.push_screen(original);await pilot.pause()
            assert float(original.query_one("#field-background-intensity",Input).value)==.25
            original.query_one("#review",Button).press();await pilot.pause()
            review=app.screen
            assert isinstance(review,ReviewScreen)
            assert review.request.experiment_values["starting_contrast"]==pytest.approx(.25)
            review.query_one("#back",Button).press();await pilot.pause()
            assert app.screen is original
            original.query_one("#field-starting-contrast",Input).value=".18"
            original.query_one("#review",Button).press();await pilot.pause()
            assert app.screen.request.experiment_values["starting_contrast"]==pytest.approx(.18)
    asyncio.run(scenario())
    assert not (tmp_path/"data").exists()

def test_physical_change_does_not_refresh_stale_hash_or_bypass_final_guard(tmp_path,monkeypatch):
    p=qualify_experiment(fixture_profile(verified=True),config_root(ROOT),CSF_SPEC,reviewed=True,values=values())
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            review=ReviewScreen(request=request(p)); app.push_screen(review); await pilot.pause()
            old_hash=review.request.monitor_profile_hash
            review.resolve_requirement('qualification'); await pilot.pause()
            save_profile(config_root(ROOT),replace(p,viewing_distance_m=2.),expected_revision=p.revision)
            app.screen.query_one('#qualification-back',Button).press(); await pilot.pause()
            assert app.screen is review and review.request.monitor_profile_hash==old_hash
            assert not review.readiness_report['human_ready']
            review.query_one('#run',Button).press(); await pilot.pause()
            assert app.screen is review and 'changed' in str(review.query_one('#readiness-technical',Static).render()).lower()
    asyncio.run(scenario())
    assert not load_monitor_profiles(ROOT)[p.id].qualified_experiments and not (tmp_path/'data').exists()


def test_protocol_cannot_be_certified_by_monitor_calibration_alone():
    p=qualify_experiment(fixture_profile(verified=True),
                        config_root(ROOT),CSF_SPEC,reviewed=True,values=values())
    report=experiment_readiness(request(p),CSF_SPEC,p,repo_root=ROOT)
    assert CSF_SPEC.id in p.qualified_experiments
    assert not report["human_ready"]
    assert any(r["key"]=="protocol" and not r["passed"]
               for r in report["requirements"])
    # The explicit researcher override is tested separately at the actual
    # human acquisition boundary; no calibration flag is rewritten here.

def test_current_grating_range_guard_rejects_invalid_modulation_without_clipping():
    # The production grating must reject unrenderable digital modulation,
    # independent of any retired shader source.
    legal={"background":.25,"contrast":.5}
    ContrastSensitivityGrating.validate(legal)
    with pytest.raises(ValueError,match="digital range"):
        ContrastSensitivityGrating.validate(legal | {"contrast":.50001})


def test_editing_current_csf_values_after_review_returns_to_same_form(tmp_path):
    p=fixture_profile()
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test() as pilot:
            original=ExperimentConfigScreen(data_root=tmp_path/"data",
                participant_id="fixture_subject",session_mode="new",
                experiment=CSF_SPEC,monitor_profile_id=p.id,defaults=values())
            app.push_screen(original);await pilot.pause()
            original.query_one("#review",Button).press();await pilot.pause()
            review=app.screen
            assert isinstance(review,ReviewScreen)
            review.query_one("#back",Button).press();await pilot.pause()
            assert app.screen is original
            original.query_one("#field-starting-contrast",Input).value=".08"
            original.query_one("#review",Button).press();await pilot.pause()
            assert app.screen.request.experiment_values["starting_contrast"]==pytest.approx(.08)
    asyncio.run(scenario())
    assert len(revisions(p))==1

def test_fullscreen_diagnostic_restart_restores_calibration_then_review(tmp_path):
    p=fixture_profile()
    reviewed=request(load_monitor_profiles(ROOT)[p.id])
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data')
        async with app.run_test() as pilot:
            review=ReviewScreen(request=reviewed); app.push_screen(review); await pilot.pause()
            review.resolve_requirement('setup'); await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
        # Simulate the existing app loop returning after a mocked diagnostic.
        restart=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/'data',geometry_summary='Fixture software diagnostic completed')
        async with restart.run_test() as pilot:
            await pilot.pause()
            assert isinstance(restart.screen,DisplayCheckScreen)
            restart.screen.query_one('#calibration-return',Button).press(); await pilot.pause()
            assert isinstance(restart.screen,ReviewScreen)
            assert restart.screen.request==reviewed
            assert not restart.screen.readiness_report['human_ready']
            assert restart.screen.readiness_report['simulation_available']
    asyncio.run(scenario()); assert len(revisions(p))==1


def test_qualification_rejects_current_unsafe_contrast_without_saving():
    p=fixture_profile(verified=True)
    v=values()|{'background_intensity':.25,'starting_contrast':1.}
    with pytest.raises(ValueError,match='contrast|digital range'):
        qualify_experiment(p,config_root(ROOT),CSF_SPEC,reviewed=True,values=v)
    assert len(revisions(p))==1 and not load_monitor_profiles(ROOT)[p.id].qualified_experiments
