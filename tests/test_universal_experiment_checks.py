"""Any researcher-created experiment can use the same software test contract.

No scientist-authored per-experiment pytest is required; tests below exercise
the universal checker against existing real specs and deliberately bad drafts.
"""
from dataclasses import replace
import json

import pytest

from psychophysics_lab.experiment_checks import (
    RESEARCHER_ACCEPTANCE, SoftwareCheck, check_experiment,
    format_checks, software_check_payload,
)
from psychophysics_lab.experiments._internal.registry import (
    get_experiment, list_experiments,
)
from scripts.validate_run import Check as DataCheck


@pytest.mark.parametrize("spec", list_experiments(), ids=lambda s: s.id)
def test_every_registered_study_has_one_total_software_check_contract(spec):
    """Valid *or invalid* defaults report actionable results, never require tests."""
    checks = check_experiment(spec, spec.field_defaults())
    assert [entry.name for entry in checks] == [
        "Effective settings",
        "Stimulus references and families",
        "Session opening",
        "Selected method and synthetic capability",
    ]
    assert all(isinstance(entry.passed, bool) and entry.detail for entry in checks)


def test_one_authoritative_spec_contract_on_existing_example():
    spec = get_experiment("example_experiment")
    checks = check_experiment(spec, spec.field_defaults())
    assert all(row.passed for row in checks), format_checks(checks)


def test_bad_stimulus_is_reported_without_mutating_source_or_running_humans():
    spec = get_experiment("example_experiment")
    changed = replace(spec, stimulus_defaults={
        **spec.stimulus_defaults,
        next(iter(spec.stimulus_slots)): "no_such_stimulus",
    })
    checks = check_experiment(changed, changed.field_defaults())
    failure = next(entry for entry in checks
                   if entry.name == "Stimulus references and families")
    assert not failure.passed
    assert "no_such_stimulus" in failure.detail
    assert "FAIL" in format_checks(checks)


def test_bad_settings_are_actionable_without_custom_tests():
    spec = get_experiment("example_experiment")
    checks = check_experiment(spec, spec.field_defaults() | {"never_defined": 5})
    assert not checks[0].passed
    assert "never_defined" in checks[0].detail
    assert not next(row for row in checks if row.name == "Session opening").passed


def test_run_verification_is_separate_from_scientific_acceptance():
    spec = get_experiment("example_experiment")
    checks = check_experiment(spec, spec.field_defaults())
    good = software_check_payload(
        spec, checks,
        synthetic_run={"passed": True, "status": "completed", "accepted_trials": 2},
        data_checks=[DataCheck("Canonical trial schema", True)],
    )
    assert good["result"] == "pass"
    assert good["physical_display_used"] is False
    assert good["human_participant_used"] is False
    assert good["scientific_validation"] == "researcher_review_required"
    assert len(good["researcher_acceptance_questions"]) == len(RESEARCHER_ACCEPTANCE)
    assert good["saved_run_validation"][0]["passed"] is True
    assert json.loads(json.dumps(good))["schema_version"] == 1

    bad = software_check_payload(
        spec, checks, synthetic_run={"passed": False, "status": "max_trials_reached"},
    )
    assert bad["result"] == "fail"
    assert bad["scientific_validation"] == "researcher_review_required"


def test_a_new_researcher_can_pass_generic_checks_without_per_study_test_code():
    """Study choices may be edited in source/Review; generic contract is reused."""
    spec = get_experiment("example_experiment")
    selected = spec.normalise_values(spec.field_defaults())
    assert all(row.passed for row in check_experiment(spec, selected))
