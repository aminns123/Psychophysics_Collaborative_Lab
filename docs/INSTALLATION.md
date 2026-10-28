# Installing PsyCoLab on a Windows laboratory computer

Windows 11 is the sole supported laboratory platform. Existing headless checks on other
operating systems are useful regression checks, not a promise of physical-display
or audio support there. The installation and qualification workflow below targets
Windows 11 and 64-bit Python 3.11. See the
[acceptance policy](WINDOWS_ACCEPTANCE_POLICY.md); historical cross-platform
results below remain evidence for their dated revisions, not support promises.

The [accepted development baseline](ACCEPTED_SOFTWARE_BASELINE.md) is
`5fec547ecf3f86cd6bbd202a9e463637deca07d3`, with passing Windows and Ubuntu
headless CI. This is separate from the earlier `v0.3.0` research pre-release
and does not yet certify a reproducible fresh laboratory installation.
The [Issue #82 roadmap](ISSUE82_RELEASE_ROADMAP.md) tracks the approved
installation identity, dependency, fresh-install and rollback stages. Stage 2
adds the editable identity check described below; dependency constraints and
the broader fresh-install/update acceptance remain future stages.

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
requirements, imports and editable installation identity. A valid environment
is reused; a changed
`pyproject.toml` triggers installation again. Errors leave the launcher terminal
open for inspection. No global package environment is modified.

Keep the complete checkout: runtime resources include root `configs/`,
`simulations/`, `scripts/` and current `src/psychophysics_lab/` modules.
The historical `_reference_csf/` driver and `packages.zip` are **not part
of the tracked current application**. Do not copy old renderer archives into a
new installation. The supported deployment is the launcher's editable source
installation. An isolated wheel is not a standalone PsyCoLab application;
building a wheel successfully does not verify runtime resources or a display.

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

The current Windows runtime uses installed Pyglet from the environment;
no tracked `libC.py` or bundled Pyglet archive overrides it. Earlier
archive-version and import-precedence findings referred to a **retired tree**,
not this checkout. Retain those audit records for history rather than treating
their paths as current dependencies.

New run manifests record `software.pyglet_runtime`, distinguishing the
version and source identity of the module actually loaded from installed
distribution metadata. A headless run may report `loaded: false`. This is
software provenance, not proof of graphics-buffer bit depth or physical
photon output.

The tested principal versions and local/CI environment differences are recorded
in the [baseline](ACCEPTED_SOFTWARE_BASELINE.md). Local read-only inspection
found source version `0.3.0` with installed editable metadata `0.2.2`.
Changing the dynamic source version does not change `pyproject.toml`, and an
editable install needs its metadata rebuilt when that version changes.

Both `.venv` and `USER_env` now check the imported package's resolved source
path and version against this checkout and its installed distribution metadata.
An isolated Python check also verifies the editable origin recorded in
`direct_url.json`; ordinary launch imports are checked separately so an
inherited `PYTHONPATH` cannot redirect the application unnoticed. This follows
the existing literal `__version__` declaration in the package initializer.

When dependency configuration is unchanged but identity is inconsistent, setup
refreshes only the editable project with `--no-deps --no-build-isolation`.
It does not upgrade build tools or dependencies, or install optional laboratory
requirements on this repair path. Successful validation is required before
setup records success; subsequent matching launches perform no installation.
Changed dependency configuration retains the existing installation behaviour.

If the existing build tools cannot perform the refresh, or imports still point
elsewhere, setup stops without starting the application or recording success.
Inspect the reported error (including inherited Python paths), correct the
environment deliberately, and rerun the launcher. Setup does not automatically
upgrade the environment to conceal the error. Exact approved build-tool and
dependency versions belong to stage 3; the laboratory's live environment was
not reinstalled as part of the stage 2 disposable acceptance tests.

For a future release, use a reviewed **Windows x64 / CPython 3.11 constraints or
lock file** containing exact runtime and transitive versions, with hashes where
the chosen installer supports them. Keep the source commit, Python version and current dependency versions alongside validation evidence. Generate it from a fresh approved
environment and test a second clean installation before adopting it. Maintain
separate platform locks if Linux support is released. Do not freeze this
computer's editable absolute checkout path into a shared lock. No new package
manager or mandatory lock was introduced by this audit; a clean second-machine graphics/runtime check remains necessary before claiming a verified installation.

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
For the branch/fork workflow, conflict recovery and local-preset boundaries,
follow [safe updates and local work](SAFE_UPDATES_AND_LOCAL_WORK.md). A private
Python extension folder placed inside the checkout is **not** protected against
`git clean -fdx` or deleting the checkout, even if Git ignores the folder.
Superseded ZIP-overlay instructions are recoverable from Git history; use the
current launcher instead of applying old overlays.
