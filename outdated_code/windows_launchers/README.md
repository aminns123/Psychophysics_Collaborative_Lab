# Retired root Windows wrappers — historical source only

On 5 November 2026 the maintainer chose `PsyCoLab.bat` as the **only** root
batch file, superseding the earlier delayed-retirement plan. These five exact
wrapper snapshots come from develop `20ad8ecdf357c0768fd107e28e99fbe01cac8fb4`.
Their `.bat.txt` suffix prevents accidental execution. Do not run them here or
copy them back: their relative paths describe their former root location.
`sha256-lf.json` pins their LF-normalized original content.

This removes entry names, not setup, qualification, recovery or Python features.
The two internal `scripts/windows_*.cmd` files and Python/C# helpers remain.
Existing virtual environments, `USER_env`, backups, local requirements,
calibration, data and installation records are not removed or migrated.

## Migrate existing shortcuts and automation

**Old root targets no longer exist.** Existing desktop/taskbar shortcuts,
scheduled tasks and scripts that name them will break until retargeted. For a
normal shortcut, browse to this checkout's `PsyCoLab.bat`, set **Start in** to
the checkout folder, and choose an action from its menu. Paths containing spaces
must remain quoted. Updating source does not edit external shortcuts for you.

| Retired root target | Current replacement |
| --- | --- |
| `Run_PsyCoLab.bat` (including older lowercase spelling) | Double-click `PsyCoLab.bat`, option 1. Automation: `PsyCoLab.bat --launch [application arguments]`. |
| `PsyCoLab_Python.bat` | Option 3, or `PsyCoLab.bat --python "script path.py" [arguments]` for a single script. |
| `run_user_env.bat` | Option 3, or `PsyCoLab.bat --workspace`. The old separate `USER_env` is retained but not selected. |
| `setup_psycolab_dev.bat` | Option 2: read and approve the supported source setup/repair. Explicit approved automation: `PsyCoLab.bat --repair`. |
| `psycolab_recovery.bat` | Option 2. Explicit approved repair: `PsyCoLab.bat --repair`; restore a recorded backup: `PsyCoLab.bat --restore`. |

For a fresh source checkout, install x64 Python 3.11 if requested, then choose
option 2 again. Repair and restore CLI commands exit after their action; they
**do not launch or replay acquisition**. Launch separately with option 1 or
`--launch`. Healthy launch/workspace entry reuses its checked environment.
Use CLI options for automation requiring the operation's exit code; exiting the
interactive menu is a normal menu exit even if an earlier operation failed.

Qualified/managed installations retain their existing qualification rules.
Version-specific packaged `.exe` shortcuts still target their own executable;
the shortcut builder never targeted these wrappers and is unchanged. Only
shortcuts or scripts naming a retired root batch path require this migration.

## Reference audit

Active native messages, internal scripts, requirement-file guidance, simulations,
installation/recovery/Python Workspace guides and launcher tests now use the
consolidated entry. Tests still cover console ownership, argument/exit propagation,
first setup, repair/retry/restore, refusal/preservation, repeat launch and Workspace.

Dated scientific/repository audits, immutable hash inventories, the published
`docs/releases/v0.3.0.md`, the 18 October handbook v1 Markdown/PDF pair,
`ISSUE82_STAGE3_ENVIRONMENT_HANDOFF.md`, `CI186_WINDOWS_HANG.md`,
`REPO_SURFACE_AUDIT.md` and `TRIAL_ACTION_ARCHITECTURE.md` retain historical
filenames as evidence for their recorded revisions. Those names are not current
launch instructions. Use this table for the current checkout. No scientific
fixture, historical PDF or installation record was rewritten to hide this change.
