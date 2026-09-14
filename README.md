# PsyCoLab — Psychophysics Collaborative Lab

PsyCoLab is a developing Python framework for configuring and running visual psychophysics experiments. The project is being refactored from a research codebase into a reusable laboratory tool while preserving the behaviour of working experiments until their scientific details are deliberately reviewed.

The repository contains the code, experiment definitions, monitor profiles, setup interface and launch machinery. **Experimental data should live outside the Git repository.**

The current repository contains one reference experiment: a contrast sensitivity function (CSF) experiment. The CSF is an example built using the framework; it is not the definition of the framework.

## Current status

The current framework provides:

- repaired independent adaptive staircase state and termination;
- explicit normalised display contrast (`C_disp`) handling;
- an explicit experiment registry;
- a Textual setup interface;
- a monitor-profile boundary;
- a user-selectable external data folder;
- one self-contained directory per experimental run;
- an append-only canonical `trials.tsv` record;
- legacy response output retained for backwards compatibility;
- run-specific experiment, monitor, runtime-display and software provenance records;
- a top-level data-folder configuration remembering the last subject/experiment/settings;
- a Python 3.11 / Pyglet 1.5.27 reproducible environment definition;
- a Windows one-click launcher.

The legacy Pyglet/OpenGL renderer is intentionally retained. The current CSF shader mathematics have **not** been changed by this framework phase.

## First launch on Windows

1. Clone or download this repository.
2. Make sure Python **3.11** is installed.
3. Double-click `run_psycolab.bat`.
4. The launcher creates/reuses a local `.venv`.
5. Required packages are installed from `pyproject.toml` when needed.
6. The PsyCoLab Textual setup interface opens.
7. Choose the **data folder**. An adjacent folder outside the repository is recommended.
8. Enter or reuse a participant ID.
9. Choose an experiment and validated display profile.
10. Configure the experiment-specific parameters.
11. Review the session.
12. Choose **Run Experiment**.
13. The Textual app exits completely, then the Pyglet experiment launches.

PsyCoLab does not silently install Python itself.

### Command-line equivalents

```powershell
.venv\Scripts\python.exe -m psychophysics_lab
.venv\Scripts\python.exe -m psychophysics_lab --diagnose
.venv\Scripts\python.exe -m psychophysics_lab --list-experiments
```

## Data ownership and folder structure

The default data folder remains a sibling of the repository:

```text
<parent>/
├── Psychophysics_Collaborative_Lab/
└── local_psychophysics_data/
```

The TUI may point PsyCoLab to another folder, but it deliberately rejects folders that are inside the Git repository or that contain the repository. This keeps participant data, large result files and local laboratory state out of version control.

At the top of the selected data folder PsyCoLab writes:

```text
psycolab_data_config.json
```

This file is a convenience index containing the most recent participant, experiment, monitor profile, experiment parameter values, run status and run location. It allows the next launch to pre-fill the setup and offer **Reuse previous setup (starts a new run)**. It is not a replacement for the run-specific scientific record.

Every run owns a unique directory:

