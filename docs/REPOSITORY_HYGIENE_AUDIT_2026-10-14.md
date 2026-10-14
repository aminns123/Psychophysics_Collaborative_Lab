# Repository hygiene and Windows installation audit — 14 October 2026

## 1. Repository baseline and scope

The inspected checkout is on `main`, remote
`https://github.com/aminns123/Psychophysics_Collaborative_Lab.git`.
Local HEAD and the live `git ls-remote origin refs/heads/main` result both identify
`ae305b8c12e33ccfbd0c7bec396fefcb9bd73bc9`. The initial tree was clean, with no
untracked non-ignored files or staged changes. The earlier Python 3.11 launcher
fix is already part of this baseline. No fetch/pull, reset, rebase, merge,
commit, push, remote branch deletion or pull request was performed.

All expected source/install resources exist: `run_psycolab.bat`, `pyproject.toml`,
`scripts/launcher_setup.py`, `src/psychophysics_lab/`, `Experiments/`, `Events/`,
`.gitignore` and `.git/`. All 195 initially tracked files are classified in
[the complete inventory](audit_evidence/repository_hygiene_inventory_2026-10-14.tsv),
including original SHA256 hashes. The inventory describes this baseline, not
new audit documents added afterward.

## 2. Shared files retained

| Baseline group | Files | Purpose / decision |
|---|---:|---|
| `src/` | 70 | Framework, stimuli, calibration algorithms, acquisition, analysis and TUI; unchanged |
| `Events/`, `Experiments/`, `Functions/`, `Interface/` | 8 | Active legacy scientific implementation; unchanged |
| `simulations/` | 14 | Synthetic observers, scenarios and reproducibility tools; unchanged |
| `tests/` | 52 | Automated tests; extend portability cases only |
| `scripts/` | 6 | Installation, checks, validation and hardware probes; extend portability checker only |
| `configs/` | 1 | Unverified shared reference specification, not a user's calibration |
| `docs/` | 30 | Scientific guidance and curated software/audit evidence; retained |
| `examples/` | 1 | Contributor example; retained |
| `.github/` | 1 | Windows/Linux headless CI; retained |
| Root files | 12 | Packaging, launcher, legacy engine, archive, Git policy and documentation; see cleanup decisions below |

No actual participant acquisitions were identified among the tracked files.
Tracked JSON and text audit evidence are curated software records; test data
definitions are synthetic fixtures. No broad JSON/CSV/PNG/ZIP ignore rules were
introduced. `configs/monitors/legacy_reference_display.json` has an empty
luminance table and `manual_unverified` status, so it remains shared.

## 3. Local environment, configuration and data

The default layout already uses a checkout-local ignored `.venv` and sibling
`local_psychophysics_config` and `local_psychophysics_data` folders. Custom
configuration/data overrides and local preferences remain supported.
No path overrides were set in the inspected process; both effective roots resolve
to those default sibling folders.
`resolve_data_root` rejects a data directory inside or above the checkout;
`config_root` rejects overlap with source and, when supplied, the data root.
No paths or user records were migrated.

The default external data folder existed with **10 files**. Its relative
hierarchy, contents and filenames match the pre-audit SHA256 inventory exactly
after testing. The default local-configuration folder was absent and remains
absent; no calibration was fabricated. The repository preference-file state
is also unchanged. Personal data values and filenames are not copied into this
shared report. Ignored environment, cache, package metadata and existing logs
remain local.

Local monitor profiles retain immutable revisions, physical snapshots and
display bindings; edits invalidate dependent declarations. Run records retain
configuration/profile snapshots, provenance and state. Synthetic runs have
reserved participant IDs and explicit markers. Active calibration records and
history are local; raw luminance sessions and diagnostic reports may also live
in the external scientific workspace. All scientific/calibration/runtime code
was preserved byte-for-byte.

**Limit:** the software does not guarantee unique physical hardware identity
across computers. OS device identifiers can repeat, and the existing unverified
legacy-reference compatibility path remains. Do not transfer calibration claims
to a different display. Physical remeasurement/review is required; this audit
does not change the calibration acceptance policy.

## 4. Cleanup implemented

