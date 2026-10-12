"""Scaffold an experiment-specific virtual observer and its test cases.

This command writes only NEW source files, never an existing simulation,
participant data, TUI configuration or registry entry.
"""
from __future__ import annotations

import keyword
from pathlib import Path
import re


def scaffold_simulation(repo_root: Path, experiment_id: str) -> tuple[Path, Path]:
    if not isinstance(experiment_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", experiment_id) or keyword.iskeyword(experiment_id):
        raise ValueError("Use a valid lowercase Python module ID such as orientation_task.")
    root = Path(repo_root).resolve()
    models = root / "simulations"
    scenarios = models / "scenarios"
    if not models.is_dir() or not scenarios.is_dir():
        raise ValueError("This checkout has no simulations/scenarios directory.")
    paths = (models / f"{experiment_id}.py", scenarios / f"{experiment_id}.py")
    if any(path.exists() or path.is_symlink() or not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError("Simulation scaffold needs two new source files; nothing was overwritten.")

    model = f'''"""Virtual participant for {experiment_id}; replace TODOs with your own experiment model."""
from dataclasses import dataclass
from simulations.registry import SimulationSpec

@dataclass(frozen=True)
class Observer:
    # Replace with scientifically meaningful, experiment-specific ground truth.
    model_parameter: float = 1.0

def runtime(observer: Observer, seed: int, algorithm_id: str | None):
    def acquire(conditions_path, parameters_path, response_path, state_directory):
        # Use local random.Random(seed); never seed global RNG.
        # Drive the actual registered experiment's accepted-response pipeline.
        # Save canonical synthetic trials and explicit data_kind metadata.
        # Do not import Pyglet or make real participant recordings.
        raise NotImplementedError("Implement this experiment's headless event adapter.")
    return acquire

SPEC = SimulationSpec("{experiment_id}", Observer, runtime, defaults={{}},
    analysis_factory=None)  # Add an experiment-specific analyser when appropriate.
'''

    scenario = f'''"""Independent acceptance cases for the {experiment_id} experiment."""
from simulations.scenarios.core import SimulationScenario

def evaluate(observer, records):
    # Compare generated estimates with this observer's known ground truth.
    # Return JSON-compatible diagnostics (no universal threshold assumptions).
    raise NotImplementedError("Implement this experiment's scientific evaluator.")

SCENARIOS = (
    SimulationScenario(
        id="{experiment_id}_baseline",
        experiment_id="{experiment_id}",
        description="Describe what this experiment must recover or preserve.",
        observer_parameters={{"model_parameter": 1.0}},
        experiment_values={{}},
        seeds=(123,),
        expect_analysis=None,
        evaluate=evaluate,
    ),
)
'''

    created = []
    try:
        for path, text in zip(paths, (model, scenario)):
            with path.open("x", encoding="utf-8") as handle:
                created.append(path)
                handle.write(text)
    except BaseException:
        for path in created:
            path.unlink()
        raise
    return paths
