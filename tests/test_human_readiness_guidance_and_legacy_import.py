"""Human Review checklist/navigation and explicit legacy pyglet import regression."""
import ast
import asyncio
from dataclasses import replace
from pathlib import Path

from textual.widgets import Button, Static

from test_calibration_review_completion import ROOT, fixture_profile, values
from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.human_readiness import (
    experiment_readiness, next_human_requirement, human_readiness_checklist,
)
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.experiments.contrast_sensitivity import SPEC as CSF_SPEC
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen
from psychophysics_lab.ui.calibration_review import PhysicalVerificationScreen


def _request(profile):
    return validate_setup(
        SetupRequest("fixture_human", "new", CSF_SPEC.id, profile.id, values()),
        CSF_SPEC, profile, mode="configuration"
    )




def test_photometry_blocker_is_prioritised_before_experiment_qualification():
    profile=fixture_profile(verified=True)
    pending=save_profile(config_root(ROOT),replace(profile,calibration_status="manual_unverified"),
                         expected_revision=profile.revision)
    report=experiment_readiness(_request(pending),CSF_SPEC,pending,repo_root=ROOT)
    assert not report["human_ready"]
    assert next_human_requirement(report)["key"]=="luminance"
    row=next(item for item in report["requirements"] if item["key"]=="luminance")
    assert row["destination"]=="verification"
    assert "photometry" in row["action"].lower()
    checklist=human_readiness_checklist(report)
    names=[item["key"] for item in checklist]
    assert names.index("luminance")<names.index("qualification")
    assert not row["passed"]


def test_test_readings_require_real_measurements_not_a_verified_checkbox():
    profile=fixture_profile(verified=True)
    fake=save_profile(config_root(ROOT),replace(profile,calibration_method="photometer fake",
                          calibration_status="accepted"),
                      expected_revision=profile.revision)
    report=experiment_readiness(_request(fake),CSF_SPEC,fake,repo_root=ROOT)
    row=next(x for x in report["requirements"] if x["key"]=="luminance")
    assert row["destination"]=="calibration"
    assert "real photometer" in row["action"].lower()
    assert next_human_requirement(report)["key"]=="luminance"
    assert not report["human_ready"]


def test_human_review_marks_next_check_and_opens_photometry_verification(tmp_path):
    profile=fixture_profile(verified=True)
    pending=save_profile(config_root(ROOT),replace(profile,calibration_status="manual_unverified"),
                         expected_revision=profile.revision)
    async def scenario():
        app=PsyCoLabSetupApp(include_historical=True, repo_root=ROOT,data_root=tmp_path/"data")
        app.run_intent="human"
        async with app.run_test(size=(120,46)) as pilot:
            review=ReviewScreen(request=_request(pending))
            await app.push_screen(review)
            await pilot.pause()
            assert review.next_requirement_key=="luminance"
            assert "NEXT REQUIRED ACTION" in str(
                review.query_one("#human-next-action",Static).render())
            assert "luminance" in str(review.query_one("#human-checklist",Static).render()).lower()
            assert review.query_one("#readiness-luminance",Static).has_class("readiness-next")
            assert review.query_one("#readiness-qualification",Static).has_class("readiness-blocked")
            review.query_one("#review-next-action",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,PhysicalVerificationScreen)
            assert app.screen.focus_category=="calibration_status"
    asyncio.run(scenario())
