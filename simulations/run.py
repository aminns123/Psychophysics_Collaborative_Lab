"""Public simulation entry point: real configure -> event adapter -> canonical data -> analysis."""
from dataclasses import asdict, is_dataclass
from pathlib import Path
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.core.synthetic import SimulationRun, simulation_workspace
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.paths import find_repo_root, default_data_root
from psychophysics_lab.data.workspace import preferred_data_root
from .registry import get_simulation


def simulate(*, workspace=None, data_root=None, seed=123, experiment_id="contrast_sensitivity", observer=None,
             values=None, repo_root=None, analyse=True, monitor_profile_id=None, monitor_profile_hash=None, stimulus_snapshots=None):
    if type(seed) is not int or seed < 0:
        raise ValueError("Seed must be a nonnegative integer.")
    root = (repo_root or find_repo_root()).resolve()
    spec = get_simulation(experiment_id)
    experiment = get_experiment(experiment_id)
    observer = observer or spec.observer_factory()
    selected_values = experiment.normalise_values(experiment.normalise_input_keys(spec.defaults) | experiment.normalise_input_keys(values or {}))
    if is_dataclass(observer) and not isinstance(observer, type):
        observer_parameters = asdict(observer)
    elif callable(getattr(observer, "simulation_parameters", None)):
        observer_parameters = dict(observer.simulation_parameters())
    else:
        raise TypeError("Observer must be a dataclass or expose simulation_parameters() for provenance.")
    metadata = {"seed": seed, "rng": "python.random.Random MT19937",
        "observer_model": type(observer).__name__, "observer_parameters": observer_parameters,
        "physical_display_used": False, "human_participant": False,
        "validation_kind":"psychometric_observer" if callable(getattr(observer,"probability_correct",None)) else "pipeline_smoke_test",
        "note": "Synthetic pipeline test; model ground truth is not necessarily the adaptive estimator's target."}
    if workspace is not None and data_root is not None:
        raise ValueError("Specify data_root only; workspace is a retained compatibility alias.")
    selected_root = data_root if data_root is not None else workspace
    if selected_root is None:
        selected_root = preferred_data_root(root, default_data_root(root))
    test_root = simulation_workspace(Path(selected_root), root)
    request = SetupRequest(f"synthetic_{seed}", "new", experiment_id, monitor_profile_id or spec.monitor_profile_id, selected_values, monitor_profile_hash=monitor_profile_hash, stimulus_snapshots=stimulus_snapshots or {})
    algorithm_id = experiment.adaptive.algorithm_id if experiment.adaptive else None
    simulation = SimulationRun(test_root, metadata, spec.runtime_factory(observer, seed, algorithm_id), response_probability=getattr(observer,"probability_correct",None))
    artifacts = run_request(request, repo_root=root, data_root=test_root, simulation=simulation)
    # Both human and synthetic runs already get a per-condition staircase
    # figure during shared run finalisation; avoid generating it twice here.
    analysis = None
    if analyse and spec.analysis_factory is not None:
        try:
            analysis = spec.analysis_factory(
                data_root=test_root, run_directory=artifacts.run_directory, create_plot=True
            )
        except ValueError as exc:
            if not any(message in str(exc) for message in spec.unavailable_analysis_messages):
                raise
            from psychophysics_lab.data.session import atomic_write_json
            missing_analysis = artifacts.run_directory / "analysis" / "threshold_unavailable.json"
            missing_analysis.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(missing_analysis, {"data_kind": "synthetic", "reason": str(exc)})
    return artifacts, analysis
