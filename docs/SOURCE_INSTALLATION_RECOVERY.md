# Repair an older Windows source installation

If PsyCoLab says its setup record is **older or incomplete**, a recognised older
source installation can now be repaired without manually renaming folders or
editing records. This supports ordinary Windows Git checkouts, including paths
with spaces. Managed or laboratory-qualified installations are never converted.

## What to do

1. Close PsyCoLab and researcher Python scripts using this checkout.
2. Update to a reviewed PsyCoLab version containing this recovery feature using
   your normal update process. An older recovery batch cannot supply this fix.
   Recovery never downloads source updates, switches branches, or runs Git pull.
3. Double-click **PsyCoLab.bat** and choose **2 — Check / Repair PsyCoLab**.
4. Read the explanation, choose **R — Repair source installation**, and type
   **YES** to proceed. A fresh checkout offers **I — Install source environment**.
5. Allow setup to finish. Progress appears in the existing console. After checks
   pass, you return to the menu. Choose **1 — Launch PsyCoLab** to open the TUI.

You need installed **64-bit Python 3.11** and internet access to obtain the pinned
packages. If Python is unavailable, install it using the launcher's instructions
(for example `py install 3.11`) and run recovery again. Recovery does not install
global packages, change PATH or require elevation. Ordinary Windows accounts
need write access to their checkout; a managed access restriction may need the
folder owner or administrator to resolve it.

The replacement uses the repository's hash-pinned build and development/runtime
wheel requirements. It is a **source development environment**, not a grant of
laboratory software qualification or physical display/timing calibration. The
usual Review, calibration, recording and acquisition safeguards still apply.

## If setup fails or is interrupted

Close any remaining setup process, then double-click recovery again and select
repair. It reuses its recorded attempt and the same original backup. It can
reinstall missing or damaged pinned dependencies, including a broken target pip.
It will not adopt an unrelated environment or change a laboratory setup record.
If the application startup check failed, recovery repeats that check before
marking the attempt complete, even when the dependency checks already pass.

The report is **.psycolab-recovery/repair.log** inside the checkout. Share it with
your maintainer if retry still fails; it can contain local paths. Nothing is
uploaded automatically. An offline launch of an already healthy environment
does not need downloads. For offline repair, a maintainer can provide a complete
wheel folder using `PSYCOLAB_WHEELHOUSE`; hashes are still checked.

## Restore the original environment

Open **PsyCoLab.bat → 2 — Check / Repair** and select **S — Restore preserved environment**. Confirm the
explanation. Alternatively, from a terminal in the source folder run:

```bat
PsyCoLab.bat --restore
```

Restoration puts the original environment back at `.venv`, preserving the
replacement separately. It never overwrites an existing `.venv`. It does not
launch PsyCoLab, qualify the old installation, or fix its older-record warning.
Rerunning an interrupted restoration is supported. Restoring to the original
path matters because Python environments are not generally relocatable.

For scripted, explicitly approved repair, `PsyCoLab.bat --repair`
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
| `.venv-dev/` | Verified replacement source environment |
| `.psycolab-recovery/state.json` | Restartable repair/restoration record tied to this source folder |
| `.psycolab-recovery/repair.log` | Setup and startup-check output |
| `.venv-dev-recovery-backup-<unique-id>/` | Replacement retained when restoring the original |

These specific directories are excluded from Git. The older manual backup name
`.venv-legacy-preserved-*` is also excluded. Do not delete a backup or recovery
record until you no longer need restoration. No backup is deleted automatically.

Recovery recognises the historical source-record fields and refuses schema-2,
qualified, unknown or interrupted-qualification records. It refuses managed
installation markers, linked folders, unrelated development environments and
changed backup records. Both repair and ordinary source launches hold a Windows
mutex for the checkout; direct Python processes using it also block repair.
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
permissions, concurrency and refusal of qualified/managed installations.
Interruption checkpoints are deliberately constructed to reproduce the state
left between atomic steps; these are simulated interruptions on real Windows.
Missing-Python and offline cases use an unavailable explicit interpreter and an
empty offline wheel folder. They do not uninstall system Python or disconnect
the user's network. These tests do not establish physical hardware qualification.
