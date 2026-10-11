"""Public simulation entry point: real configure -> event adapter -> canonical data -> analysis."""
from dataclasses import asdict
from pathlib import Path
from psychophysics_lab.analysis.thresholds import analyse_thresholds
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.core.synthetic import SimulationRun, simulation_workspace
from psychophysics_lab.experiments.registry import get_experiment
from psychophysics_lab.paths import find_repo_root, default_data_root
from psychophysics_lab.data.workspace import preferred_data_root
from .registry import get_simulation


def simulate(*, workspace=None, data_root=None, seed=123, experiment_id="contrast_sensitivity", observer=None,
             values=None, repo_root=None, analyse=True):
    if type(seed) is not int or seed < 0:
        raise ValueError("Seed must be a nonnegative integer.")
    root = (repo_root or find_repo_root()).resolve()
    spec = get_simulation(experiment_id)
    experiment = get_experiment(experiment_id)
    observer = observer or spec.observer_factory()
    selected_values = experiment.normalise_values(dict(spec.defaults) | (values or {}))
    metadata = {"seed": seed, "rng": "python.random.Random MT19937",
        "observer_model": type(observer).__name__, "observer_parameters": asdict(observer),
        "physical_display_used": False, "human_participant": False,
        "note": "Synthetic pipeline test; observer midpoint is not a validated human threshold."}
    if workspace is not None and data_root is not None:
        raise ValueError("Specify data_root only; workspace is a retained compatibility alias.")
    selected_root = data_root if data_root is not None else workspace
    if selected_root is None:
        selected_root = preferred_data_root(root, default_data_root(root))
    test_root = simulation_workspace(Path(selected_root), root)
    request = SetupRequest(f"synthetic_{seed}", "new", experiment_id, spec.monitor_profile_id, selected_values)
    algorithm_id = experiment.adaptive.algorithm_id if experiment.adaptive else None
    simulation = SimulationRun(test_root, metadata, spec.runtime_factory(observer, seed, algorithm_id))
    artifacts = run_request(request, repo_root=root, data_root=test_root, simulation=simulation)
    analysis = None
    if analyse:
        try:
            analysis = analyse_thresholds(data_root=test_root, run_directory=artifacts.run_directory, create_plot=False)
        except ValueError as exc:
            if "No reversal observations" not in str(exc):
                raise
            from psychophysics_lab.data.session import atomic_write_json
            missing_analysis = artifacts.run_directory / "analysis" / "threshold_unavailable.json"
            missing_analysis.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(missing_analysis, {"data_kind": "synthetic", "reason": str(exc)})
    return artifacts, analysis
