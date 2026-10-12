# PsyCoLab — Psychophysics Collaborative Lab

PsyCoLab is a developing Python framework for configuring and running visual
psychophysics experiments. It is being refactored from a research codebase into
a reusable laboratory tool while preserving working scientific behaviour until
specific stimulus/procedure changes are deliberately reviewed.

The repository contains experiment definitions, monitor profiles, setup/launch
machinery and acquisition code. **Experimental participant data live outside the
Git repository.**

The current reference experiment is a contrast sensitivity function (CSF)
experiment. It is an example built with the framework; it is not the definition
of the framework.

## Researcher-facing development

To create a new stimulus/experiment pair without editing the framework internals:

```powershell
.venv\\Scripts\\python.exe -m psychophysics_lab --scaffold orientation_task
```

Implement the generated modules in `src/psychophysics_lab/stimuli/` and
`src/psychophysics_lab/experiments/`, then register them in
`src/psychophysics_lab/contributions.py`. The scaffold is deliberately
incomplete until you implement the actual experimental procedure.

Start with the [researcher quickstart](docs/RESEARCHER_QUICKSTART.md),
the [adaptive-methods guide](docs/ADAPTIVE_METHODS.md) and the
[headless simulation guide](docs/SIMULATION_TESTING.md).
The [simulation laboratory guide](simulations/README.md) explains how each
experiment owns a separate virtual observer and its own test scenarios.

Virtual observers can exercise real staircase, recording, run validation
and experiment-specific analysis without a display. **In the normal PsyCoLab TUI,
open the Simulate page**, select an experiment/scenario, edit the model's
declared parameters, review the configuration and select Run Virtual Experiment.
The TUI reopens with a pass/fail report after the headless run.

The equivalent command-line access remains available:

```powershell
.venv\\Scripts\\python.exe -m simulations --seed 123 --max-trials 400
.venv\\Scripts\\python.exe -m simulations --list-scenarios
.venv\\Scripts\\python.exe -m simulations --scenario csf_baseline
.venv\\Scripts\\python.exe -m simulations --scaffold-simulation orientation_task
```

Synthetic runs are saved in the **same external data repository as human
runs**, beneath reserved `synthetic_...` participant IDs, with per-participant
markers and explicit synthetic provenance. The human TUI's saved setup is not
overwritten. Virtual timestamps are reproducible but do not measure actual
presentation or response times.

## First launch on Windows

1. Clone/download the repository.
2. Install Python **3.11**.
3. Double-click `run_psycolab.bat`.
4. PsyCoLab creates/reuses `.venv`.
5. Choose an external data folder in the TUI.
6. Enter/reuse a pseudonymous participant ID.
7. Choose experiment and display profile.
8. Configure experiment-specific values.
9. Review the run.
10. Choose **Run Experiment**.
11. The Textual TUI closes before Pyglet/OpenGL launches.

Useful direct commands:

```powershell
.venv\Scripts\python.exe -m psychophysics_lab
.venv\Scripts\python.exe -m psychophysics_lab --diagnose
.venv\Scripts\python.exe scripts\portability_check.py
```

## TUI, local display profiles and diagnostics

The six navigation buttons stay at the top of every page. Configure, Review and
Run actions remain outside the scrolling forms. **Inspect** opens the real file
in VS Code with the repository folder supplied as the project context.

Use **Display → Edit / copy display profile** to create a machine-local profile,
detect/select its monitor and save a numbered revision. Shared profiles under
`configs/monitors/` remain reference specifications. The default local folder is
`../local_psychophysics_config/`, separate from source and participant data.
Display tests cover size, position, spatial gratings and temporal modulation;
their reports distinguish requested values, pixel/frame quantisation and
software timing observations from physical measurements.

See [the display and TUI guide](docs/TUI_AND_LOCAL_DISPLAYS.md) for calibration,
multiple monitors, frequency limits, configuration overrides and acceptance checks.

## Acquisition-data contract

PsyCoLab now uses a stable, human-readable acquisition hierarchy:

```text
participant
└── experiment
    └── display_profile
        └── important fixed run-level conditions
            └── date
                └── run_NNN
```

For the current CSF reference experiment:

```text
PsyCoLab_Data/
├── psycolab_data_config.json
├── runs_index.csv
└── S001/
    └── contrast_sensitivity/
        └── legacy_reference_display/
            └── max_500cdm2/
                └── background_49cdm2_unverified/
                    └── 2026-09-15/
                        ├── run_001/
                        └── run_002/
```

