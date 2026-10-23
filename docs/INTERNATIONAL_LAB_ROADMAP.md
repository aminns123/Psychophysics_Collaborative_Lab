# PsyCoLab: international laboratory roadmap and operating model

**Status:** planning and contributor/user guidance, reviewed against `main` after Design E (PR #78), 23 October 2026. This document distinguishes existing behaviour from proposed changes. A checked item is not evidence of measured display calibration.

## Why this separation matters

PsyCoLab should remain understandable to a scientist reading **one stimulus class and one experiment Python file**. The terminal UI is the researcher-facing hub, not a source-code generator. The engine supplies reusable presentation, calibration, adaptive, simulation and canonical recording services. Each experiment owns its scientific policy. A researcher should be able to install a framework update without unintentionally modifying their own studies or historical participant records.

### Three layers and the present boundary

| Layer | Responsibility | Where it lives today | Status |
|---|---|---|---|
| 1: Core | TUI, calibration, run/simulation engines, adaptive and storage services, registries | `src/psychophysics_lab/{ui,config,core,adaptive,data,stimuli}` | Implemented; maintain as protected framework code |
| 2: Curated science | Shared stimulus classes and published experiments (CSF, flanker, ellipse, teaching tasks) | `src/psychophysics_lab/stimulus_library.py` and `src/psychophysics_lab/experiments/*.py` | Implemented, automatic experiment discovery; curated contributions need review |
| 3: Lab-local studies | Locally written, pilot, unpublished or institution-specific science and presets | Current work can be kept on branches/forks; settings presets and calibration live in local configuration | **Independent external scientific-code loading is NOT implemented yet** |

**Do not treat creating a Git-ignored directory as implementing Layer 3.** The current public experiment loader scans the packaged experiment directory; the runner verifies registered source files under the repository root. An external sibling directory cannot safely be run through the standard TUI without explicitly extending discovery, source identity, validation and provenance.

## Decisions for routine researcher use — available now

1. For **different values of declared scientific settings**, use the TUI configuration and **local presets**. This includes run-specific conditions, timings and adaptive choices declared by the experiment. Reusing a preset must start a new run, not overwrite the original.
2. For **different scientific equations, trial order, response meanings or stimulus classes**, author Python on a **Git branch or fork**. Keep the seven-section experiment narrative, the single shared stimulus-class convention, and the published Draft/Test/Ready checks.
3. Keep source, machine-local configuration/calibration and external acquisition data separate. Never keep participant data or personally identifying records in a public PR.
4. Do not download a new ZIP and extract it on top of a working Git checkout. Always review local changes and back up custom code before updating.
5. Stable future releases should be used for laboratory acquisition instead of following the moving `main` branch, **once** releases have been reviewed and published. There is no approved `v1.0.0` release implied by this roadmap.

See [Safe updates and local work](SAFE_UPDATES_AND_LOCAL_WORK.md) and [Contributing experiments and stimuli](CONTRIBUTING_EXPERIMENTS.md) for reproducible steps.

## Change programme: separate reviewable PRs

### P0 — preserve existing behaviour and document it (this first PR)

- [x] Write an international researcher/contributor narrative.
- [x] Document safe Git clone/fork/branch/update versus unsafe ZIP overlays.
- [x] Clarify that existing external data, local monitor profiles and local presets are separate from Git.
- [x] Correct misleading authoring/registry instructions and stale experiment counts in current guides.
- [x] Record current schema versions, known unknowns and policy for future migration.
- [x] Begin `CHANGELOG.md` and release readiness guidance.
- [ ] Audit **every** Markdown document for stale paths, links, behaviours and calibration claims; preserve dated audit reports as historical evidence, annotate instead of rewriting historical claims.
- [ ] Add automated documentation-link checks, if they prove useful without introducing more dependencies.

Acceptance: this PR changes documentation only. Existing scientific/runtime code is untouched.

### P1 — independent local extensions (separate **code** PR; not implemented by P0)

Proposed sibling layout:

```text
Laboratory/
  Psychophysics_Collaborative_Lab/   # tracked framework, safe to update
  PsyCoLab_Extensions/               # local experiment/stimulus source; own Git history optional
    stimulus_library.py              # ONE researcher-owned file containing LibraryStimulus classes
    experiments/
      my_task.py                     # ONE file per experiment, exports SPEC
    presets/                         # optional local settings
    tests/                            # optional lab fixtures
  local_psychophysics_config/        # monitor revisions, photometry and preferences
  local_psychophysics_data/          # immutable acquisition/run records
```

**Implementation gates (all required):**

1. User explicitly selects/authorises a local source root. No silent scanning of arbitrary folders, automatic downloads, untrusted execution or overriding built-in IDs.
2. The loader discovers only supported classes and experiment `SPEC` declarations with stable names and **no competing stimulus-writing framework**. Fail clearly for duplicate IDs, invalid imports, symlinks outside the allowed root or unavailable dependencies; keep built-ins usable.
3. Store the external-root choice in machine-local preferences, **not** the shared repository. Preserve it across `git pull`, moving the framework checkout and restarting the TUI.
4. Extend source resolution consistently in the TUI, experiment/source inspectors, publisher/validator and runner. Never make a source look like a built-in `src/...` file when it lives elsewhere.
5. Before a human run, verify hashes/validation of the **exact** loaded local scientific sources; distinguish Draft, software-tested and physically qualified. A changed file invalidates readiness; local sources must never bypass hardware and experiment qualification gates.
6. Record portable extension identity, relative source path within its named extension root, source SHA-256, declared dependencies, selected parameters and software/Git provenance in **new** run metadata. Do not record private absolute home paths as canonical identities.
7. Handle old run manifests and source lookup without trying to import a missing/renamed local extension to display already acquired data.
8. Write actual headless registry, TUI, import, simulation and provenance regressions on Windows and Linux. Verify custom visual appearance and timing physically before human acquisition.
9. Do not migrate/copy/delete scientists' existing source, presets, monitor profiles or participant data as part of enabling extensions.
10. Document the upgrade, backup, export/import and promotion-to-official-PR path. Promotion means deliberate review and copying the finished scientific definition into the official source location, **not** an automatic filesystem move.

**Reason this needs a separate PR:** current `ExperimentSpec.source_paths`, registry discovery, user editing, draft/ready fingerprinting and runner guards assume package/repository-relative Python files. A folder alone would give a misleading impression of supported acquisition.

### P2 — explicit saved-format compatibility, with no silent data rewrite

Inventory each independently versioned persisted object and its writer/reader. Verified current examples include run manifest `schema_version: 3`, experiment configuration `schema_version: 2`, luminance dataset `schema_version: 1`, and workspace convenience state `schema_version: 3`. The acquisition directory layout has independent version `1`. **Not every saved object necessarily has a uniform schema today.** Check monitor profiles, `resolved_experiment.json`, scenario reports, JSON presets, calibration status files and each analysis export individually.

For each format:

- Specify current writer version, supported reader versions and fields with physical/scientific meanings.
- Add fixtures representing real earlier supported versions and tests that open them unchanged.
- Refuse unknown newer/ambiguous schemas with a clear explanation. Never silently insert new scientific values or reinterpret a unit/response category.
- Where migration is indispensable, write a **new** file/destination, retain the original and SHA-256, provide a preview/diff and demand deliberate confirmation. Never destructively migrate canonical `trials.tsv`, original manifest, captured hardware evidence, monitor history or prior calibration.
- Mark deprecations in release notes; stop reading a format only after a documented support window and migration path.
- Keep demonstration fixtures free of participant identifiers.

No P2 migration is authorised until the inventory and acceptance tests are reviewed.

### P3 — contributor governance and trustworthy releases

- Maintain clear contribution rules: scientific intent, supported task and source location, unique ID, parameter units/ranges, stimulus preview, simulation where supported, response/adaptive/timing assumptions, run-provenance validation, no changes to existing protocol defaults without explicit scientific review.
- Require separate PRs for scientific changes, UI, data/schema changes and dependency upgrades; review/fingerprint source, avoid merging broken hardware-independent tests without documenting the reason.
- Select a software licence and verify permissions for bundled third-party sources **with repository-owner/institutional review**. There is no selected licence in the repository as of this review; a public GitHub repository is not automatically open-licensed.
- Start a maintained changelog and publish **tagged releases** with release notes, supported Python/OS/runtime stack, known limitations and reviewed Windows lab-acceptance evidence. The current Python package declares version `0.2.2`; a release tag is not implied.
- Use reproducible, reviewed dependency constraints for supported hardware platforms. Do not claim general Linux acquisition support from headless tests.
- First stable release must be a deliberate decision after resolving/blocking and documenting the existing 12 pytest failures, confirming source and schema compatibility and completing hardware/photometry/timing acceptance on designated setups.
- CI quotas may prevent immediate cloud test completion; local Python 3.11 test results and Windows acceptance evidence should still accompany release proposals.

### P4 — long-term exchange and institutional support

- Export a **study bundle** containing scientific source and hashes, parameters/presets, procedural versions, calibration requirements, and non-identifying metadata. Human records remain a separate, explicitly approved export with privacy/ethics safeguards.
- Import in a preview-only mode first: detect conflicts, unknown schema versions, missing external modules and unsupported calibration hardware; never import external Python as trusted execution without opt-in.
- Keep platform-specific guidance for monitor/GPU/photometer qualification, fallback paths for users without physical measurement instruments, support contact and troubleshooting.
- Make non-programmers able to select, configure, calibrate, simulate, inspect and run **already trusted** studies through the TUI; do not hide the explicit Python source from scientists creating new studies.

## Risk register

| Risk | Mitigation |
|---|---|
| A local scientist edits a tracked official experiment and updates | Prefer presets; keep code in a branch/fork; status/backup before fetch/merge |
| `git clean -fdx` or ZIP overlay removes ignored local files | Prefer external sibling extension source and independent backup/Git |
| Two labs use the same experiment ID for different science | Unique IDs and namespace/origin/provenance; no override of official definitions |
| Untested new Python silently enters acquisition | Draft/Test/Ready plus exact-source hashes and unchanged physical gates |
| Historic calibration becomes unreadable after update | Versioned readers, fixture tests, original-file preservation and explicit migrations |
| OS/GPU supports nominal 10-bit but not validated luminance/timing | Separate physical video-chain tests; software checks cannot certify photons |
| Historic data cannot be interpreted without a deleted extension | Self-contained run snapshots, human-readable identities and portable source fingerprints |
| Community contribution changes existing science | Scientific change declaration, focused tests, human review and no auto-merge |

## Roles and evidence

- **Researcher:** author and inspect science, select settings, create local backups, validate/stage, retain hardware evidence and confirm participant readiness.
- **Maintainer:** review proposals/PRs, run software regression checks, document version impact, protect main and publish validated releases.
- **Lab/institution:** assess physical display and response timing, instruments and ethics/privacy; keep secure acquisition archives.

A passing headless suite is never a substitute for photometry, source-device setup, display refresh/signal-depth checks or genuine participant-hardware qualification. Software-ready does not imply physically calibrated or publication-ready.
