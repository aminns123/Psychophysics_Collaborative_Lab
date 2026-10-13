"""Run experiment-owned virtual-participant scenarios through real PsyCoLab.

A scenario selects an experiment-specific observer and scenario evaluator.
Generic code checks provenance, files and data integrity only. The scenario's
evaluator decides how to interpret its own model and recovered quantities.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from psychophysics_lab.core.synthetic import simulation_workspace
from psychophysics_lab.data.session import atomic_write_json
from psychophysics_lab.paths import default_data_root, find_repo_root
from psychophysics_lab.data.workspace import preferred_data_root

from ..registry import get_simulation
from ..controls import effective_experiment_values, effective_observer_values
from psychophysics_lab.experiments.registry import get_experiment
from ..run import simulate
from .registry import get_scenario


@dataclass(frozen=True)
class ScenarioRun:
    seed: int
    artifacts: Any
    analysis: Any


@dataclass(frozen=True)
class ScenarioResult:
    experiment_id: str
    scenario_id: str
    passed: bool
    report_file: Path
    runs: tuple[ScenarioRun, ...]
    checks: tuple[dict[str, Any], ...]
    evaluation: dict[str, Any]


def _validator_checks(scenario, run_directory: Path) -> tuple[dict[str, Any], ...]:
    if scenario.validator is None:
        from scripts.validate_run import validate_run
        validator = validate_run
    else:
        validator = scenario.validator
    result = []
    for entry in validator(run_directory):
        # The default run validator returns Check dataclasses. An experiment
        # can instead return custom Check objects with the same attributes.
        name = getattr(entry, "name", None)
        passed = getattr(entry, "passed", None)
        if not isinstance(name, str) or type(passed) is not bool:
            raise TypeError("Scenario validator must yield objects with name:str and passed:bool.")
        result.append({"name": name, "passed": passed, "detail": str(getattr(entry, "detail", ""))})
    if not result:
        raise ValueError("Scenario validator must return at least one check.")
    return tuple(result)


def run_scenario(*, experiment_id: str, scenario_id: str, data_root=None,
                 repo_root=None, seeds=None, observer_parameters=None,
                 experiment_values=None, monitor_profile_id=None, monitor_profile_hash=None) -> ScenarioResult:
    """Execute scenario seeds; save report alongside human and synthetic runs.

    Physical display, participant IDs and acquisition defaults are untouched.
    Any numerical scientific evaluation is supplied by the specific scenario.
    """
    from ..run import simulate

    source_root = (Path(repo_root) if repo_root is not None else find_repo_root()).resolve()
    scenario = get_scenario(experiment_id, scenario_id)
    model = get_simulation(experiment_id)

    # A simulation inherits EVERY normal human-experiment configuration field,
    # including adaptive up/down counts, steps, stopping, display and timing.
    # The model contributes separate observer-only parameters.
    experiment_spec = get_experiment(experiment_id)
    base_experiment = effective_experiment_values(scenario)
    base_observer = effective_observer_values(scenario)
    observer_values = dict(base_observer)
    for key, value in (observer_parameters or {}).items():
        if key not in base_observer:
            raise ValueError(f"Observer setting {key!r} is not declared by this model.")
        original = base_observer[key]
        if type(value) is not type(original) or (isinstance(value, float) and not math.isfinite(value)):
            raise ValueError(f"Observer setting {key!r} has an invalid type or nonfinite value.")
        observer_values[key] = value

    fields = {field.key: field for field in experiment_spec.fields}
    experiment_settings = dict(base_experiment)
    for key, value in (experiment_values or {}).items():
        if key not in fields:
            raise ValueError(f"Experiment setting {key!r} is not a registered human configuration field.")
        if not fields[key].editable and value != base_experiment[key]:
            raise ValueError(f"Experiment setting {key!r} is fixed and cannot be edited.")
        experiment_settings[key] = fields[key].coerce(value)
    experiment_settings = experiment_spec.normalise_values(experiment_settings)
    selected_seeds = tuple(scenario.seeds if seeds is None else seeds)
    if (not selected_seeds or len(selected_seeds) > 128
            or len(set(selected_seeds)) != len(selected_seeds)
            or any(type(seed) is not int or seed < 0 for seed in selected_seeds)):
        raise ValueError("Specify 1–128 unique nonnegative integer seeds.")

    if monitor_profile_id is not None:
        from psychophysics_lab.config.monitor import load_monitor_profiles
        from psychophysics_lab.config.preflight import validate_setup
        from psychophysics_lab.config.models import SetupRequest
        from psychophysics_lab.config.local import content_hash
        profiles = load_monitor_profiles(source_root)
        if monitor_profile_id not in profiles:
            raise ValueError("Selected monitor profile is unavailable; no reference fallback was used.")
        validate_setup(SetupRequest("synthetic_preview", "new", experiment_id, monitor_profile_id,
            experiment_settings, monitor_profile_hash=monitor_profile_hash), experiment_spec,
            profiles[monitor_profile_id], mode="simulation")
        monitor_profile_hash = content_hash(profiles[monitor_profile_id].to_dict())

    selected_data_root = (Path(data_root) if data_root is not None
                          else preferred_data_root(source_root, default_data_root(source_root)))
    root = simulation_workspace(selected_data_root, source_root)
    observer = model.observer_factory(**observer_values)
    records = []
    checks = []
    failed_seed = None
    try:
        for seed in selected_seeds:
            failed_seed = seed
            artifacts, analysis = simulate(
                data_root=root, repo_root=source_root, experiment_id=experiment_id,
                seed=seed, observer=observer, values=experiment_settings,
                monitor_profile_id=monitor_profile_id, monitor_profile_hash=monitor_profile_hash, analyse=True,
            )
            records.append(ScenarioRun(seed, artifacts, analysis))
            manifest = json.loads(artifacts.manifest_file.read_text(encoding="utf-8"))
            checks.append({
                "seed": seed, "name": "virtual participant provenance",
                "passed": (
                    manifest.get("data_kind") == "synthetic"
                    and manifest.get("participant_id") == f"synthetic_{seed}"
                    and (artifacts.run_directory / "SYNTHETIC_DATA.json").exists()
                ),
                "detail": "run must be marked synthetic and belong to a reserved virtual participant",
            })
            if scenario.expect_analysis is not None:
                checks.append({
                    "seed": seed, "name": "experiment-specific analysis expectation",
                    "passed": (analysis is not None) == scenario.expect_analysis,
                    "detail": f"expected analysis={scenario.expect_analysis}, actual={analysis is not None}",
                })
            for check in _validator_checks(scenario, artifacts.run_directory):
                checks.append({"seed": seed, **check})

        failed_seed = None  # failures below are scenario evaluation/export failures
        evaluation = dict(scenario.evaluate(observer, tuple(records))) if scenario.evaluate else {}
        # An experiment may declare its own scientific acceptance checks. These
        # are distinct from the universal provenance and file-integrity checks.
        for entry in evaluation.get("checks", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or type(entry.get("passed")) is not bool:
                raise TypeError("Experiment-specific evaluation checks need name:str and passed:bool.")
            checks.append({
                "seed": "scenario",
                "name": entry["name"],
                "passed": entry["passed"],
                "detail": str(entry.get("detail", "")),
            })
        succeeded = all(bool(check["passed"]) for check in checks)
        # Every observer run is self-contained: the success report lives beside
        # trials.tsv, adaptive_session.json and analysis/ in its OWN run directory.
        # With multiple seeds an identical aggregate report is attached to each run.
        report_file = records[0].artifacts.run_directory / "scenario_report.json"

        def relative(path: Path) -> str:
            return path.resolve().relative_to(root.resolve()).as_posix()

        from psychophysics_lab.analysis.previews import latest_staircase_plot
        def preview_path(record):
            plot = latest_staircase_plot(data_root=root, run_directory=record.artifacts.run_directory)
            return relative(plot) if plot else None

        report = {
            "schema_version": 1,
            "data_kind": "synthetic",
            "experiment_id": experiment_id,
            "scenario_id": scenario_id,
            "description": scenario.description,
            "passed": succeeded,
            "seeds": list(selected_seeds),
            "observer_model": type(observer).__name__,
            "observer_parameters": observer_values,
            "experiment_values": experiment_settings,
            "monitor_profile_id": monitor_profile_id or model.monitor_profile_id,
            "display_hardware_used": False,
            "expected_analysis": scenario.expect_analysis,
            "tests": checks,
            "experiment_evaluation": evaluation,
            "runs": [
                {
                    "seed": record.seed,
                    "relative_run_directory": relative(record.artifacts.run_directory),
                    "status": record.artifacts.status,
                    "accepted_responses": record.artifacts.accepted_trials,
                    "canonical_trials": relative(record.artifacts.trial_log_file),
                    "canonical_manifest": relative(record.artifacts.manifest_file),
                    "staircase_plot": preview_path(record),
                    "threshold_plot": (
                        relative(Path(record.analysis.plot_file))
                        if record.analysis is not None and getattr(record.analysis, "plot_file", None) is not None
                        else None
                    ),
                    "relative_analysis_summary": (
                        relative(Path(record.analysis.summary_json))
                        if record.analysis is not None and getattr(record.analysis, "summary_json", None) is not None
                        else None
                    ),
                }
                for record in records
            ],
            "scientific_warning": (
                "This test verifies software processing with experiment-specific virtual observers. "
                "It is not human-subject evidence or physical calibration, and estimated reversal "
                "thresholds need not coincide with a virtual observer's psychometric midpoint."
            ),
        }
        for record in records:
            atomic_write_json(record.artifacts.run_directory / "scenario_report.json", report)
        return ScenarioResult(experiment_id, scenario_id, succeeded, report_file,
                              tuple(records), tuple(checks), evaluation)
    except BaseException as exc:
        # Preserve a scenario-level failure alongside every already acquired
        # run, even if a later seed or scientific evaluator fails. The original
        # acquisition exception remains authoritative.
        failure = {"schema_version": 1, "data_kind": "synthetic", "passed": False,
                   "status": "error", "experiment_id": experiment_id,
                   "scenario_id": scenario_id, "seeds": list(selected_seeds),
                   "failed_seed": failed_seed, "error": repr(exc),
                   "display_hardware_used": False, "tests": checks,
                   "completed_seed_records": [record.seed for record in records],
                   "scientific_warning": "Partial synthetic scenario; no physical calibration or human evidence."}
        for record in records:
            try:
                atomic_write_json(record.artifacts.run_directory / "scenario_report.json", failure)
            except Exception as report_error:
                exc.add_note(f"Could not save partial scenario report: {report_error!r}")
        raise
