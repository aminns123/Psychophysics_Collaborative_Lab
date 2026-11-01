"""Reusable software-contract checks for *any* scientist-authored experiment.

No experiment-specific test Python is required. The checks inspect the
registered source contract and selected effective settings. Full synthetic
execution and saved-run verification remain with the established simulator
and scripts.validate_run; this module does not duplicate their logic.

A PASS says nothing about physical stimulus quality or scientific validity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SoftwareCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Researchers can use these questions without learning pytest or writing a
# bespoke automated suite. These are deliberately unverified statements.
RESEARCHER_ACCEPTANCE = (
    "Do the independent stimuli look correct, at the requested positions and overlap order?",
    "Does each condition select the correct interval, response and scientific strength?",
    "Are adaptation/constant levels, stopping criteria and threshold rules suitable for the study?",
    "Are contrast units, geometry, background and saved measures scientifically interpretable?",
    "Have the actual monitor, photometry, display timing and input devices been qualified?",
)


def check_experiment(spec, selected_values: Mapping[str, Any]) -> tuple[SoftwareCheck, ...]:
    """Universal declaration checks, with actionable messages rather than a crash.

    The experiment's own validator still controls study-specific constraints;
    there is no framework guess about which contrast range, stimulus shape or
    trial sequence is scientifically appropriate.
    """
    results = []

    def run(name, operation):
        try:
            detail = operation()
        except (ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
            results.append(SoftwareCheck(name, False, f"{type(exc).__name__}: {exc}"))
        else:
            results.append(SoftwareCheck(name, True, str(detail)))

    normalised = {}

    def validate_settings():
        nonlocal normalised
        if not isinstance(selected_values, Mapping):
            raise TypeError("Experiment settings must be a mapping.")
        normalised = spec.normalise_values(selected_values)
        return f"{len(normalised)} selected settings and study-specific validation checked."

    run("Effective settings", validate_settings)

    def validate_stimuli():
        from .stimuli.registry import get_stimulus

        slots = dict(spec.stimulus_slots)
        defaults = dict(spec.stimulus_defaults)
        if not slots and not defaults:
            return "No visual stimuli declared; response-only studies may be valid."
        if set(defaults) != set(slots):
            raise ValueError(
                "Stimulus slots and defaults disagree: "
                f"no default for {sorted(set(slots)-set(defaults))}; "
                f"unrecognized defaults {sorted(set(defaults)-set(slots))}."
            )
        for slot, identity in defaults.items():
            stimulus = get_stimulus(identity)
            if stimulus.family != slots[slot]:
                raise ValueError(
                    f"{slot}: selected {identity!r} has family {stimulus.family!r}, "
                    f"but the slot requires {slots[slot]!r}."
                )
        return f"{len(slots)} independent stimulus slots and compatible defaults verified."

    run("Stimulus references and families", validate_stimuli)

    def validate_session():
        if not normalised:
            raise ValueError("Correct the effective settings before resolving the session opening.")
        spec.session_start.resolve(normalised).validate_slots(spec.stimulus_slots)
        return "Once-only readiness and opening event slots/timings resolve."

    run("Session opening", validate_session)

    def validate_method():
        if not spec.supports_simulation:
            raise ValueError(
                "Software simulation is not declared; a human run cannot substitute for a synthetic test."
            )
        field = next((x for x in spec.fields if x.key == "contrast_method"), None)
        if field is None:
            return "The study declares its own method; its procedure is checked by execution."
        if not normalised:
            raise ValueError("Correct the effective settings before selecting the method.")
        name = normalised.get("contrast_method")
        if name not in field.choices:
            raise ValueError(f"Unsupported contrast method {name!r}.")
        if name == "constant_stimuli" and spec.method_planner is not None:
            schedule = spec.method_planner(normalised, 0)
            if not schedule:
                raise ValueError("Constant-stimuli method planned no trials.")
            return f"Selected constant-stimuli method plans {len(schedule)} trials."
        return f"Selected {name!r} method; update and stopping behaviour tested by simulation."

    run("Selected method and synthetic capability", validate_method)
    return tuple(results)


def software_check_payload(spec, checks, *, synthetic_run=None, data_checks=()):
    """Human-readable evidence, explicitly NOT scientific certification."""
    return {
        "schema_version": 1,
        "experiment_id": spec.id,
        "result": "pass" if all(item.passed for item in checks)
                  and (synthetic_run is None or synthetic_run.get("passed") is True)
                  else "fail",
        "evidence_scope": "software_only",
        "physical_display_used": False,
        "human_participant_used": False,
        "scientific_validation": "researcher_review_required",
        "generic_contract_checks": [item.to_dict() for item in checks],
        "synthetic_run": synthetic_run,
        "saved_run_validation": [asdict(item) for item in data_checks],
        "researcher_acceptance_questions": list(RESEARCHER_ACCEPTANCE),
        "note": (
            "One selected configuration and synthetic observer were checked. "
            "Neither a passed generic check nor Ready status establishes scientific "
            "validity, display luminance, geometry, timing, or human-run safety."
        ),
    }


def format_checks(checks) -> str:
    return "\n".join(
        f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}"
        for check in checks
    )
