# Windows launchers and persistent laboratory sessions

## Supported daily workflow

Double-click **PsyCoLab.bat**. It opens a native text menu without requiring Python
or Textual. Choose **1 — Launch PsyCoLab**, **2 — Check / Repair PsyCoLab**,
**3 — Python Workspace**, or **4 — Exit**. The native host is compiled once per
launcher session using the existing Windows .NET bootstrap. Operations use the
same console; no detached application shell is created.

For first setup from Git or an environment error, choose **2**. If a supported
action is available, type **Y** to proceed or **N** to return to the menu. See
[Windows source installation recovery](SOURCE_INSTALLATION_RECOVERY.md) for
the two setup routes and the administrator cases. Successful setup returns to
the menu. Choose **1** to open the TUI. Closing the TUI returns to this menu.

Choose **3** for a normal command prompt with the verified environment's Python
first on its local PATH. Its banner identifies the interpreter and qualification
status. For example:

```bat
python "C:\Research folder\my experiment.py" "argument with spaces"
```

Type `exit` to return to the menu. Reopening the workspace reuses the same
environment. Healthy launches and workspace entry do not reinstall packages.
Script exit codes are preserved and scripts run once. The working directory is
the checkout; use explicit output locations or script-relative paths in your
code. Scripts execute with your ordinary account permissions. The launcher does
not automatically install optional packages or `user_requirements.txt`.

Existing laboratory qualification and packaged source seals remain authoritative.
When the same approved profile can be reused, option **2** prepares a separate
environment and retains the original. Offline launches of a healthy environment
need no package index. A new install still needs the dependencies.

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

## Entry-point inventory (5 November 2026)

| Entry | Current role |
| --- | --- |
| `PsyCoLab.bat` | **The only root batch file.** Launch, Check / Repair, Python Workspace and Exit; supported CLI options share these implementations. |
| `scripts/windows_startup.cmd` | Internal native-host compilation, source/managed launch and recovery bootstrap. |
| `scripts/windows_development.cmd` | Internal interpreter discovery/development setup; retained infrastructure, not a second researcher entry. |
| Python/native helpers | Existing setup, qualification, recovery, application and Python execution implementations. |

The five former root wrappers are retired by the maintainer's 5 November
consolidation decision. This supersedes the earlier plan to retain them through
another tagged release. Exact non-executable snapshots and the full
[shortcut/script migration table](../outdated_code/windows_launchers/README.md)
are retained under `outdated_code/windows_launchers/`. Old external paths will
break until retargeted; no compatibility at removed root paths is claimed.
Version-specific packaged executable shortcuts are unaffected.

### Internal helpers

| Helper | Responsibility |
| --- | --- |
| `scripts/developer_setup.py` | Existing owned `.venv-dev` setup and separate read-only `--check`; development evidence only. |
| `scripts/launcher_setup.py` | Existing exact-profile laboratory setup and read-only `--check`; retained explicit `--user-env` compatibility facility. |
| `packaging/windows/GuidedSetup.cs` | Existing guided setup, source/managed launch, qualification/recovery and native process observer; added same-environment Python mode. |
| `scripts/build_windows_candidate.py` | Maintainer package builder; not a researcher launcher. |
| `scripts/windows_display_preflight.py` | Display diagnostic process; not an installer or alternate application entry. |
| `python -m psychophysics_lab` / installed `psycolab` | Existing application entry (`__main__.py` â†’ `app.main`). |
| `python -m psychophysics_lab.ui.refresh` | Internal fresh-source checker; refresh handoff restarts interpreter deliberately. |
| `python -m simulations` | Existing explicit synthetic pipeline CLI; labelled virtual data. |

There is one recommended daily batch file, `PsyCoLab.bat`. The root
compatibility files are retired; migrate external references as described above.
The duplicated USER_env bootstrap discovery was removed from the batch layer.
The locked installer and source development setup remain distinct because their
scientific qualification contracts are different.

## Historical verification and limits (4 November 2026)

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
separate checks. The later consolidation retains the implementation through
PsyCoLab.bat while retiring only the root wrappers.
