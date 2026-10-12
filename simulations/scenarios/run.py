"""Run experiment-owned virtual-participant scenarios through real PsyCoLab.

A scenario selects an experiment-specific observer and scenario evaluator.
Generic code checks provenance, files and data integrity only. The scenario's
evaluator decides how to interpret its own model and recovered quantities.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

from psychophysics_lab.core.synthetic import simulation_workspace
from psychophysics_lab.data.session import atomic_write_json
from psychophysics_lab.paths import default_data_root, find_repo_root
from psychophysics_lab.data.workspace import preferred_data_root

from ..registry import get_simulation
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
                 experiment_values=None) -> ScenarioResult:
    """Execute scenario seeds; save report alongside human and synthetic runs.

    Physical display, participant IDs and acquisition defaults are untouched.
    Any numerical scientific evaluation is supplied by the specific scenario.
    """
    from ..run import simulate

    source_root = (Path(repo_root) if repo_root is not None else find_repo_root()).resolve()
    scenario = get_scenario(experiment_id, scenario_id)
    model = get_simulation(experiment_id)

    # All configurable keys must have been explicitly exposed by the author
    # of this scenario. Unknown keys and nonfinite/type-changing overrides
    # fail before touching any participant or analysis directories.
    def effective(base, override, label):
        values = dict(base)
        for key, value in (override or {}).items():
            if key not in values:
                raise ValueError(f"{label} {key!r} is not configurable in this scenario.")
            expected = values[key]
            if type(value) is not type(expected):
                raise ValueError(f"{label} {key!r} must retain its declared type.")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"{label} {key!r} must be finite.")
            values[key] = value
        return values

    observer_values = effective(scenario.observer_parameters, observer_parameters, "Observer setting")
    experiment_settings = effective(scenario.experiment_values, experiment_values, "Experiment setting")
    selected_seeds = tuple(scenario.seeds if seeds is None else seeds)
    if (not selected_seeds or len(selected_seeds) > 128
            or len(set(selected_seeds)) != len(selected_seeds)
            or any(type(seed) is not int or seed < 0 for seed in selected_seeds)):
        raise ValueError("Specify 1–128 unique nonnegative integer seeds.")

    selected_data_root = (Path(data_root) if data_root is not None
                          else preferred_data_root(source_root, default_data_root(source_root)))
    root = simulation_workspace(selected_data_root, source_root)
    observer = model.observer_factory(**observer_values)
    records = []
    checks = []
    for seed in selected_seeds:
        artifacts, analysis = simulate(
            data_root=root, repo_root=source_root, experiment_id=experiment_id,
            seed=seed, observer=observer, values=experiment_settings,
            analyse=True,
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
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    report_directory = root / "simulation_reports" / experiment_id / scenario_id / f"{stamp}_{uuid4().hex[:12]}"
    report_directory.mkdir(parents=True, exist_ok=False)
    report_file = report_directory / "scenario_report.json"

    def relative(path: Path) -> str:
        return path.resolve().relative_to(root.resolve()).as_posix()

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
        "expected_analysis": scenario.expect_analysis,
        "tests": checks,
        "experiment_evaluation": evaluation,
        "runs": [
            {
                "seed": record.seed,
                "relative_run_directory": relative(record.artifacts.run_directory),
                "status": record.artifacts.status,
                "accepted_responses": record.artifacts.accepted_trials,
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
    atomic_write_json(report_file, report)
    return ScenarioResult(experiment_id, scenario_id, succeeded, report_file,
                          tuple(records), tuple(checks), evaluation)
