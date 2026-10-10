"""Hardware-free extension example; explicitly register it in a local entry point.

This is a pipeline adapter demonstration, not a scientific participant task.
It uses the current four-path adapter contract and never changes CSF settings.
"""
from pathlib import Path
from psychophysics_lab.experiments.spec import ConfigField, ExperimentSpec
from psychophysics_lab.data.session import atomic_write_json
from psychophysics_lab.data.trials import TrialLog

SPEC = ExperimentSpec(
    id="pipeline_example", display_name="Pipeline extension example",
    description="Hardware-free demonstration of a user experiment adapter.",
    legacy_module="examples.minimal_experiment", legacy_experiment_type="pipeline_example",
    configure_module="examples.minimal_experiment", configure_function="configure",
    fields=(ConfigField("example_level", "Example level", "float", default=0.5, minimum=0, maximum=1),),
    source_paths=("examples/minimal_experiment.py",))

def configure(participant_id, data_root, setup, *, run_directory):
    state = Path(run_directory) / "state"
    paths = [state / "conditions.runtime.json", state / "parameters.runtime.json"]
    for path in paths:
        atomic_write_json(path, {"example_level": setup["example_level"]})
    atomic_write_json(state / "user_experiment_config.json", {"example_level": setup["example_level"]})
    response = Path(run_directory) / "legacy_response.txt"
    response.write_text("", encoding="utf-8")
    return *map(str, paths), str(response)

def run_experiment(conditions, parameters, response, state):
    run = Path(response).parent
    atomic_write_json(run / "runtime_display.json", {"timing_status": "not_applicable", "hardware": "none"})
    atomic_write_json(run / "resolved_experiment.json", {"experiment_id": SPEC.id, "example_level": __import__('json').loads(Path(conditions).read_text())["example_level"]})
    TrialLog(run / "trials.tsv").append({"trial_index": 1, "stimulus_condition": "example", "participant_response": "synthetic", "run_status": "returned"})