The `_unverified` suffix is deliberate while the legacy monitor profile lacks a
trusted encoded command-to-luminance calibration. Once a monitor profile has a
verified mapping the folder becomes, for example, `background_49cdm2`.

Dates occur only after the scientifically useful grouping levels, so a long-term
workspace remains browsable by participant/experiment/condition instead of
becoming a top-level collection of thousands of dates.

Each experiment may declare its own fixed run-level grouping folders. PsyCoLab's
core storage layer therefore does **not** hard-code CSF, staircase or luminance
assumptions.

See [`docs/DATA_LAYOUT.md`](docs/DATA_LAYOUT.md) for the storage contract and
rules for adding future experiments.

## Configurable CSF conditions and introductory staircase phase

In both **Run** (human participants) and **Simulate** (virtual observers),
the reference CSF experiment now provides a **Stimulus conditions**
section to enter the number of conditions and their ordered, comma-separated
numeric values (for example `63,126,252`). The number must match the list,
with 1–24 distinct positive values permitted. These are *legacy reference
stimulus values*, not yet verified cycles/degree. A separate **Adaptive
algorithm** section controls independent staircases per condition, the normal
n-down/n-up rule and step sizes, and an optional initial 1-down phase.

By default the first **up to five accepted responses per staircase** use
1-down for correct choices. The first incorrect answer, or reaching the
configured response limit, ends this phase separately for that staircase.
The incorrect answer is handled by the specified n-up rule; normal n-down/n-up
logic governs later answers. Set the early 1-down limit to `0` to disable
this feature. The experiment-wide `max_trials` ceiling is shared across
every condition and staircase. Everything is saved in the same run folder
for later reproducible analysis.

## One run = one self-contained scientific record

A run folder contains:

```text
run_001/
├── manifest.json
├── experiment_config.json
├── monitor_profile.json
├── runtime_display.json
├── resolved_experiment.json
├── adaptive_session.json
├── trials.tsv
├── trial_context.json
├── trials_readable.txt
├── scenario_report.json            # virtual observers only
├── analysis/                        # derived images/tables, not raw acquisition
│   ├── staircases.png               # correct/incorrect responses and reversals
│   ├── staircase_preview.json
│   ├── threshold_vs_condition.png   # only if reversals permit
│   └── thresholds/<timestamp>/      # independent reanalysis versions
├── trial_data_dictionary.tsv
├── legacy_response.txt
└── state/
    ├── experiment_defined.json
    ├── conditions.runtime.json
    ├── conditions.initial.json
    ├── conditions.final.json
    ├── parameters.runtime.json
    ├── parameters.initial.json
    ├── parameters.final.json
    ├── user_experiment_config.json
    ├── user_config.initial.json
    └── user_config.final.json
```

`run_001`, `run_002`, ... are human navigation labels. `manifest.json` also
stores a globally unique `run_uuid`.

`trials.tsv` is the canonical append-only response record. It distinguishes the
stimulus **actually presented** from the post-response staircase state intended
for the next presentation. `trial_context.json` links all rows in that run to the
run UUID, exact profile revision/hash, calibration status and runtime snapshots.
The canonical TSV columns and existing run hierarchy are unchanged.

`trials_readable.txt` is generated from the canonical TSV at run finalisation as
a fixed-width human-readable view. Each column is padded to the longest value in
that column, making headers and values easy to follow. It is derived rather than
canonical and can always be regenerated from `trials.tsv`.

`trial_data_dictionary.tsv` is saved beside it in every run and defines every
trial column, its logical type, units/encoding and meaning, including
experiment-specific response codes. The repository-wide explanation is in
`docs/TRIAL_DATA_DICTIONARY.md`.

The historical six-column file is retained as `legacy_response.txt` for
backwards compatibility; its historical semantics are not silently redefined.

## Workspace convenience files

`psycolab_data_config.json` remembers the last participant, experiment, display
profile and parameter values so the next launch can pre-fill the TUI. Reusing
those settings creates a **new** run; it is not partial-staircase resumption.

`runs_index.csv` contains one human-readable row per acquisition with participant,
experiment, display, condition path, date, run number, status, accepted-trial
count and relative path. It is an index only: each run folder remains the
authoritative scientific record.

## What belongs in folder names?

Folder names are for fixed, scientifically useful run-level grouping variables.

Good examples:

```text
max_500cdm2/
background_49cdm2/
```

Things that should remain in config/trial files instead:

```text
DW2_UP1
step_down_0.19
10_reversals
250ms
2cpd
4cpd
```

Adaptive parameters are implementation/procedure details rather than universal
filesystem concepts, and trial-varying values must never generate folders.

