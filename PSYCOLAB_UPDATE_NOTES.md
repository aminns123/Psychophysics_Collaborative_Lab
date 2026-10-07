# PsyCoLab hub + geometry diagnostic overlay

Baseline inspected: public `aminns123/Psychophysics_Collaborative_Lab` `main`,
latest visible commit `9bf531906d1e7079af7295f35eeeeae165afc592` (2026-09-15).

## Apply

1. **Back up or commit/stash your local work first.** This ZIP was built from the
   public `main` baseline and cannot see uncommitted files on your PC.
2. Extract the ZIP directly into the root of `Psychophysics_Collaborative_Lab`,
   preserving folders and allowing these overlay files to replace files of the
   same name.
3. Do not copy any participant data into the Git checkout.
4. Run `run_psycolab.bat`. The changed `pyproject.toml` causes the launcher to
   refresh the environment and includes matplotlib so the Data page can save the
   threshold plot.
5. Before collecting real data, run the repository tests and the display/lab
   checks described below.

## Added / changed

- Hub-style Textual navigation: Run / Setup, Experiments, Stimuli, Display Check,
  Data and Help / Developer.
- Reactive experiment description and compatible-monitor selection.
- Existing-participant selector plus clearer new/reuse semantics.
- Generic review with intended acquisition path.
- Read-only experiment/stimulus source inspection.
- Reusable white-bar geometry calculations.
- Fullscreen display ruler diagnostic saved under external `diagnostics/`.
- Optional ruler measurement/error stored in the diagnostic record.
- Read-only run browser for manifest, trials and adaptive staircase state.
- Derived threshold analysis: final 80% of reversal values by default,
  staircase mean, then condition mean, with TSV/JSON/PNG outputs under external
  `analysis/`.
- Headless tests for geometry, analysis, source inspection and hub navigation.

## Scientific behaviour deliberately unchanged

This overlay does not change CSF stimulus mathematics, timings, response maps,
staircase step/update/termination rules, contrast definitions, calibration
semantics, canonical acquisition schemas or the retained `31.5` scaling.

The threshold estimator is post-hoc only. The default uses
`next_display_contrast` at reversal because this matches the current legacy
post-update reversal convention; the TUI makes the choice explicit.

## External-data rule

The existing `resolve_data_root()` protection remains authoritative: participant
and acquisition data must be outside the Git repository. New diagnostics and
analysis outputs live in the same external workspace but outside participant
run folders.

## Zero-response legacy export

The existing zero-response legacy-export edge case was inspected. Its failure is
in the old formatting path after the placeholder response row is removed. This
overlay does **not** alter that compatibility code yet, because doing so while
also replacing the hub would mix a legacy-data fix with the UI/diagnostic
change. The canonical `trials.tsv` path remains the scientific source of truth.
Treat the zero-response export fix as the next small, separately tested patch.

## Validation performed for this ZIP

- Python syntax compilation of all new/replaced Python modules.
- Headless execution of the new pure geometry and threshold calculations in the
  build environment.
- Static inspection against the current public architecture and data contracts.

The build container does not have Python 3.11/Textual installed and cannot clone
GitHub directly, so the full repository pytest suite and Textual pilot tests
could not be executed here. Run on the target repository with Python 3.11:

```text
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\portability_check.py
```

## Laboratory-only checks

Automated tests do not establish:

- actual white-bar ruler length;
- actual viewing distance;
- fullscreen monitor selection/resolution;
- photometric calibration;
- visual appearance;
- stimulus timing/refresh behaviour.

Perform the Display Geometry Check with a ruler before treating angular geometry
as physically validated.
