# Installing PsyCoLab on a Windows laboratory computer

Git contains the shared software. Each computer creates its own Python environment
and physical-display configuration. Scientific records live in an external data
workspace. Never copy another computer's `.venv` or treat its calibration as valid
for a different display.

## First installation

1. Clone the repository into a writable folder, keeping the complete source tree.
2. Install **64-bit Python 3.11**. Python 3.12 or later is not supported by this
   project's current compatibility requirement.
3. Double-click `run_psycolab.bat`. An internet connection and access to a package
   index are needed for the first installation; no manual scientific-package
   installation is required.
4. Choose an external data folder in the TUI and explicitly configure/calibrate
   the physical display before human acquisition.

The launcher checks `py -3.11`, then resolves `python3.11.exe` with `where` and
executes its quoted full path, then tries `python` and `python3`. Every candidate
must report major/minor **3.11**. This also supports the newer Python install
manager's versioned executable when an older `py` launcher cannot find it.
If needed, reopen the terminal after Python installation. Do not remove newer
Python installations or change PsyCoLab's version restriction as a workaround.

`scripts/launcher_setup.py` creates `.venv` with the selected interpreter. It
preserves an incompatible `.venv` as `.venv.incompatible-<timestamp>` rather than
deleting it. It installs the project in editable mode and validates package
requirements and imports. A valid environment is reused; a changed
`pyproject.toml` triggers installation again. Errors leave the launcher terminal
open for inspection. No global package environment is modified.

Keep the checkout: the current acquisition renderer still uses `Events/`,
`Experiments/`, `Functions/`, `Interface/`, `libC.py` and `packages.zip`.
Installing an isolated wheel without those checkout resources is not the
supported acquisition deployment.

## Source, local configuration and scientific records

Default siblings (the checkout folder can have any name):

```text
laboratory-folder/
  PsyCoLab/                       # Git checkout
    .venv/                       # created locally, ignored
    configs/monitors/             # shared unverified reference specifications
  local_psychophysics_config/     # local profiles, revisions, measurements, preferences
  local_psychophysics_data/       # participant/run records and synthetic runs
```

Existing `PSYCOLAB_DATA_DIR`, `PSYCOLAB_CONFIG_DIR` and local preferences remain
supported. Data cannot be inside or above the checkout; local configuration must
also be separate from source and the selected data workspace. No migration or
automatic movement of existing records is needed. `.psycolab_local.json` and
`.psycolab_logs/`, when present in the checkout, are ignored. Ignore rules for
`local_psychophysics_config/`, `local_psychophysics_data/` and `PsyCoLab_Data/`
are defensive protection against accidental copying, not recommended locations.

Shared reference profiles are not personal calibration datasets. The retained
legacy profile is explicitly `manual_unverified` and has no trusted luminance
table. Local profiles retain revisions, display bindings and physical snapshots;
material changes invalidate dependent verification declarations. The software
does not provide a cryptographic machine/monitor identity: device labels can
repeat across computers, and the historical reference-profile compatibility
path remains. Recheck binding, geometry, photometry and timing on every laboratory
computer; never copy a verified declaration as proof for another monitor.

Each run retains its profile, configuration, provenance and state snapshots.
Synthetic runs use reserved `synthetic_...` participants and explicit markers;
they share the external workspace but are not human observations. Raw luminance
sessions and diagnostic reports may also be retained in that external workspace;
active profile datasets/history live in the local configuration root. Preserve
both locations. See [data layout](DATA_LAYOUT.md) and
[calibration records](CALIBRATION_DATA_MANAGEMENT.md).

## Dependencies and reproducibility boundaries

The project requires NumPy **1.26.4**, installed Pyglet **1.5.27**, Textual
`>=1,<2` and Matplotlib `>=3.8,<4`. The launcher installs transitive dependencies
automatically. These ranges do not provide a fully locked environment: clean
installs on different dates may resolve different compatible versions, and the
launcher upgrades packaging tools during initial setup/configuration changes.

`packages.zip` is a retained legacy runtime resource, not an installer or a
backup of PsyCoLab's own source. Static inspection found 196 files (233 entries
including directories): 195 beneath `pyglet/` and one `wmi.py`; five are Python
3.7 bytecode caches. Its Pyglet source declares **1.5.19**. `libC.py` prepends the
archive to `sys.path`; thus import order can select that bundled implementation
instead of installed 1.5.27. `pip check` and ordinary imports cannot establish
which graphics implementation every legacy entry path will use. The archive is
retained byte-for-byte to avoid altering renderer behavior. Removing its caches,
replacing it, or eliminating it requires a separate dependency/provenance and
renderer-equivalence review. Header notices exist in source files; this audit
does not establish complete licensing or upstream equivalence.

For a future release, use a reviewed **Windows x64 / CPython 3.11 constraints or
lock file** containing exact runtime and transitive versions, with hashes where
the chosen installer supports them. Keep the source commit, Python version and
archive hash alongside validation evidence. Generate it from a fresh approved
environment and test a second clean installation before adopting it. Maintain
separate platform locks if Linux support is released. Do not freeze this
computer's editable absolute checkout path into a shared lock. No new package
manager or mandatory lock was introduced by this audit; archive import
precedence must also be resolved before claiming one locked graphics stack.

## Validation and updates

After the launcher has prepared the environment:

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m psychophysics_lab --list-experiments
.venv\Scripts\python.exe scripts\portability_check.py
```

For development tests only, install the declared development extra locally:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
```

`pytest` is not required for ordinary launch. Headless tests do not certify
physical stimulus appearance, photometric accuracy or photon timing. Use
[Windows hardware acceptance](WINDOWS_HARDWARE_ACCEPTANCE.md) before acquisition.

Before updating source, review `git status` and preserve local edits. After a
reviewed update, rerun the launcher; do not copy environments between computers.
Superseded ZIP-overlay instructions are recoverable from Git history; use the
current launcher instead of applying old overlays.
