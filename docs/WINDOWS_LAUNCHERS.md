# Windows launchers and persistent laboratory sessions

## Supported daily workflow

Double-click **Run_PsyCoLab.bat**. In a fresh Git checkout with neither `.venv`
nor `.venv-dev`, it calls the existing source development setup. Install 64-bit
Python 3.11 if requested (`py install 3.11` with the Python install manager), then
reopen it. Downloads happen at first setup, not on matching repeated launches.
No administrator privileges or global PATH edits are introduced.

**PsyCoLab_Python.bat** opens an interactive Python prompt in the same verified
environment. From a terminal, pass a quoted script path and arguments:

```bat
PsyCoLab_Python.bat "C:\Research folder\my experiment.py" "argument with spaces"
```

Script exit codes are preserved and scripts run once. The working directory is
the checkout; use explicit output locations or script-relative paths in your
code. Scripts execute with your ordinary account permissions. The launcher does
not automatically install optional packages or `user_requirements.txt`.

Existing laboratory `.venv` checks, qualification records and packaged source
seals remain authoritative. A broken or interrupted existing environment is
preserved, never replaced by the source setup. Use diagnostics and the retained
explicit setup path. Offline launches of a healthy environment need no package
index; a new install still needs the dependencies. Recovery reports distinguish
missing Python, setup failure and invalid installation evidence.

## Why acquisition used to close the application

`app._main` deliberately ended with `return` immediately after `run_request` and
its summary. This was a one-run application lifecycle, rather than evidence of
a failed installation. The existing simulation and calibration branches already
looped back to the TUI. Acquisition now joins that loop only after the runner
has finished recording, snapshots, manifest finalisation and cleanup.

The result page provides the exact saved folder, **Inspect saved results**,
**Configure another run of this experiment**, and **Return to experiment
selection**. Workspace, participant, display selection, unsaved experiment and
stimulus drafts, parameter-file identities and original loaded-source hashes
stay in memory. Repeat configuration goes through normal Review and preflight;
it never replays an old human override. A repeat allocates a fresh run folder.
Saved edits to Python still require Refresh/F5 in a clean interpreter.

Only `completed` is labelled successful. Participant abort, safety-ceiling
termination, returned/incomplete states and recording errors remain distinct.
Exceptions and Ctrl+C during acquisition preserve the exact partial run path
and diagnostic before returning. Ctrl+C outside acquisition retains application
exit code 130. A failure while returning to the TUI still reaches the existing
top-level crash handler. Hard process termination can leave a configuring or
incomplete manifest; it cannot manufacture successful completion.

Timed presentation remains outside Textual's active event loop. No frame timing,
staircase rule, contrast calculation, calibration gate or data schema changes
are part of this repair. RunContext already closes its presentation in finalisation
even when recording fails. The application coordinator now joins outstanding asynchronous beep threads
after recording finalisation, before a new run can begin. No delay is inserted into a
timed trial. Native window/context closure releases keyboard and display state;
physical display/input/audio behaviour still needs apparatus acceptance.

## Why two terminals appeared

The batch starts the existing compiled `.NET` GUI startup host (`/target:winexe`).
That host previously launched console Python without attaching to the batch's
console. Windows allocated Python a second console while the first waited empty.
The host now attaches to its parent console before application or researcher
Python launch. A direct GUI shortcut with no console still lets Python allocate
the single required console. The observer handles console Ctrl+C/Ctrl+Break
without inheriting an ignore flag into Python. Experiment display windows remain
independent. Nonzero application exits retain existing incident diagnostics;
arbitrary researcher scripts retain their own exit semantics.

## Entry-point inventory

| Entry | Responsibility / disposition |
| --- | --- |
| `Run_PsyCoLab.bat` (formerly lowercase name) | Supported application entry; delegates to shared native startup. |
| `PsyCoLab_Python.bat` | Supported Python prompt / external script entry; same verified environment. |
| `setup_psycolab_dev.bat` | Retained explicit source setup/retry compatibility wrapper. Do not remove before independent clean-Windows acceptance. |
| `run_user_env.bat` | Retained compatibility name; delegates to `PsyCoLab_Python.bat`. Existing USER_env files are preserved. |
| `psycolab_recovery.bat` | Retained explicit recovery/diagnostics entry; no acquisition retry. |
| `scripts/windows_startup.cmd` | Internal shared native-host compilation, first-source-setup gate, temporary ownership and exit propagation. |
| `scripts/windows_development.cmd` | Internal shared interpreter discovery and invocation of existing source setup. Explicit interpreter, own development Python, registered 3.11, then compatible PATH Python. |
| `scripts/developer_setup.py` | Existing owned `.venv-dev` setup and separate read-only `--check`; development evidence only. |
| `scripts/launcher_setup.py` | Existing exact-profile laboratory setup and read-only `--check`; retained explicit `--user-env` compatibility facility. |
| `packaging/windows/GuidedSetup.cs` | Existing guided setup, source/managed launch, qualification/recovery and native process observer; added same-environment Python mode. |
| `scripts/build_windows_candidate.py` | Maintainer package builder; not a researcher launcher. |
| `scripts/windows_display_preflight.py` | Display diagnostic process; not an installer or alternate application entry. |
| `python -m psychophysics_lab` / installed `psycolab` | Existing application entry (`__main__.py` â†’ `app.main`). |
| `python -m psychophysics_lab.ui.refresh` | Internal fresh-source checker; refresh handoff restarts interpreter deliberately. |
| `python -m simulations` | Existing explicit synthetic pipeline CLI; labelled virtual data. |

There are two recommended daily batch files. Compatibility files are retained
rather than claiming their removal has passed a fresh operating-system test.
The duplicated USER_env bootstrap discovery was removed from the batch layer.
The locked installer and source development setup remain distinct because their
scientific qualification contracts are different.

## Verification and limits (4 November 2026)

Baseline: `develop` at `21e103a` includes merged PR #207; `main` at `c739f81`
includes #208 and has the identical tree `8589249`. Both are protected. Work is
on a feature branch based on develop; no protected branch was edited directly.

Native Windows Python 3.11 tests exercise the actual compiled host, batch chain,
parent-console membership, scripts outside the checkout with Unicode/spaces,
script nonzero exit propagation, repeated launches, setup failure, read-only
environment checks and recovery. A fresh source environment was also installed
through Run_PsyCoLab.bat on the available Windows machine, using its already
installed Python 3.11.9. This is not a new Windows installation with no Python.

Persistent-session tests mount and tear down the real Textual UI and use the real
configure/record/finalise/validate pipeline for two runs, including repeats.
Additional official orientation/probe sequences use explicitly labelled virtual
observers. These tests establish software navigation and record integrity, not
native fullscreen photon timing, monitor calibration or human performance.
Physical two-run acceptance and an independent clean-Windows machine remain
separate checks; retain the known-working explicit setup path until those pass.