| Item | Exact action |
|---|---|
| `.gitignore` | Preserve existing protections; add `desktop.ini`, `Thumbs.db`, `.DS_Store`, `.env`, `.env.*`, exception `!.env.example`, `local_psychophysics_config/`, and `PsyCoLab_Data/` |
| `desktop.ini` | `git rm --cached -- desktop.ini`; local bytes preserved and now ignored. This is the only staged deletion and only file untracked without a shared replacement |
| `OVERLAY_MANIFEST.txt` | Move unchanged to `docs/history/2026-09-15-overlay/OVERLAY_MANIFEST.txt` |
| `PSYCOLAB_UPDATE_NOTES.md` | Move unchanged to `docs/history/2026-09-15-overlay/PSYCOLAB_UPDATE_NOTES.md` |
| `docs/history/2026-09-15-overlay/README.md` | Explain historical-only status and the original manifest paths/hashes |
| `scripts/portability_check.py` | Reject tracked filesystem metadata, environment/secret files, preferences and local config/data/cache directories, including nested variants |
| `tests/test_portability.py` | Add 12 rejection cases and 6 positive cases for legitimate examples/resources |
| `README.md` | Link the current installation guide |
| `docs/ARCHITECTURE.md` | Replace pending archive-inventory wording with the observed dependency limitation |
| `docs/INSTALLATION.md` | Document current installation, data/config separation, checks and reproducibility limits |
| This report and inventory | Preserve reviewable audit evidence |

The old overlay notes instruct users to overwrite checkout files from a ZIP and
refer to the September baseline. Only the historical manifest references those
notes; current runtime/setup code does not use either document. Their archived
copies are byte-identical, including line endings. All other historical audits
remain intact.

### `packages.zip`: retained, not obsolete

Size: **1,158,761 bytes**. SHA256:
`deb26d7084bd5e335cfdeb2be10e35b7a38ed2019d2df6f793939e759e291877`.
Read-only ZIP inspection, with no extraction/import/execution of its members,
found **233 entries / 196 files**, totaling 5,119,222 uncompressed bytes:
195 files beneath `pyglet/` plus `wmi.py` (declared WMI version 1.5.1).
There are 191 Python source files and five Python 3.7 bytecode caches.
The bundled Pyglet source declares **1.5.19**.

It is a vendored dependency archive, not an old snapshot of PsyCoLab source or
participant data. No unsafe member paths, recognizable secret-shaped strings
or user-home paths were found by the bounded static scan; this is not a general
security certification. None of its member paths duplicates a tracked source
file byte-for-byte. Of 190 source paths also present in installed Pyglet,
only 15 are byte-identical, so installed 1.5.27 is not an equivalent copy.
Source headers contain copyright/license notices; complete licensing/upstream
provenance remains a separate review.

The installer uses `pyproject.toml`, not this ZIP. However, `libC.py` prepends
`packages.zip` to `sys.path`, and the acquisition source inventory fingerprints
it. The legacy runtime context sets the checkout directory for that resolution.
Import order can therefore select bundled Pyglet 1.5.19 even though installed
requirements pin 1.5.27. Preserve the archive and its historical evidence until
a separately reviewed renderer-equivalence change removes this ambiguity.
No renderer imports were executed to inspect the archive, and no archive bytes
or scientific behavior were changed here.

## 5. Launcher and dependency installation

`run_psycolab.bat`, `scripts/launcher_setup.py` and `pyproject.toml` remain
byte-for-byte unchanged. The committed launcher already resolves the quoted
full path of `python3.11.exe` after trying `py -3.11`, before generic
`python`/`python3`; every candidate must be Python 3.11.

The Windows command-shell smoke check executed a temporary copy of the actual
batch file with only its working directory adjusted, pauses disabled, and its
final interactive command replaced by `--list-experiments`. It selected
**64-bit Python 3.11.9**, completed setup and listed the CSF experiment with exit
code 0. The unchanged production batch remains ready for double-click use.
An actual Explorer double-click and physical display presentation were not
performed; TUI startup/navigation are exercised by the headless suite.

A separate clean source copy with no `.venv` successfully ran the real setup
script, created a local environment and installed all declared requirements.
Running setup again reused it. Both existing and fresh environments passed
`pip check` and imported PsyCoLab 0.2.2, NumPy 1.26.4, installed Pyglet 1.5.27,
Textual 1.0.0 and Matplotlib 3.11.2. NumPy/Pyglet compatibility requirements and
all dependency declarations are unchanged. No packages were installed into the
user's original environment or global Python during this audit; pytest 8.4.2
was installed only into the separate test environment.

