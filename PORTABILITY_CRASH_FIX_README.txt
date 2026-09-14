PsyCoLab v0.2.1 portability + crash diagnostics patch
=====================================================

Built against Git commit:
8dda87b87328bbfd3bf566360050b68df4d99447
("gpt updated code. error in run.")

Why this patch exists
---------------------
The latest repository commit contains the data-integrity update, but the user
reported that the application disappeared/crashed at the final TUI-to-experiment
transition. No traceback or crash log is committed in the repository, so the
exact runtime exception cannot be identified responsibly from Git alone.

This patch therefore does two things without changing scientific behaviour:

1. Adds a process-wide diagnostic boundary so a TUI/launch failure prints its
   traceback, returns exit code 1 (so run_psycolab.bat pauses), and writes a local
   .psycolab_logs/psycolab_error_*.log file.
2. Tightens portability so shared code/configuration does not depend on the
   author's Windows home directory or checkout location.

Portability changes
-------------------
- psycolab_data_config.json no longer persists an absolute data-root path.
  It stores data_root as "." and reusable SetupRequest state stores data_root=None.
- Canonical manifest metadata no longer stores absolute repository/data/run paths
  or a full Python executable path. Run-owned file references remain relative.
- .psycolab_local.json remains the machine-local way to remember the last data
  directory and is ignored by Git.
- .vscode/ and .psycolab_logs/ are now ignored by Git.
- cleanup_git_tracking.py now untracks .vscode as well as .venv/cache artefacts
  without deleting local files.
- scripts/portability_check.py checks the Git index and source/config files for
  tracked local artefacts and common hard-coded user-home paths.
- tests cover portable workspace state and crash-report creation.

What this patch does NOT change
-------------------------------
- No staircase mathematics.
- No CSF shader mathematics.
- No stimulus geometry or the deferred 31.5 scaling.
- No experiment timings/defaults.
- No canonical trial semantics.

How to apply
------------
1. Commit/back up current local work.
2. Extract this ZIP into the ROOT of Psychophysics_Collaborative_Lab.
3. Allow matching files to be replaced.
4. Run:

   .venv\Scripts\python.exe scripts\cleanup_git_tracking.py

   This only changes Git tracking; it does NOT delete your local .venv or VS Code
   settings from disk.

5. Inspect `git status`, then commit the untracking when satisfied.
6. Run:

   .venv\Scripts\python.exe scripts\portability_check.py

7. Launch normally with run_psycolab.bat.

If it fails again
-----------------
The launcher should now pause instead of appearing to vanish. Copy the traceback
or send the newest file from either:

  <selected data folder>\.psycolab_logs\

or, if the data folder was not yet available:

  <PsyCoLab repository>\.psycolab_logs\

That log will identify the exact remaining runtime exception so it can be fixed
without guessing.
