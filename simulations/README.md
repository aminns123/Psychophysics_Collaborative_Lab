# PsyCoLab simulation laboratory

This folder exists **only to test experiments and the scientific data pipeline
without a human participant**. It is independent of the real stimulus display.
Tests run the normal experiment configuration, adaptive-response handling,
canonical trial recorder, run validator, and experiment-specific analysis.

No single observer or estimator is assumed to work for every psychophysical
experiment. **Each experiment supplies its own virtual model and its own
scientific evaluation.**

## Simulation is a pipeline test, not a replacement for human psychophysics

A virtual participant is used only where a real person, graphical display or
external instrument would otherwise be required. The CSF case reuses the real
experiment setup, legacy staircase transition code, canonical `trials.tsv`,
reversal records, run finalisation, validator, indexing and post-hoc analysis.
The simulated observer replaces human response generation; virtual clock and
screen coordinates are **synthetic**, not measured reaction time or physical
luminance. Neither Pyglet fullscreen rendering nor display photon timing is
certified by a headless pipeline test.

**The Simulate page now offers ALL experiment configuration fields that the
human Run page offers**, including n-up/n-down response counts, independent
logarithmic up/down step magnitudes, reversal stopping, maximum accepted trials,
starting probe intensity, luminance settings and timing values. In Simulate,
select **Adaptive algorithm** at the top to open a dedicated editor for the
currently selected experiment's staircase rules and stopping criteria.
Change n-down/n-up counts, log-step magnitudes, reversal termination and
maximum trials. Select **Apply adaptive settings** to copy validated changes
back to the simulation setup, or **Cancel** to discard edits. You can
then inspect all effective settings in **Review Simulation** before running.
The inline Adaptive algorithm section also displays these parameters.
Other human experiment settings and simulation-only virtual-observer
settings are grouped separately. It reuses the
same experiment `ConfigField` validation and optional step-size calculator.
A qualified monitor profile may be selected as recorded metadata; no display
hardware is driven. The separate Virtual Observer section supplies
simulation-only model controls (threshold, preferred legacy condition, tuning,
slope, lapse). Changing virtual timing configuration tests its propagation and
recording, **not physical display duration**.

## One shared experiment setup, with real spatial frequency units

For new experiments use **Experiment → Configure Experiment → Review**.
The same configuration is used by either **Run human experiment** or
**Run simulation**. The simulation option then asks only for scenario, seeds
and **virtual-observer-only** parameters. The old *Scenarios* page remains an
advanced direct testing route, useful for old seeded legacy reference cases.

Before presenting human gratings, visit **Calibrate** to bind a monitor, measure
active physical width/height and eye distance, detect/confirm actual fullscreen
pixel dimensions and run a geometric check. The cpd renderer uses the resulting
physical visual-angle transformation for each fragment. Saving display
dimensions does **not** prove the luminance transfer function or frame timing
is calibrated. See [spatial calibration](../docs/SPATIAL_FREQUENCY_CALIBRATION.md).

For reference CSF, specify `condition_unit=cycles_per_degree` with conditions
such as `2,4,8` (cpd), or `degrees_per_cycle` with `0.5,0.25,0.125`
(spatial period in degrees/cycle, reciprocated into canonical cpd).
The `legacy_shader_radians` choice intentionally reproduces earlier
uncalibrated phase scalars such as `63,252`, **not** cpd. Existing standalone
scenario defaults retain this legacy mode for reproducibility.

## Choose conditions and introductory 1-down phase (human and simulation)

For the reference CSF experiment, **Run** and **Simulate** share the exact
`ExperimentSpec` settings and validation:

- **Number of stimulus conditions**: 1–24.
- **Condition values**: ordered comma-separated numeric values, e.g.
  `2,4,8` with `cycles_per_degree`. The count must match. Frequencies are
  canonical physical cycles/degree in cpd/period modes. The explicitly
  selected legacy phase-coefficient mode is *not* physical cpd.
- **Independent staircases per condition**: 1–24. For 3 conditions and 4
  staircases each, the run uses **12 independent staircase identities**.
- **Initial 1-down maximum accepted responses per staircase**: default
  5; set `0` to disable and reproduce the previous purely n-down/n-up
  algorithm from the first trial.

