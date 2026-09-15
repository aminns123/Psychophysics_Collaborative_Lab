# PsyCoLab acquisition-data layout contract

**Layout schema:** `1`

This document defines how PsyCoLab stores newly acquired experimental data.
Changing this hierarchy later should be treated as an explicit data-format
migration rather than an informal folder rename.

## Design rule

The acquisition tree should tell a researcher what they are looking at before
they open a JSON file:

```text
participant
    ↓
experiment
    ↓
display profile
    ↓
important fixed run-level scientific conditions
    ↓
date
    ↓
run
```

Dates are deliberately late in the hierarchy. A long-running laboratory can
therefore browse by subject and scientific condition instead of facing thousands
of top-level date folders.

## Current CSF layout

With the current unverified reference-display calibration:

```text
PsyCoLab_Data/
├── psycolab_data_config.json
├── runs_index.csv
│
└── S001/
    └── contrast_sensitivity/
        └── legacy_reference_display/
            └── max_500cdm2/
                └── background_49cdm2_unverified/
                    └── 2026-09-15/
                        ├── run_001/
                        │   ├── manifest.json
                        │   ├── experiment_config.json
                        │   ├── monitor_profile.json
                        │   ├── runtime_display.json
                        │   ├── resolved_experiment.json
                        │   ├── adaptive_session.json
                        │   ├── trials.tsv
                        │   ├── legacy_response.txt
                        │   └── state/
                        │       ├── experiment_defined.json
                        │       ├── conditions.runtime.json
                        │       ├── conditions.initial.json
                        │       ├── conditions.final.json
                        │       ├── parameters.runtime.json
                        │       ├── parameters.initial.json
                        │       ├── parameters.final.json
                        │       ├── user_experiment_config.json
                        │       ├── user_config.initial.json
                        │       └── user_config.final.json
                        │
                        └── run_002/
                            └── ...
```

When the selected display profile contains a verified luminance calibration, the
suffix is removed:

```text
background_49cdm2/
```

Until then, `_unverified` is intentional. PsyCoLab must not imply that a
manually selected physical luminance and digital command have been validated as
a pair.

## What belongs in a folder name?

A run-level value belongs in the hierarchy only when it is all of the following:

1. fixed for the whole run;
2. scientifically useful for finding/grouping the data;
3. meaningful to a human researcher;
4. not merely an implementation detail.

For the CSF reference experiment, maximum and background luminance satisfy this
rule.

The following do **not** belong in the universal hierarchy:

- `2-down/1-up`, staircase step sizes or reversal limits;
- response timeouts and trial timings;
- spatial-frequency values that vary within a CSF run;
- individual trial conditions;
- random seeds or internal IDs.

Those are recorded in `experiment_config.json`, `resolved_experiment.json`,
`adaptive_session.json` and/or `trials.tsv`.

Each future experiment can expose its own fixed grouping folders through its
`ExperimentSpec.data_path_builder`. The core storage engine therefore remains
independent of CSF.

## Human run number versus machine identity

Folders use:

```text
run_001
run_002
run_003
```

because these are pleasant to navigate.

`manifest.json` separately stores a random `run_uuid`, which is the globally
unique machine identity for that acquisition. The folder number and UUID serve
different purposes.

## Top-level files

### `psycolab_data_config.json`

Convenience state only. It remembers the latest participant, experiment,
display profile and parameter choices so a researcher can quickly start another
run. It is not the canonical scientific record.

### `runs_index.csv`

A human-readable catalogue with one row per run. It contains the participant,
experiment, display, condition path, date, run number, status, trial count and
relative path. The row is updated as the run changes from configuring to its
final status.

The self-contained run directory remains authoritative if the index is lost or
must be regenerated.

## Canonical run record

`trials.tsv` is the canonical accepted-response table and is append-only during
acquisition.

`manifest.json` is the high-level provenance record.

`experiment_config.json` records the requested and normalised experiment
configuration without machine-specific data-root paths.

`monitor_profile.json` records the selected display profile.

`runtime_display.json` records the actual Pyglet fullscreen resolution and
derived physical geometry observed at run time.

`resolved_experiment.json` records concrete runtime stimulus/timing/adaptive
parameters, including retained legacy constants.

`adaptive_session.json` records adaptive-run completion, reversals and
staircase state.

`legacy_response.txt` remains only for compatibility with historical analysis.

`state/` contains mutable legacy runtime state plus initial/final snapshots.

## Acquisition versus analysis

A run directory is an immutable acquisition record. It should not become a
dumping ground for:

```text
plots/
fits/
bootstrap/
processed/
figures/
```

Analysis and publication repositories should create their own processed/derived
layers. This follows the useful distinction in the PNAS data archive between raw
records and processed scientific outputs.

## Portability

All canonical paths stored inside PsyCoLab data are relative to the data
workspace or run directory. A copied `PsyCoLab_Data` folder should remain
interpretable on another computer without an `Alexander`, `C:\Users\...`, or any
other machine-specific path.