## Saved parameters and provenance

`manifest.json` records the run identity/status, Git/source fingerprints,
software versions, monitor/calibration information and relative file ownership.

`experiment_config.json` stores the requested and normalised experiment values
without machine-specific data-root paths.

`resolved_experiment.json` records concrete runtime timing, stimulus, response
mapping, adaptive parameters and resolved geometry.

`runtime_display.json` records the actual fullscreen dimensions obtained by
Pyglet plus physical dimensions, viewing distance, field of view and calculated
pixels/degree.

`adaptive_session.json` records staircase completion/reversal state using
run-relative paths.

The saved maximum accepted-response value is kept consistent across the
experiment and staircase parameter records.

## Display profiles and luminance calibration

Profiles live under:

```text
configs/monitors/
```

The current reference profile preserves the legacy geometry:

- width: 610 mm;
- height: 350 mm;
- refresh rate: 60 Hz;
- viewing distance: 1.0 m.

The existing reference profile is `manual_unverified`: PsyCoLab does not invent
a correspondence between the old unequal luminance and digital-command lists.
When a measured calibration table is added and marked verified, PsyCoLab can
enforce the physical/digital pairing.

## Architecture

```text
src/psychophysics_lab/
├── adaptive/
├── config/
├── core/
├── data/
├── experiments/
├── stimuli/
└── ui/
```

Working legacy experiment/rendering code remains temporarily under:

```text
Events/
Experiments/
Functions/
Interface/
libC.py
```

This migration is intentionally incremental.

See [the current architecture](docs/ARCHITECTURE.md) for package responsibilities
and provenance coverage, and [CONTRIBUTING.md](CONTRIBUTING.md) for development rules.

Validate a finalized run without modifying it:

```text
python scripts/validate_run.py <run_directory>
```

The validator reports PASS/FAIL and individual consistency checks; it does not
validate physical stimulus rendering, timing or calibration.

## Experiment termination and Escape

PsyCoLab distinguishes scientific completion from an intentional manual abort
and from software failure. The current adaptive experiment uses four principal
final states:

- `completed` — every active staircase reached its configured termination criterion;
- `max_trials_reached` — the accepted-response safety ceiling was reached first;
- `aborted_by_user` — the researcher deliberately pressed Escape;
- `error` — an unexpected failure occurred.

After an accepted response, `trials.tsv` is appended and flushed immediately.
If that response completes the final unfinished staircase, PsyCoLab stops
accepting further responses, clears the remaining presentation queue, closes the
Pyglet experiment window automatically, finalises all run metadata and returns
to the terminal. No extra Escape press is required.

Pressing Escape before scientific completion is a controlled termination rather
than a crash. PsyCoLab first records `aborted_by_user`, then closes the experiment
window and finalises the run. A partially presented stimulus for which no response
was accepted does not create a fabricated trial row.

The Windows launcher keeps the terminal open after both normal and error exits so
the researcher can read the final status and saved-data location.

See `docs/EXPERIMENT_LIFECYCLE.md` for the detailed lifecycle contract.

## Acquisition versus analysis

PsyCoLab canonical acquisition files (`trials.tsv`, state snapshots,
manifest and configuration) remain **immutable**. Each human or simulated run
now also owns a clearly separated `analysis/` subfolder containing automatic
per-condition staircase plots and exploratory threshold summaries, without
editing the acquisition records. Reanalysing by a different reversal convention
creates a versioned analysis under that same run. Publication-ready analyses
may still be exported to a separate analysis/publication repository; the
per-run figures are for inspection and quality control.

## Portability and errors

The shared repository does not require a particular user name, home directory,
drive letter or checkout location. `.psycolab_local.json` may remember the
selected data folder on one machine but is Git-ignored and is not scientific
metadata.

Canonical dataset paths are relative.

If the setup TUI or experiment launch raises a normal Python error, PsyCoLab
prints the traceback and writes a best-effort `psycolab_error_*.log`; the Windows
launcher uses a non-zero exit code to remain open/pause rather than silently
disappearing.

## Current scientific limitations

The following remain deliberately deferred:

- CSF shader contrast mathematics have not been reinterpreted;
- the legacy `31.5` spatial scaling has not been redefined as measured PPD;
- the legacy reference luminance mapping is not yet verified;
- the Pyglet/OpenGL renderer has not been modernised;
- physical rendering/timing still requires validation on the intended display;
- true resume-from-partial-staircase state is not implemented.

## Development tests

When development dependencies are available:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

Real stimulus rendering/timing requires additional validation on the laboratory
display.
