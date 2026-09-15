PsyCoLab acquisition-data layout contract v1
============================================

Built against GitHub commit:
    93ad95af723dfb1da0c182cf7dbc341f5e927a3b

Purpose
-------
This update settles the human-facing acquisition folder narrative before more
experiments are added.

New hierarchy
-------------
participant / experiment / display / experiment-defined fixed conditions /
date / run_NNN

Current CSF example:

S001/
  contrast_sensitivity/
    legacy_reference_display/
      max_500cdm2/
        background_49cdm2_unverified/
          2026-09-15/
            run_001/
            run_002/

Other changes
-------------
- Adds top-level runs_index.csv with one row per run.
- Keeps psycolab_data_config.json as convenience "last setup" state.
- Stores an internal run_uuid in manifest.json while folders use readable run_NNN.
- Makes run paths in metadata portable/relative.
- Removes the absolute data-root path from experiment_config.json.
- Writes adaptive metadata as adaptive_session.json with a relative trials.tsv ref.
- Fixes saved number_trials so it agrees with the actual max accepted responses.
- Adds reversal-limit provenance to resolved_experiment.json.
- Keeps trials.tsv as the canonical append-only accepted-response record.
- Does not change shader maths, trial timing defaults, staircase maths, contrast
  definition, response mapping or legacy 31.5 spatial scaling.

Apply
-----
1. Make sure current work is committed/backed up.
2. Extract this ZIP into the ROOT of Psychophysics_Collaborative_Lab.
3. Allow matching files to be replaced.
4. Run:
       .venv\Scripts\python.exe scripts\portability_check.py
5. If pytest is available:
       .venv\Scripts\python.exe -m pytest
6. Start one test run in a NEW/EMPTY external data folder.
7. Inspect the generated path and files before using the layout for real data.

Old data
--------
Existing old folders are not moved, renamed or deleted. New acquisitions use
layout-contract v1. This avoids silently rewriting historical datasets.
