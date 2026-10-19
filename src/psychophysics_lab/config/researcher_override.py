"""Run-scoped researcher decisions; qualification evidence remains unchanged."""

from dataclasses import asdict, replace
from datetime import datetime, timezone

from .local import content_hash
from .models import ResearcherOverride

# Unknown/new requirements fail closed. Binding, sampling and digital range
# are operational constraints, not declarations a researcher can waive.
OVERRIDABLE_REQUIREMENTS = frozenset({
    "qualification", "protocol", "geometry", "luminance", "timing",
})
ACKNOWLEDGEMENT = (
    "I choose to collect human participant data with these outstanding requirements "
    "and accept responsibility for this run."
)


def outstanding_requirements(spec, profile, values):
    from .preflight import human_requirements
    return tuple(row for row in human_requirements(spec, profile, values)
                 if row["required"] and not row["passed"])


def _review_hash(request, profile, outstanding):
    payload = asdict(request)
    payload.pop("researcher_override")
    # Machine-local paths are not portable scientific metadata.
    payload.pop("data_root")
    return content_hash({"request": payload, "profile": profile.to_dict(),
                         "outstanding_requirements": outstanding})


def authorize_researcher_override(request, spec, profile, *, acknowledged=False):
    """Explicit API equivalent of the confirmation button; default is refusal."""
    from .preflight import effective_requirements, validate_setup
    if acknowledged is not True:
        raise ValueError("Confirm the researcher override before collecting participant data.")
    request = validate_setup(replace(request, researcher_override=None), spec, profile,
                             mode="configuration")
    spec = effective_requirements(spec, request.stimulus_snapshots)
    outstanding = outstanding_requirements(spec, profile, request.experiment_values)
    record = ResearcherOverride(
        confirmed_utc=datetime.now(timezone.utc).isoformat(),
        review_sha256=_review_hash(request, profile, outstanding),
        experiment_id=spec.id,
        waived_requirements=tuple(row["key"] for row in outstanding
                                  if row["key"] in OVERRIDABLE_REQUIREMENTS),
    )
    return validate_setup(replace(request, researcher_override=record), spec, profile)


def validate_researcher_override(request, profile, outstanding):
    record = request.researcher_override
    if not isinstance(record, ResearcherOverride):
        raise ValueError("Researcher override requires an explicit reviewed decision.")
    try:
        confirmed = datetime.fromisoformat(record.confirmed_utc)
    except (ValueError, TypeError):
        raise ValueError("Researcher override needs a valid confirmation time.") from None
    expected = tuple(row["key"] for row in outstanding
                     if row["key"] in OVERRIDABLE_REQUIREMENTS)
    if (confirmed.utcoffset() is None or record.experiment_id != request.experiment_id
            or record.waived_requirements != expected
            or record.review_sha256 != _review_hash(request, profile, outstanding)):
        raise ValueError("Setup or requirements changed since researcher review. Confirm a new override.")
    return record.waived_requirements


def override_provenance(request, spec, profile):
    from .preflight import effective_requirements
    spec = effective_requirements(spec, request.stimulus_snapshots)
    outstanding = outstanding_requirements(spec, profile, request.experiment_values)
    waived = validate_researcher_override(request, profile, outstanding)
    return asdict(request.researcher_override) | {
        "schema_version": 1,
        "acknowledgement": ACKNOWLEDGEMENT,
        "requirements": [row for row in outstanding if row["key"] in waived],
        "calibration_verification_changed": False,
    }
