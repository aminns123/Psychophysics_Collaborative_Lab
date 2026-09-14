PsyCoLab public-v1 continuation overlay
======================================

Basis
-----
This overlay was prepared against GitHub branch:

    refactor/public-v1

at commit:

    df705ae529f9c4c4e2d5276ed56713276068e01d

Repository:

    aminns123/Psychophysics_Collaborative_Lab

It continues the work after Codex reached its usage limit.

What this overlay changes
-------------------------
- Adds the src/psychophysics_lab package boundary.
- Uses psychophysics_lab as the Python import package.
- Uses psycolab as the command.
- Adds an explicit experiment registry.
- Adds a general Textual setup TUI.
- Adds a monitor-profile boundary with the current legacy reference display.
- Adds per-run config/parameter snapshots around the legacy runtime files.
- Adds pyproject.toml.
- Adds run_psycolab.bat and scripts/launcher_setup.py.
- Adds a practical README.
- Adds .gitignore without changing/deleting .vscode/settings.json.
- Adds public-v1 tests for registry/config/profile/entrypoint behaviour.
- Replaces Interface/config.py so adaptive/timing parameters supplied by the
  experiment configuration are honoured while preserving all old defaults.

What it deliberately does NOT change
------------------------------------
- CSF shader rendering mathematics.
- Existing Pyglet/OpenGL renderer.
- The legacy 31.5 spatial scaling.
- packages.zip.
- Existing thesis experiments/stimuli beyond the current CSF.
- Existing historical data.
- True partial-session resume semantics.
- libC.py (Codex identified an implicit pyglet-name dependency, but this overlay
  avoids replacing the large legacy engine solely for that import cleanup).

How to apply
------------
1. Make sure your current local work is committed or backed up.
2. Close the running experiment.
3. Extract the CONTENTS of this ZIP into the ROOT of
   Psychophysics_Collaborative_Lab and allow matching files to be replaced.
4. Reopen the repository.
5. Run:

       git status

6. Optional quick tests in your existing psychophysics Python 3.11 environment:

       python -m pytest tests/test_psycolab_registry.py tests/test_psycolab_config.py tests/test_psycolab_monitor_profiles.py tests/test_psycolab_entrypoint.py

7. Then double-click:

       run_psycolab.bat

Important
---------
The current CSF is only marked compatible with the legacy reference display.
That is intentional: adding a JSON monitor profile should not silently imply
that the legacy renderer has been physically validated for a new lab display.

If Codex created uncommitted files after the GitHub commit above, compare them
with this overlay before deleting anything. This overlay does not include
commands that remove files from Git.
