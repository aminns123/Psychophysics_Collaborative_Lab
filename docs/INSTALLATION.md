# Installing PsyCoLab on a Windows laboratory computer

Windows 11 is the sole supported laboratory platform. Existing headless checks on other
operating systems are useful regression checks, not a promise of physical-display
or audio support there. The installation and qualification workflow below targets
Windows 11 and 64-bit Python 3.11. See the
[acceptance policy](WINDOWS_ACCEPTANCE_POLICY.md); historical cross-platform
results below remain evidence for their dated revisions, not support promises.

The approved Stage 3 route uses the
[exact Windows environment profile](WINDOWS_ENVIRONMENT.md). Independent
Windows 11 fresh-install and update/rollback acceptance remain separate under
Stages 4–5. See the [Issue #82 roadmap](ISSUE82_RELEASE_ROADMAP.md) for the
remaining gates and the [release policy](RELEASE_POLICY.md) for tested revisions.

Git contains the shared software. Each computer creates its own Python environment
and physical-display configuration. Scientific records live in an external data
workspace. Never copy another computer's `.venv` or treat its calibration as valid
for a different display.

For a source ZIP or tar archive, extract the complete tree to a fresh
folder and follow the [qualified laboratory software installation](#qualified-laboratory-software-installation)
below. The ordinary development setup menu applies to Git checkouts.

## First installation from Git (ordinary Python 3.11)

1. Clone the complete repository into a writable folder under your ordinary Windows account.
2. Double-click **PsyCoLab.bat** and choose **2 — Check / Repair**. If it reports missing Python, install **64-bit
   Python 3.11**; with the Python install manager the command is `py install 3.11`.
   Reopen the launcher afterwards. An explicit interpreter path can be selected
   with `PSYCOLAB_BOOTSTRAP_PYTHON`. PsyCoLab does not edit global PATH.
3. With no existing `.venv` or `.venv-dev`, choose **I — Install source environment**
   and type **YES**. Setup runs in the same terminal and returns to the menu.
   Choose **1 — Launch PsyCoLab**. Initial package installation
   requires internet/package-index access; subsequent matching launches do not.
4. Choose the external data folder, configure the experiment and display, and Review.
   Software installation does not calibrate apparatus or qualify a study.
5. After a run, inspect the results, configure a repeat, or select another experiment.
   Exit the TUI explicitly when the laboratory session is finished.

The same Python environment is available through **3 — Python Workspace** in
`PsyCoLab.bat`. This opens a normal command prompt for commands and scripts, including
scripts outside the checkout. The launch working directory is the checkout;
independent scripts should use explicit data paths or paths relative to `__file__`.
Do not add packages to a qualified environment in place. Existing separate
`USER_env` folders and their requirements files are preserved but no longer
selected by the current launcher. The `run_user_env.bat` root wrapper is retired;
retarget shortcuts/scripts using the [migration table](../outdated_code/windows_launchers/README.md).

An existing environment is checked without installation. A failed check does not
replace it, silently fall back to a different Python, or resume an interrupted
setup. Choose **2 — Check / Repair** for supported initial setup, repair or
restoration. See [repair and restore](SOURCE_INSTALLATION_RECOVERY.md).
First-time failure messages remain visible in the launch terminal.

## Qualified laboratory software installation

The ordinary source route above uses the existing development setup and does
not claim the exact locked interpreter profile. For a qualified deployment,
follow [WINDOWS_ENVIRONMENT.md](WINDOWS_ENVIRONMENT.md) and its explicit approved
bootstrap/setup commands, or the separately qualified guided installation.
`scripts/launcher_setup.py` retains the exact interpreter, binary-wheel,
installation identity and qualification checks. An existing laboratory `.venv`
is always preserved and checked as such. No administrator rights are added by
the source launcher. Physical calibration and experimental qualification remain
separate requirements on either route.

See [launcher inventory and evidence](WINDOWS_LAUNCHERS.md) for the process chain,
compatibility entry points, offline diagnosis, and current acceptance limits.

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
`>=1,<2` and Matplotlib `>=3.8,<4` in its broad package metadata. Supported launcher
installation additionally enforces the reviewed exact runtime/build closure in
`requirements/windows-cp311/`, including Textual 1.0.0 and Matplotlib 3.11.2.
Hashes, binary-only installation and controlled editable builds prevent floating
tool or transitive upgrades. Development requirements remain separate.

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
Changed dependency configuration is refused without upgrading the environment.

If the existing build tools cannot perform the refresh, or imports still point
elsewhere, setup stops without starting the application or recording success.
Inspect the reported error (including inherited Python paths), correct the
environment deliberately, and rerun the launcher. Setup does not automatically
upgrade the environment to conceal the error. See the [Windows environment
guide](WINDOWS_ENVIRONMENT.md) for exact build tools, locked dependencies,
USER_env constraints, bounded pending-install retries and qualification limits.

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
