PsyCoLab data-integrity update
==============================

Built against repository commit:
136d4fdd4825e6f759a72a045da8897187ce2b4c

How to apply
------------
1. Close PsyCoLab / VS Code processes using these files.
2. Make a backup or commit your current work.
3. Extract this ZIP directly over the root of Psychophysics_Collaborative_Lab.
   Allow Windows to replace files with the same names.
4. Re-run run_psycolab.bat. The editable install should pick up the source changes;
   if the launcher decides dependencies/configuration changed it can refresh them.
5. Run the test suite if desired:
      .venv\Scripts\python.exe -m pytest
6. Run the one-time Git-index cleanup:
      .venv\Scripts\python.exe scripts\cleanup_git_tracking.py
   Then inspect `git status` before committing.

Main changes
------------
- Data folder is selectable in the TUI and must be outside the Git repository.
- The selected folder contains psycolab_data_config.json remembering the most
  recent participant, experiment, monitor and experiment parameters.
- Every run gets a unique, self-contained run folder.
- trials.tsv is append-only and explicitly distinguishes the stimulus presented
  on a trial from the post-response value intended for the next presentation.
- Legacy response output is retained unchanged for compatibility.
- manifest.json records software/Git provenance, source/output SHA-256 fingerprints, and run status.
- runtime_display.json records actual Pyglet resolution and derived display
  geometry.
- resolved_experiment.json records concrete timing, stimulus, response and adaptive
  values used for the run, including retained legacy hard-coded constants.
- Monitor profiles can carry a measured luminance calibration table; the current
  legacy profile is deliberately marked manual/unverified rather than guessing
  the mapping.
- .psycolab_local.json remembers the last selected data-folder path locally and
  is ignored by Git.

Important
---------
This update does NOT reinterpret the legacy 31.5 spatial scaling and does NOT
change the CSF shader mathematics. Those remain deferred scientific/stimulus
review items.

Recommended first validation
----------------------------
Before collecting scientific participant data, run one short pilot/test session
(e.g. participant ID `pilot_data_integrity`) and inspect the resulting run folder.
Confirm that `trials.tsv`, `manifest.json`, `resolved_experiment.json`,
`runtime_display.json`, the legacy response, and final state snapshots are all
present and sensible for the laboratory display.
