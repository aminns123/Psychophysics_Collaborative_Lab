# Safe Git updates and protection of local PsyCoLab research

This guide applies to the current source-based PsyCoLab installation. It protects **locally authored Python, presets, monitor calibrations and external run data** while letting a researcher obtain later reviewed framework updates.

## Know which files belong where

| Work | Current supported location | Will an ordinary framework update replace it? |
|---|---|---|
| Official experiment/stimulus Python | Tracked `src/psychophysics_lab/experiments/` and `src/psychophysics_lab/stimulus_library.py` | Git integrates updates and may produce merge conflicts; never assume local edits are immune |
| Experimental values/presets saved through TUI | Machine-local configuration root (outside checkout) | Not included in a normal Git pull; back up separately |
| Local monitor/calibration measurements and history | Machine-local configuration root (outside checkout) | Not included in a normal Git pull; hardware identity/physical qualifications still must be checked |
| Participant/synthetic run records | External data root (outside checkout) | Not included in a normal Git pull; archive/restore separately |
| Lab-owned Python experiments and stimuli | **Explicitly trusted external extensions root**, separate from the checkout | Normal framework Git pulls do not touch external files; keep independent backups and retest readiness after scientific changes |

Do not edit the Python files to change a single experiment's declared *run values* when the TUI already exposes those controls. Save a named local preset. **Changing the scientific code itself** requires a source-controlled version, retesting and potentially protocol requalification.

## Case A — update an unchanged Git checkout (Windows PowerShell or CMD)

In the repository directory:

```powershell
git status
git fetch origin
git switch main
git pull --ff-only origin main
```

Inspect the changed files before opening PsyCoLab, then rerun `run_psycolab.bat` and verify that the selected monitor, presets and intended experiment remain present. A `git pull --ff-only` refuses to create an unexpected merge commit; it is not a method for discarding changes.

## Case B — you edited tracked official Python files

**Do not overwrite them with a ZIP or force a pull.** First use `git status` and save the work on your own branch. For example, when edits are still uncommitted:

```powershell
git switch -c lab/my-custom-study
git add src/psychophysics_lab/experiments/my_task.py
git commit -m "Save local my_task study"
git switch main
git pull --ff-only origin main
```

If you also changed the shared `stimulus_library.py`, explicitly include it in the commit after checking its diff. Avoid `git add .` when unsure of what personal files are present.

You may later incorporate updated core changes into your lab branch:

```powershell
git switch lab/my-custom-study
git merge main
```

A conflict **requires an explicit human decision** about the resulting scientific procedure. Do not accept a whole-file automatic replacement just to get the merge to complete. Review diffs, test the final values/equations and update the source fingerprint/readiness status as appropriate.

A branch is not an independent backup of a lost disk. Push to a trusted private remote or maintain an offline backed-up copy, particularly before major updates.

## Case C — contributing your study to PsyCoLab

Work on a branch in a fork (or an authorised contributor branch), then open a PR proposing only the reviewed files. Put a new approved experiment in `src/psychophysics_lab/experiments/<id>.py` and a new stimulus class in the existing `stimulus_library.py`; see [contributor rules](CONTRIBUTING_EXPERIMENTS.md). Do not place participant runs, local display calibration, or institutional/private files in the PR.

For a fork, `origin` usually points to your fork and `upstream` to the official repository. Verify with `git remote -v`. Fetch from the actual upstream remote; do not assume remotes have been configured for you.

## ZIP extraction, stash and destructive commands

- **Do not overlay a downloaded ZIP** onto an old checkout: matching files may be overwritten and removed files may remain as stale code.
- `git pull` does not casually delete a committed branch, but merge conflicts, resets, force commands and manual overwrites can still destroy local work.
- `git stash` is temporary, not a durable backup; it does not include ignored files by default. A stash apply/pop can conflict.
- **Never use `git reset --hard`, `git clean -fdx`, forced checkout, or directory deletion on a lab's sole copy** without an independently verified backup. `git clean -fdx` can delete ignored local extensions and virtual environments.
- Keep original `manifest.json`, `trials.tsv` and physical calibration evidence intact. Back up *both* external configuration and data directories, not just the source checkout.

## Running a lab after an update

1. Confirm the selected profile and revision on the *actual* monitor; do not inherit another institution's qualification by copying a JSON file.
2. Inspect the chosen experiment's parameters, timing, response keys, adaptivity and stimulus class.
3. Preview and simulate representative conditions; verify expected data outputs and recorded provenance.
4. Check the experiment's software test/Ready state and human calibration/protocol gates. A source change can invalidate previous validation.
5. For actual acquisition, repeat required physical display, photometry, signal-depth, and timing qualification. Real hardware tests cannot be inferred from headless CI.
6. If unexpected behaviour occurs, preserve the old source tag/commit, test outputs and logs before troubleshooting. Revert through a reviewed branch rather than modifying historical data.

## Independent laboratory extensions (supported opt-in)

For lab-owned Python, use the [external extension guide](LABORATORY_EXTENSIONS.md).
The researcher must deliberately authorise one trusted source root, separate
from the framework, configuration and acquisition folders. PsyCoLab loads
source into its existing registries and runner only when enabled; it never
silently discovers or migrates scientists' code. Source fingerprints and
software Ready are recorded independently of hardware qualification.

A private branch/fork remains appropriate for editing **official** code or
submitting a curated contribution. An external folder is not an off-machine
backup: keep a separate copy or its own private Git repository. Preserve the
exact experiment source associated with old run manifests and never overwrite
laboratory files by unpacking an official source ZIP.