```text
local_psychophysics_data/
└── S001/
    └── contrast_sensitivity/
        └── 2026-09-14/
            └── run_20260914_145600_a1b2c3d4/
                ├── manifest.json
                ├── experiment_config.json
                ├── monitor_profile.json
                ├── runtime_display.json
                ├── resolved_experiment.json
                ├── trials.tsv
                ├── legacy_response.txt
                ├── legacy_response.session.json
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

This gives PsyCoLab a simple rule:

> **one experimental run = one self-contained run folder**

Run folders are not reused or overwritten by later sessions.

## Canonical trial data

`trials.tsv` is the new canonical response-level record. One row is appended for each accepted participant response and flushed to disk immediately.

Important fields include:

- trial index;
- staircase identity and staircase trial index;
- stimulus condition;
- target alternative;
- participant response and correctness;
- the display contrast and digital intensity **actually presented** for that response;
- the staircase step (`down`, `up`, `hold`);
- whether the response created a reversal;
- reversal count;
- the next contrast/intensity produced by the adaptive rule;
- staircase/run completion state.

The historical six-column response file is still written as `legacy_response.txt` so previous analysis can continue to work. Its historical post-update semantics are therefore preserved rather than silently redefined.

## Run manifest and reproducibility

`manifest.json` is the high-level scientific provenance record for a run. It stores:

- participant ID;
- experiment ID and complete experiment values;
- selected monitor profile and calibration status;
- the legacy setup passed to the experiment;
- run status and timestamps;
- file ownership within the run directory;
- Python, NumPy, Pyglet and Textual versions;
- operating system information;
- the Git commit when available;
- whether the Git working tree was clean at run time;
- SHA-256 fingerprints of the main runtime source files, so a dirty working tree can still be identified precisely;
- SHA-256 fingerprints of completed run-owned output files (excluding the manifest itself);
- adaptive-session metadata;
- the actual runtime display geometry reported by the experiment.

`runtime_display.json` records the fullscreen pixel dimensions actually obtained by Pyglet together with the physical dimensions, viewing distance, field of view and calculated pixels/degree used during that run.

`resolved_experiment.json` records the concrete timing, fixation, grating, response-mapping, adaptive and resolved pixel-geometry values used by the reference experiment, including values that are still hard-coded in the legacy implementation. This makes those parameters visible in the dataset rather than requiring later source-code archaeology.

## Participant IDs

Use pseudonymous IDs such as:

```text
S001
subject_1
pilot-A
```

Avoid personally identifying information in participant folder names.

## Reusing the previous setup

The selected data folder remembers its last setup in `psycolab_data_config.json`.

When PsyCoLab is opened again on the same machine:

- the last data folder is restored from the local, Git-ignored `.psycolab_local.json` pointer;
- the previous participant, experiment and monitor are preselected when available;
- choosing **Reuse previous setup** loads the previous experiment parameter values;
- a completely new run directory is still created.

This is **not** resume-from-partial-staircase functionality. A reused setup always starts a new adaptive run.

## Display profiles and luminance calibration

Display profiles live in:

```text
configs/monitors/
```

The initial profile reproduces the geometry currently assumed by the reference CSF:

- width: 610 mm;
- height: 350 mm;
- refresh: 60 Hz;
- viewing distance: 1.0 m.

Monitor profiles can now also contain an explicit `luminance_calibration` table mapping normalised digital screen intensity to measured luminance in cd/m². When such a table is present, the TUI validates that the physical luminance and digital command form a calibrated pair.

The current legacy reference profile deliberately contains **no invented calibration mapping** and is marked `manual_unverified`. PsyCoLab therefore records both selected values and surfaces a warning rather than pretending that the existing unequal legacy choice lists form a verified calibration table. Add measured calibration points only from the actual laboratory calibration.

## Architecture

```text
src/psychophysics_lab/
├── adaptive/        future public adaptive-method boundary
├── config/          session/display configuration models
├── core/            experiment orchestration bridge
├── data/            workspace, trial recording and participant helpers
├── experiments/     explicit experiment specifications/registry
├── stimuli/         future public stimulus boundary
└── ui/              Textual setup interface
```

Working legacy implementation remains temporarily in:

```text
Events/
Experiments/
Functions/
Interface/
libC.py
```

The migration is incremental: stable data/configuration boundaries are added before the graphics layer is rewritten.

## Adaptive methods

The staircase algorithm is parameterised rather than defined globally by a particular paper. `n_down`, `n_up`, step sizes, reversal termination and the maximum response ceiling are experiment/session configuration.

The current reference defaults remain:

- 2-down / 1-up;
- up-step 0.35 legacy log units;
- down-step `0.5488 × 0.35`;
- 10 reversals;
- 30 accepted responses as the safety ceiling.

Changing these through the setup interface is an explicit session choice.

## Known limitations / deliberately deferred work

- The CSF shader contrast expression is preserved and still requires a separate scientific/rendering review.
- The legacy `31.5` spatial scaling has not been reinterpreted as measured pixels/degree.
- The current luminance command/luminance table must be populated from real measurements before a profile can claim verified photometric pairing.
- Additional monitor profiles must be validated before the current CSF can use them.
- `packages.zip` is retained until its legacy role has been fully audited.
- The Pyglet/OpenGL implementation has not been modernised.
- Physical rendering and display timing still require validation on the intended laboratory display.
- True resume-from-partial-staircase state is not implemented.

## One-time Git cleanup

The commit used to build this update already contains a tracked `.venv`. `.gitignore` prevents future additions but cannot untrack files already committed.

After extracting this update, run once from the repository:

```powershell
.venv\Scripts\python.exe scripts\cleanup_git_tracking.py
```

or, if the virtual environment is not available:

```powershell
python scripts\cleanup_git_tracking.py
```

The script removes `.venv` and Python cache files from the **Git index only**. It does not delete the local virtual environment. Review the result with `git status`, then commit the removals when satisfied.

## Development tests

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

Unit tests are appropriate for configuration, registry, data handling and adaptive algorithms. Real stimulus rendering/timing must additionally be validated on the intended laboratory display.
