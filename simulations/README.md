# PsyCoLab simulation laboratory

This folder exists **only to test experiments and the scientific data pipeline
without a human participant**. It is independent of the real stimulus display.
Tests run the normal experiment configuration, adaptive-response handling,
canonical trial recorder, run validator, and experiment-specific analysis.

No single observer or estimator is assumed to work for every psychophysical
experiment. **Each experiment supplies its own virtual model and its own
scientific evaluation.**

## Folder structure

```text
simulations/
├── README.md
├── run.py                  # Shared headless launcher / provenance
├── registry.py             # Observer, runtime and optional analyser per experiment
├── scaffold.py             # Creates two non-overwriting contributor templates
├── csf.py                  # CSF observer and simulated legacy event adapter
└── scenarios/
    ├── core.py             # Minimal Scenario contract
    ├── registry.py         # Explicit named test cases
    ├── run.py              # Acquisition → validation → model evaluation → report
    └── csf.py              # CSF-only test scenarios and ground-truth comparisons

tests/
├── test_simulation_pipeline.py
└── test_simulation_scenarios.py
```

The first group belongs to the researcher building an experiment; the second
`tests/` group is automated software regression coverage. Neither writes
participant data into the Git repository.

## Run from the PsyCoLab TUI (no command line required)

Start PsyCoLab normally with `run_psycolab.bat`, then select **Simulate**
in the top navigation. Choose the experiment and its registered scenario.
The panel shows exactly the model parameters that scenario declares: for
example CSF contrast midpoint, preferred stimulus condition, tuning width,
slope and lapse rate. You can adjust the permitted experiment settings
(such as maximum accepted responses) and enter a single seed or a comma-separated
seed list.

Select **Review Simulation** to validate and inspect the effective settings,
chosen external data root, expected analysis and synthetic-data warning.
Select **Run Virtual Experiment** on the review screen to proceed.

The TUI then **closes**, executes the real experiment-specific headless
simulation/recording/analysis pipeline, and **reopens**, displaying the latest
pass/fail result and the saved report path. This avoids running a CPU-intensive
virtual experiment in Textual's event loop. The separate Data page can inspect
canonical synthetic run manifests and trial tables like other runs.

The default external data repository is shared with human acquisition, while
simulation records are assigned reserved `synthetic_...` participant IDs.
Running a simulation never changes the selected human participant's saved
setup or starts a physical display. The TUI is only the user interface for
the existing experiment/scenario registries; future experiments need no
special TUI-specific code.

## Run scenarios

From the checkout using its installed Python 3.11 environment:

```powershell
.venv\Scripts\python.exe -m simulations --list-scenarios
.venv\Scripts\python.exe -m simulations --scenario csf_baseline
.venv\Scripts\python.exe -m simulations --scenario csf_short_censored
.venv\Scripts\python.exe -m simulations --scenario csf_shifted_preference
```

Use `--experiment another_experiment` for cases attached to another registered
experiment. If necessary, supply `--data-root "C:\path\to\local_psychophysics_data"`.
Without it, PsyCoLab uses the same external data root selected by the human TUI.
A scenario prints the status of each simulated run and the resulting report
file, and returns a nonzero command exit status if a required check fails.

The original direct CSF sweep is still supported:

```powershell
.venv\Scripts\python.exe -m simulations --thresholds 0.05,0.1,0.2 --seeds 1,2,3 --preferred-condition 63 --tuning-width-octaves 2
```

**Units:** The current CSF condition values (such as 63 and 252) are legacy
internal units, not scientifically verified cycles per degree.

## Set an observer's known properties

The virtual CSF observer includes a contrast midpoint `threshold`, a preferred
stimulus condition `preferred_condition`, tuning width (octaves), slope and
lapse rate. For a custom set of parameters:

```python
from simulations.csf import CSFObserver
from simulations.run import simulate

virtual_observer = CSFObserver(
    threshold=0.08,
    preferred_condition=252.0,
    tuning_width_octaves=1.5,
    slope=3.0,
    lapse=0.02,
)
artifacts, analysis = simulate(seed=42, observer=virtual_observer, values={"max_trials": 200})
```

The virtual observer produces probabilities of correct 2AFC responses. The
adaptive staircase must respond to simulated choices; the code then records
canonical trials and derives the same estimator used for real CSF data.

The midpoint of this observer's psychometric function is **not** a guaranteed
convergence point for an arbitrary weighted staircase, so the `csf_baseline`
evaluation reports condition-by-condition estimator bias instead of demanding
an unjustified exact match.

## Add a completely different experimental paradigm

Start from non-overwriting templates:

```powershell
.venv\Scripts\python.exe -m simulations --scaffold-simulation orientation_task
```

Two **new source files** are generated:

1. `simulations/orientation_task.py` — an experiment-specific observer
   (its ground-truth properties), headless runtime adapter and `SimulationSpec`.
2. `simulations/scenarios/orientation_task.py` — independent scenarios,
   including their own `evaluate(observer, runs)` procedure.

The templates deliberately contain `NotImplementedError`. Implement the
experiment's actual trial semantics and synthetic responses, then explicitly
register the `SimulationSpec` with `register_simulation` in
`simulations/registry.py`, and add
`"simulations.scenarios.orientation_task"` to `SCENARIO_MODULES` in
`simulations/scenarios/registry.py`. They must also have a corresponding
registered actual experiment in PsyCoLab.

There is no requirement to use the CSF psychometric function, spatial frequency,
two-alternative correctness mapping, or CSF post-hoc threshold estimator.
`SimulationSpec.analysis_factory` is optional; `None` means no automatic
threshold analysis. It accepts the same keyword arguments as the CSF analysis
function if enabled: `data_root`, `run_directory` and `create_plot`.
An observer can be a dataclass, or provide `simulation_parameters()` for
auditable JSON-compatible provenance.

A scenario specifies its own random seed(s), observer parameters, experiment
values and optional analysis expectation. Its evaluator receives the **actual
results** and can implement whatever scientifically relevant checks make sense:
orientation preference, flanker modulation, temporal-order thresholds, failure
handling, or another paradigm entirely. Model predictions and recovery errors
belong in that evaluator, not in the generic runner.

For specialised validation of canonical records, give the scenario a
`validator(run_directory)` that returns `Check`-like objects with
`name`, `passed`, and `detail`. Otherwise it uses PsyCoLab's normal
read-only run validator.

## What is saved, and where?

All results use the normal **external** PsyCoLab data folder, shared with
human acquisition. Virtual participant IDs are reserved as `synthetic_123`,
`synthetic_42`, and so on. The regular run hierarchy and common
`runs_index.csv` are retained, while each run has a clearly synthetic
`manifest.json`, `SYNTHETIC_DATA.json`, `trials.tsv` and a virtual
timestamp specification.

A named scenario additionally writes a report at:

```text
local_psychophysics_data/
└── simulation_reports/
    └── contrast_sensitivity/
        └── csf_baseline/
            └── <timestamp>_<unique-id>/
                └── scenario_report.json
```

Each report links to the run directories **using relative paths**, records
which checks passed, and includes the experiment-specific model diagnostics.
Reports do not replace or mutate the canonical trial records. An invalid
human/synthetic participant-folder overlap fails explicitly.

## Three distinct validation levels

1. **Unit tests:** confirm maths, file handling, decisions and validation.
2. **Virtual experiment scenarios:** verify the integrated software pipeline
   with known synthetic observer responses and experiment-specific comparisons.
3. **Hardware acceptance:** verify the actual display resolution, viewing
   geometry, calibrated luminance and real stimulus timing on Windows.

Passing levels 1–2 cannot establish level 3. See
`docs/WINDOWS_HARDWARE_ACCEPTANCE.md` for the physical checks.