For stronger release reproducibility, consider reviewed Windows x64 / CPython
3.11 constraints with exact transitive versions, installation hashes where
supported, source commit and archive hash. Validate a second clean installation
before adoption. Current version ranges and packaging-tool upgrades are not a
complete lock; a lock alone would not fix the ZIP's import precedence. No new
mandatory lockfile or package manager was imposed.

## 6. Validation results and limits

| Check | Outcome |
|---|---|
| Full existing headless suite plus new hygiene cases | **677 passed, 0 failed, 0 errors, 0 skipped in 133.72 seconds** |
| Final focused portability tests after clarifying the checker remediation message | **27 passed in 0.25 seconds** |
| Fresh Python 3.11 environment creation and installation | Passed |
| Fresh and existing environment reuse | Passed |
| Required package imports / versions / `pip check` | Passed in both environments |
| Actual Windows batch detection/setup and CLI entry point | Passed, Python 3.11.9, exit 0 |
| Python 3.14 setup rejection | Passed, exit 2 |
| Incompatible environment preservation | Created a disposable real Python 3.14 environment; the existing preservation helper moved it to its backup name with every file hash unchanged |
| Ignore checks | 20 local-file paths ignored; 10 legitimate shared/example paths remain trackable |
| `.venv` tracking | No tracked entries |
| Tracked files matching ignore rules | None after untracking `desktop.ini` |
| Repository portability checker | Passed |
| Shared-source path and bounded secret scan | No actual user-home paths or recognizable secrets found; matches in docs/tests were generic examples/detector fixtures |
| Archive inspection | Static only; retained unchanged |
| Preservation | Unrelated tracked files, archived documents, local metadata and all 10 external data files unchanged |
| `git diff --check` | Passed |

The full suite was run against the actual edited checkout using the separate
fresh environment's interpreter and temporary test data/config roots outside
the checkout. Raw installation/test logs and JUnit results remain in the audit
workspace outside the repository, rather than adding personal machine paths to
shared evidence. The temporary environment is not a deployable artifact and
should not be copied to another computer.

No test failures remain. During validation, a harness initially used unqualified
`python` in a Python subprocess; Windows resolved the parent Python directory
instead of the shell's Python 3.14. The negative-version check was corrected to
use the explicit verified Python 3.14 executable and then passed. This was a
test-harness issue, not a production launcher change.

No human experiment, real calibration, photometer measurement, display-binding
change, fullscreen timing validation or Windows setting change was performed.
Hardware acceptance and the bundled-renderer dependency review remain pending.

## 7. Review state

GitHub is unchanged. The branch remains `main` at the baseline commit; the
following local changes await review. Only `desktop.ini` removal is staged.
The historical moves appear as deletions plus new files until staged together;
Git can then recognize them as exact renames.

```text
 M .gitignore
 D OVERLAY_MANIFEST.txt
 D PSYCOLAB_UPDATE_NOTES.md
 M README.md
D  desktop.ini
 M docs/ARCHITECTURE.md
 M scripts/portability_check.py
 M tests/test_portability.py
?? docs/INSTALLATION.md
?? docs/REPOSITORY_HYGIENE_AUDIT_2026-10-14.md
?? docs/audit_evidence/repository_hygiene_inventory_2026-10-14.tsv
?? docs/history/
```

## 8. Suggested commit after review

Suggested message: `Improve repository hygiene and document portable Windows installation`

Run from the checkout. These commands are supplied for the researcher only;
the audit did not run `git add`, `git commit` or `git push`.

```powershell
git diff
git diff --cached
git add -- .gitignore README.md docs/ARCHITECTURE.md docs/INSTALLATION.md docs/REPOSITORY_HYGIENE_AUDIT_2026-10-14.md docs/audit_evidence/repository_hygiene_inventory_2026-10-14.tsv docs/history/2026-09-15-overlay OVERLAY_MANIFEST.txt PSYCOLAB_UPDATE_NOTES.md scripts/portability_check.py tests/test_portability.py
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "Improve repository hygiene and document portable Windows installation"
git push origin main
```

If GitHub advances before the push, review that change separately; do not force
push or discard local work. Existing `.venv`, data and local metadata stay on
disk and are not included in the proposed commit.