During that first phase, every correct accepted response steps contrast
**down** immediately. The phase ends *separately for each staircase* at
the first incorrect response or after N accepted responses (whichever
comes first). The first incorrect response is evaluated by the configured
**n-up** rule, then subsequent responses follow the usual configured
n-down/n-up rule. There is no shared countdown between conditions,
and no undocumented special update to the step sizes. The usual
`logUNIT_DW` down-step magnitude applies during this phase.

The input list is consumed by the actual CSF legacy configuration and
grating renderer in human acquisition, and by the same configuration and
virtual observer for simulation. Condition identities, adaptive settings,
first-phase counters/end reasons and per-trial actual condition values
are saved into each run's configuration, session and `trials.tsv` records.
Reversal-analysis conventions remain independent of acquisition.

Important: the `max_trials` limit still applies to **all** staircases
in a run, not to each staircase independently.

## Saved trial data and quick-look figures

The scenario report is a **software test result**, not a replacement for
the actual trial history. It is saved as `scenario_report.json` IN EACH
synthetic acquisition folder, beside `trials.tsv` and `adaptive_session.json`.
No separate top-level reports directory is created.

```text
local_psychophysics_data/
└── synthetic_123/contrast_sensitivity/.../run_NNN/
    ├── trials.tsv
    ├── trials_readable.txt
    ├── adaptive_session.json
    ├── manifest.json
    ├── experiment_config.json
    ├── resolved_experiment.json
    ├── SYNTHETIC_DATA.json
    ├── scenario_report.json
    └── analysis/
        ├── staircases.png
        ├── staircase_preview.json
        ├── threshold_vs_condition.png
        ├── latest_threshold_analysis.json
        └── thresholds/<analysis-timestamp>/
            ├── staircase_thresholds.tsv
            ├── threshold_by_condition.tsv
            └── threshold_analysis.json
```

The figures plot **presented display contrast for every accepted staircase
response**, with separately marked correct/incorrect responses and reversals.
Only conditions actually presented get a panel; no empty placeholder axes.
Each condition's legend shows its independent staircase IDs and response counts.
An exploratory threshold-contrast
vs condition curve when reversal data permit. A short/censored run may have
a staircase image but no valid THC estimate; one is never invented.

In the TUI, open **Data**, choose the synthetic run, and use **Open staircase
image** or **Open THC image**. Choose **Generate staircase + THC previews** to
derive a new set. For re-analysis select either final fraction (default 80%)
or **last N reversals per staircase**, then choose **Generate Threshold Table +
Plot**. These outputs live under that run's `analysis/` folder and never overwrite
canonical acquisition records. Quick-look THC is not a final scientific
estimate until your selected estimator and exclusion criteria are justified.

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

Start PsyCoLab normally with `run_psycolab.bat`, then choose
**Experiment → Configure Experiment → Review → Run simulation**. The same
configured run can instead be launched as a human experiment. For advanced
direct scenario tests, open the separate **Scenarios** page.
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

**Units:** The direct legacy reference commands deliberately use `63,252`
as historical shader phase coefficients. The unified workflow defaults to
physical `cycles_per_degree` and `2,8`; do not conflate the two.

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

Each run's `scenario_report.json` contains the validation checks and links
to that run's canonical trials and staircase/THC images. With multiple seeds,
each run receives the aggregate report, so no seed is left without one.

**Staircases per condition:** CSF now exposes `staircases_per_condition`
(1–24; default 1) in the Adaptive algorithm settings of both human and
simulated runs. Setting four creates eight independent staircases across
the two reference CSF conditions. The `max_trials` safety ceiling is
**shared across all staircases**; increase it appropriately if you increase
staircase count. No missing staircase responses or THC estimates are invented.

**Visible progress:** after Textual closes to run the virtual experiment,
periodic dots appear in the terminal until the pipeline returns. The TUI
reopens with a success/failure summary afterwards. Dots indicate activity,
not an estimated time remaining.

## Three distinct validation levels

1. **Unit tests:** confirm maths, file handling, decisions and validation.
2. **Virtual experiment scenarios:** verify the integrated software pipeline
   with known synthetic observer responses and experiment-specific comparisons.
3. **Hardware acceptance:** verify the actual display resolution, viewing
   geometry, calibrated luminance and real stimulus timing on Windows.

Passing levels 1–2 cannot establish level 3. See
`docs/WINDOWS_HARDWARE_ACCEPTANCE.md` for the physical checks.
