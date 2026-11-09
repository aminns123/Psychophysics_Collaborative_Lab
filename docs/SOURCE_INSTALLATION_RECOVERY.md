# Windows source installation recovery

Use **2 — Check / Repair PsyCoLab** to diagnose a source installation. The
launcher explains what it found and offers a **Y/N** choice when it can safely
prepare a compatible environment.

## What to do

1. Close PsyCoLab and researcher Python scripts using this checkout.
2. Update to a reviewed PsyCoLab version containing this recovery feature using
   your normal update process. An older recovery batch cannot supply this fix.
   Recovery never downloads source updates, switches branches, or runs Git pull.
3. Double-click **PsyCoLab.bat** and choose **2 — Check / Repair PsyCoLab**.
4. Read the explanation. If a repair is offered, type **Y** to proceed or **N**
   to return to the menu.
5. Allow setup to finish. Progress appears in the existing console. After checks
   pass, you return to the menu. Choose **1 — Launch PsyCoLab** to open the TUI.

## Which environment is prepared?

- **Existing qualified source installation.** If the requirements, files or
  source location changed, recovery can prepare a separate environment when the
  existing approved profile still matches and its interpreter is available.
  The original `.venv` stays in place. Launch and Python Workspace use the
  verified replacement when the original fails its checks. If you return to a
  source version that matches the original, it can pass its own checks again.
- **Ordinary Git checkout.** Fresh setup and supported older records use the
  pinned development setup. A completed development environment that fails
  verification is preserved before a replacement is installed. A handled
  setup failure returns the previous development environment to its original
  location. Development setup does not grant laboratory qualification.
- **Administrator setup.** A fresh source archive, managed installation, changed
  qualified profile, unrecognised setup record or unavailable approved
  interpreter needs the [reviewed installation route](WINDOWS_ENVIRONMENT.md).

For development setup, the launcher looks for an installed 64-bit CPython 3.11
in recorded interpreter locations, Windows registrations and common launcher
locations. If none is available, use the
[official Windows installer](https://www.python.org/downloads/windows/) or ask
your administrator. An administrator can supply an explicit executable path
with `PSYCOLAB_BOOTSTRAP_PYTHON`. Recovery never installs global packages or
edits the global PATH.

## If setup fails or is interrupted

Close any remaining setup process and choose **2** again. The qualified route
keeps incomplete attempts separate and uses a fresh location on retry. The
development route can resume an owned incomplete attempt and keeps its recorded
legacy backup. Setup verifies dependencies and checks application startup
before reporting success.

The report is **.psycolab-recovery/qualified-repair.log** or
**.psycolab-recovery/repair.log** inside the checkout. Review it for local paths
before sharing it with your maintainer. If setup cannot write to the folder or
obtain packages, ask the folder owner or administrator about access. A
maintainer can provide an offline wheel folder through `PSYCOLAB_WHEELHOUSE`.
The launcher still checks package hashes.

## Restore the original environment

For a legacy source backup, open **PsyCoLab.bat → 2 — Check / Repair** and
type **S** when offered. Confirm with **Y**. Administrators can also use:

```bat
PsyCoLab.bat --restore
```

Restoration puts the original environment back at `.venv`, preserving the
replacement separately. It never overwrites an existing `.venv`. It does not
launch PsyCoLab, qualify the old installation, or fix its older-record warning.
Rerunning an interrupted restoration is supported. Restoring to the original
path matters because Python environments are not generally relocatable.

For read-only checks use `PsyCoLab.bat --check`. For scripted, explicitly
approved repair, `PsyCoLab.bat --repair`
performs the same preflight, backup, setup and verification, then exits. This
flag supplies consent to the displayed repair explanation; ordinary double-click
use asks before modifying the installation. No experiment arguments are replayed.
The older `psycolab_recovery.bat` root file has been retired. Retarget old
shortcuts/scripts using the [migration table](../outdated_code/windows_launchers/README.md#migrate-existing-shortcuts-and-automation).
Unlike that old wrapper, `PsyCoLab.bat --repair` exits after verification;
choose option 1 or run `PsyCoLab.bat --launch` separately to open the TUI.

## Files and safeguards

| Location | Purpose |
| --- | --- |
| `.venv-recovery-backup-<unique-id>/` | Original environment, including unchanged historical setup record |
| `.venv-recovered-<unique-id>/` | Separate qualified environment or retained incomplete attempt |
| `.venv-dev/` | Verified replacement source environment |
| `.psycolab-recovery/state.json` | Restartable repair/restoration record tied to this source folder |
| `.psycolab-recovery/qualified.json` | Selection and record hash of the verified qualified replacement |
| `.psycolab-recovery/repair.log` | Setup and startup-check output |
| `.venv-dev-recovery-backup-<unique-id>/` | Replacement retained when restoring the original |

These specific directories are excluded from Git. The older manual backup name
`.venv-legacy-preserved-*` is also excluded. Do not delete a backup or recovery
record until you no longer need restoration. No backup is deleted automatically.

The legacy development route recognises historical source records and keeps
qualified records separate. Repair refuses managed installation markers, linked
folders, unrelated development environments and changed backup records. Both
repair and ordinary source launches hold a Windows mutex for the checkout.
Direct Python processes using it also block repair.
Recovery does not stop running processes. Windows releases the mutex after a
crash, and journal checkpoints allow safe retry after interrupted folder moves.

Shared defaults remain tracked. Per-machine calibration and researcher profiles
continue in the separate configuration folder; experiments and workspace data
continue in the selected external data folder. Ignored checkout preferences and
logs remain local. Recovery changes no scientific experiment or stimulus code.

## Validation boundaries

`tests/test_source_recovery.py` runs the actual Windows batch files, compiled
native host, pinned wheel installation, environment checks and restoration in
disposable checkouts. It mounts the real TUI headlessly through a test-only entry
point and exits without an experiment. It checks repeat launches, offline package
unavailability and retry, corrupted dependencies, missing Python, Windows write
permissions, concurrency, side-by-side qualified recovery and refusal of
managed installations or a different qualified profile.
Interruption checkpoints are deliberately constructed to reproduce the state
left between atomic steps; these are simulated interruptions on real Windows.
Missing-Python and offline cases use an unavailable explicit interpreter and an
empty offline wheel folder. They do not uninstall system Python or disconnect
the user's network. These tests do not establish physical hardware qualification.
