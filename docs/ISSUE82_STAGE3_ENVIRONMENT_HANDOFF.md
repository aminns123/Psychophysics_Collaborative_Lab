# Issue #82 Stage 3: Windows environment qualification handoff

**Status: preparation only — no dependency lock is approved or installed.**
This is a narrow Windows 11 / x64 Python 3.11 installation-identity task, not
scientific or apparatus qualification. Read
[Issue #82 roadmap](ISSUE82_RELEASE_ROADMAP.md),
[Windows acceptance policy](WINDOWS_ACCEPTANCE_POLICY.md) and
[release policy](RELEASE_POLICY.md) first.

## Verified gaps in the current source

- `pyproject.toml` fixes NumPy `1.26.4` and Pyglet `1.5.27`, but leaves
  Textual `>=1,<2`, Matplotlib `>=3.8,<4`, pytest `>=8,<9`, and transitive
  packages subject to future resolution.
- `scripts/launcher_setup.py` creates an editable local `.venv` and correctly
  verifies package source, installed version and editable provenance. On first
  installation it **upgrades pip, setuptools and wheel without version bounds**;
  it tracks `pyproject.toml`, not a full reviewed environment lock. Existing
  `USER_env` may add optional lab-specific dependencies.
- Hosted Windows CI installs `.[dev]` with floating dependencies. Its headless
  success does not prove that a second Windows 11 machine reconstructs the
  same environment.
- The accepted Windows 11 development evidence used a conda-forge CPython
  3.11.15 interpreter, while GitHub hosted Windows may use a different patch
  and distribution. **Neither is an authorised release installer by itself.**
- Preserve the existing launcher, editable installation model, trust/Ready
  invariants and local data/config/extensions separation.

## Decision that requires evidence, not guessing

The maintainer must approve **one** x64 CPython 3.11 distribution, patch/build,
acquisition source and expected platform, backed by a clean Windows installation
trial. Do not silently select conda-forge or python.org as universal policy.

Build an auditable, exact runtime environment specification:

1. Full runtime dependency closure with exact package versions and reviewed
   Windows wheel/artifact hashes, including compatible NumPy/Pyglet/Textual/
   Matplotlib and all transitive libraries.
2. Explicit bootstrap/build tools (`pip`, `setuptools`, `wheel`) with reviewed
   versions and installation ordering; handle isolated build dependencies
   explicitly rather than assuming runtime constraints govern them.
3. Separate optional development/test requirements so a laboratory installation
   does not depend on pytest or unnecessary test extras.
4. Separate lab-owned `USER_env` extras. If extras conflict with the approved
   runtime, fail with actionable explanation; do not replace them silently.
5. Source commit, interpreter/distribution identity, constraints-file digest,
   complete installed inventory and installer/artifact identity. Keep these
   distinct from scientific run provenance and from photometric qualification.

Do not assume `pip freeze` alone establishes artifact identity. Hash-validated
installation, `pip check`, editable source/metadata identity and read-only
installed-inventory comparison should be separately demonstrable.

## Integration boundaries

- Keep `run_psycolab.bat`, `scripts/launcher_setup.py`, existing `.venv`
  reuse and editable installation as the public workflow.
- No unconditional latest-package upgrade once a reviewed lock is adopted.
- On an incompatible/missing/stale environment: explain the mismatch, preserve
  the old environment and external laboratory files, and require an explicit
  bounded repair or new isolated environment. Do not silently change previously
  qualified local science or auto-mark extensions Ready.
- A lock change is a deliberate software release event and must invalidate any
  cached setup state that assumed the previous environment.
- Do not alter trial algorithms, presentation timing, stimulus classes, contrast
  methods, experimental defaults, recording formats, historical saved runs,
  calibration or TUI layout.

## Tests and review gates

Run these with disposable Windows 11 checkouts and empty environments:

- Two independent constructions of the **same approved** interpreter/lock.
  Compare full inventories, interpreter/build identity, lock hashes and the
  installed editable project identity.
- First launcher run and second no-change run; deliberately corrupted/stale
  editable identity; missing package; changed lock; incompatible Python;
  package-index/network failure (without unbounded retries or mutation).
- All ten official experiment imports, extension import and Ready fingerprints,
  a short deterministic synthetic run, canonical saved-data validation, and
  read-only archive compatibility.
- Demonstrate protected external extensions, config/calibration and acquisition
  roots remain byte-identical during installation/setup.
- Targeted launcher regression first; one final full Windows suite and required
  Windows CI on the exact PR head before production integration. Real Windows
  11 and hosted Windows Server are separate evidence.

Stage 4, after acceptance of this specification, is an independent Windows 11
workstation/fresh-researcher rehearsal. Stage 5 covers reviewed update/rollback
between *approved* old/new environments. Neither is satisfied merely by writing
a constraints file.

## Delivery

Return the interpreter decision and provenance, full version/hash inventory,
a concise explanation of chosen package-resolution approach, a minimal
integration PR, targeted/full Windows tests, reproducible first/repeat launcher
evidence and explicit remaining risks. **No automatic merge, tag, release or
physical-calibration claim.** If artifact versions or hashes cannot be
independently verified, stop at a candidate design rather than inventing them.
