"""Explicit, isolated physical presentation tests; never certified acquisition."""

from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4
from ..config.local import config_root
from ..config.preflight import validate_setup, human_requirements
from ..data.locking import file_lock
from ..data.session import atomic_write_json

MARKER = ".psycolab_presentation_tests.json"


@dataclass(frozen=True)
class PresentationTestRequest:
    request: object
    trial_limit: int | None = None

    def __post_init__(self):
        if self.trial_limit is not None and (
            type(self.trial_limit) is not int or not 1 <= self.trial_limit <= 1000
        ):
            raise ValueError(
                "Test length must be 1 to 1000 responses, or None for the full experiment."
            )


class PresentationTestComplete(Exception):
    """A test-only response limit was reached; the study itself is unfinished."""


def validate_presentation(request, spec, profile):
    request = validate_setup(request, spec, profile, mode="configuration")
    # Certification is omitted only for this explicitly labelled test boundary.
    # Shader, physical sampling and connected framebuffer requirements remain.
    failures = [
        r["detail"]
        for r in human_requirements(spec, profile, request.experiment_values)
        if r["key"] in ("contrast", "sampling", "binding") and not r["passed"]
    ]
    if failures:
        raise ValueError("Presentation test blocked: " + "; ".join(failures))
    from .display import preflight_fullscreen_display

    preflight_fullscreen_display(profile)
    return request


def run_presentation_test(action, *, repo_root):
    from .runner import run_request
    from ..config.monitor import load_monitor_profiles
    from psychophysics_lab.experiments._internal.registry import get_experiment

    if not isinstance(action, PresentationTestRequest):
        raise TypeError("Use the explicit presentation-test action.")
    request = action.request
    profile = load_monitor_profiles(repo_root)[request.monitor_profile_id]
    spec = get_experiment(request.experiment_id)
    if spec.procedure is None and action.trial_limit is not None:
        raise ValueError(
            "This historical driver requires a full test; leave the test length blank."
        )
    validate_presentation(request, spec, profile)
    data = (config_root(repo_root).parent / "psycolab_presentation_tests").absolute()
    if data != data.resolve() or any(p.is_symlink() for p in (data, *data.parents)):
        raise ValueError(
            "Presentation test root cannot be redirected through symlinks."
        )
    with file_lock(data.parent / ".psycolab_presentation_tests.lock"):
        if data.exists() and not (data / MARKER).is_file():
            raise ValueError(
                "Existing unmarked folder cannot be used for test presentation. No files were changed."
            )
        atomic_write_json(
            data / MARKER,
            {
                "data_kind": "uncalibrated_presentation_test",
                "human_acquisition_allowed": False,
            },
        )
    reserved = replace(
        request,
        participant_id="presentation_test_" + uuid4().hex,
        session_mode="new",
        data_root=str(data),
    )
    return run_request(
        reserved, repo_root=repo_root, data_root=data, presentation=action
    )
