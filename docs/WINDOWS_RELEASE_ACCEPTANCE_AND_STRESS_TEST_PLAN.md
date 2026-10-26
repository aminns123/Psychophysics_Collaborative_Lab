# PsyCoLab — Windows acceptance and historical stress-audit plan

## Current disposition — 26 October 2026

The reliability-repair phase is complete at the
[accepted development baseline](ACCEPTED_SOFTWARE_BASELINE.md),
`5fec547ecf3f86cd6bbd202a9e463637deca07d3`: post-merge Windows CI has
**1,562 passed**, Ubuntu CI **1,560 passed**, zero failures and both
portability checks passed. The earlier audit and its repairs are recorded
evidence, not an instruction to repeat a broad audit without a new failure.

Issue #80's trust, simulation, provenance, archive and source-invalidation
acceptance is recorded in its [reconciled handoff](ISSUE80_VALIDATION.md).
Only current readiness and native source-editor/preset handoff remain there.
The [five Issue #82 stages](ISSUE82_RELEASE_ROADMAP.md) now govern fresh
installation, constraints, update/rollback and release evidence. Physical
measurement and licensing/owner decisions remain separate release gates.
The terminology guide and current installed-Pyglet documentation are already
available; older references below to forthcoming guides or bundled graphics
import precedence describe the original planning state.

## Historical plan opened 25 October 2026 — preserved verbatim

The remaining sections preserve the original evidence table, pending items
and audit instructions for their dated revisions. Their historical
"PENDING", "future" and baseline failure statements are superseded by the
current disposition above; they are not current work orders. Do not erase
or relabel earlier test results as passes.

**Opened:** 25 October 2026. **Status:** software regression passed; independent
lab acceptance remains open. This is a living evidence checklist, **not** a
certificate of psychophysical measurement quality.

See also [Issue #80](https://github.com/aminns123/Psychophysics_Collaborative_Lab/issues/80),
[Issue #82](https://github.com/aminns123/Psychophysics_Collaborative_Lab/issues/82),
[external laboratory source guide](LABORATORY_EXTENSIONS.md),
[installation](INSTALLATION.md), [physical display acceptance](WINDOWS_HARDWARE_ACCEPTANCE.md)
and [scientific terminology](PSYCHOPHYSICS_METHODS_AND_TERMINOLOGY.md)
(the last document arrives in the separate terminology PR).

## 1. Evidence verified on the maintainer's Windows machine

| Gate | Evidence | Decision |
| --- | --- | --- |
| Full Windows headless regression | Synced `main` at `98f4119`; **1505 passed, 0 failed, 4 warnings; exit code 0; 17m34s** | **Software regression PASS** for tested revision |
| Working tree / remote | `git pull --ff-only origin main` successful; `git status` clean | PASS at recorded revision |
| Warnings at time of full run | Four repeated warnings that `new_probe_vertical_line_stimulus` changed since software test | **Historical warning evidence**, not four distinct defects |
| Teaching experiment source retest | `--dev-test new_probe_vertical_line_stimulus` returned `VALID virtual run`, under `PsyCoLab_USER_env_data\...\synthetic_123\...`; `--dev-ready experiment new_probe_vertical_line_stimulus` printed `READY` | PASS **software-only**, pending catalogue restart/inspection |
| UI crash-report line during regression | The successful test suite exercised a deliberate hardware/preflight fault-injection path; a local test crash report was written in isolated `pytest_issue82_final_full` | **Not evidence of an actual hardware failure**; preserve report for investigation only if real use reproduces it |
| Instrument measurements | None supplied by this regression | **NOT VERIFIED** |
| External laboratory-owned source / lifecycle on actual workstation | Existing software test coverage; no completed manual TUI and local-file evidence in this acceptance record | **PENDING** |
| Documentation scientific accuracy | Targeted source-to-guide comparisons started; academic terminology review and current CSF defaults correction prepared separately | **IN PROGRESS** |

Keep a distinction between the **current source revision**, historical
release tag `v0.3.0`, and the exact runtime source hash saved with a
participant session. Passing automated tests is not a substitute for a
reproducible environment or physical verification.

## 2. External extension acceptance (Issue #80) — actual Windows TUI

**Rules:** Do not alter participant acquisition folders, locally verified
calibration records, framework source or a colleague's pre-existing extension
root. Do not overwrite an existing extension file. Use a
**new demonstration/test namespace** in an independent directory if needed.
The extension folder is trusted Python code, **not sandboxed**.

1. **Record baseline:** in the Git checkout, run `git status`,
   `git rev-parse HEAD`, `.\.venv\Scripts\python.exe -m pip check`.
   Confirm external acquisition/config roots are not inside the checkout.
2. **Prepare starter:** start `.\.venv\Scripts\python.exe -m psychophysics_lab`.
   Inspect **Build Experiments → Laboratory Extensions**. The normal TUI
   prepares a starter beside the checkout when necessary; it does **not**
   automatically trust or load it. Record the exact full extension root and
   verify its `psycolab_extensions.json`, `stimulus_library.py`,
   `experiments/demolab__left_right.py` and `presets/left_right.json`
   files. Never assume the parent of a nested older starter is the root.
3. **Explicit trust:** read source first, select exactly the manifest-containing
   absolute folder, then tick **trust** and **Enable trusted folder**.
   F5/restart. Confirm discovered IDs match the chosen namespace, and that
   the user cannot shadow an official ID. Use `--dev-list` to inspect.
4. **Preview and Ready, in the normal USER_env/development workflow:**
   ```powershell
   .\.venv\Scripts\python.exe -m psychophysics_lab --dev-preview demolab__line
   .\.venv\Scripts\python.exe -m psychophysics_lab --dev-ready stimulus demolab__line
   .\.venv\Scripts\python.exe -m psychophysics_lab --dev-test demolab__left_right
   .\.venv\Scripts\python.exe -m psychophysics_lab --dev-ready experiment demolab__left_right
   ```
   **Use these names only if the untouched starter actually has the
   `demolab` namespace.** For a renamed lab extension, use its actual
   IDs. Preview is not measured visual contrast; development simulation
   is not a participant.
5. **TUI equivalence:** restart the TUI. Open Build Stimuli / Build Experiments,
   inspect the source, configure the selected study, inspect the same settings
   in Review and conduct a synthetic run. Verify response/target mapping,
   proposed stimuli, condition values, termination and status against the
   *actual extension's* `make_trial`, `RESPONSES`, `primary_rule`
   when present and `SPEC`.
6. **Canonical provenance:** inspect new synthetic run `manifest.json`,
   `experiment_config.json`, `trial_data_dictionary.tsv`,
   `resolved_experiment.json` and `trials.tsv`. Verify exact source
   origin/namespace, selected values and hashes; run
   `python scripts/validate_run.py <your-new-synthetic-run-folder>`.
   Never reinterpret synthetic measurements as actual luminance/timing.
7. **Source change invalidation, without risking other work:** in an independently
   backed-up *disposable* extension root, change one harmless declared source
   string and verify a former Ready fingerprint is invalidated. Restore or
   deliberately retest and mark Ready. No automatic readiness after a change.
8. **Disable/archival read:** disable external trusted code and restart.
   Confirm the old synthetic trial files can still be read without executing
   the disabled extension. A fresh run must not silently execute it while
   disabled. Do not delete experimental source/data to test this.
9. **Git update isolation:** record hashes of that disposable extension and
   local data before/after `git pull --ff-only` of the framework. A framework
   update must not overwrite lab science, presets or acquired records; a
   framework source change may legitimately invalidate software Ready.

For each line record **date, exact source commit/hash, local path (privately),
observed result, evidence file and pass/fail**. Mark Issues #80/#82 based on
that evidence rather than on a GitHub PR merging.

## 3. Scientific experiment and Markdown documentation audit

**Review active guides against the code, not against each other alone.**
Dated historical reports remain historical; give a conspicuous dated notice
rather than rewriting old results as if the old code never existed.

| Area | Source of truth | Required checks |
| --- | --- | --- |
| New scientist introduction | `docs/LEARN_PSYCOLAB.md`, `src/psychophysics_lab/experiments/README.md` | Seven sections map to real functions; no extra generators/registries; previews and testing instructions work |
| Stimulus definition | `stimulus_library.py`, `docs/AUTHORING_CONTRACT.md` | Exactly one official class/library path, `PARAMETERS`, `render`, `SPEC`, accurate pixel-coordinate/visual-angle descriptions |
| Task nomenclature | Experiment `RESPONSES`, `PARADIGM`, `make_trial`; terminology guide | Distinguish 2AFC, **2IFC**, single-interval two-response classification; never advertise **2AFTC** as a standard term |
| Scientific parameters | Real `FIELDS` and `SCIENTIFIC_SPEC` in each experiment | No stale defaults; check units, lower/upper bounds, required selections, target locations, frequency lists, contrast/increment meaning, response keys |
| Adaptive settings | `adaptive/steps.py`, experiment `initialise_experiment`, `primary_rule`, `docs/ADAPTIVE_METHODS.md` | Up/down streak semantics; García-Pérez ratio validity; true CSF defaults **0.36/0.30294** (4-down/1-up); starting/presented/next contrast, reversal completion |
| Threshold and simulated analysis | `analysis/`, canonical `trials.tsv`, `docs/THRESHOLD_ANALYSIS.md` | Do not claim 75% criterion without a validated model; no fabricated threshold for censored staircases; distinguish post-acquisition estimator and online adaptive rule |
| Temporal presentation | `core/presentation.py`, trial timeline functions and `docs/EXPERIMENT_TIMELINES.md` | First/second intervals really presented; actual response assignments/randomisation; ms vs frames; expected vs measured onset and sound timing |
| Canonical data | `docs/TRIAL_DATA_DICTIONARY.md`, `docs/DATA_LAYOUT.md`, reader/validator | Schema 1 (20 columns) provenance; human vs synthetic; abort/error/censor statuses; old archive readability |
| External extensions | `extensions.py`, `docs/LABORATORY_EXTENSIONS.md`, TUI | Trusted root, local authoring, test/ready fingerprints, namespace ID, provenance, disable/read old runs, update safety |
| Calibration and human readiness | `config/preflight.py`, `docs/HUMAN_EXPERIMENT_READINESS_CHECKLIST.md`, `docs/WINDOWS_HARDWARE_ACCEPTANCE.md` | No fake photometry, no software-flip-as-photon claims; profile revision, gamut, pixel sampling, physical verification and explicit protocol review |
| Installation / version / rights | `pyproject.toml`, `docs/INSTALLATION.md`, `docs/RELEASE_POLICY.md` | Windows 3.11 install, dependencies and bundled Pyglet import precedence, existing prerelease status, licensing, clean reinstall/downgrade |

**Editorial review rule:** If prose and source disagree, document exactly
which function, default, line/commit and experiment differs. Do not silently
edit scientific code or delete an existing test solely to make the prose
look consistent. Resolve it in a separate PR with objective regression
evidence. Cite peer-reviewed psychophysics definitions where terminology
or interpretation is contested.

### Documentation sweep milestones

- [x] Reviewed key active source/guide contracts for 2AFC/2IFC and CSF step defaults; corrections prepared in separate documentation PR.
- [x] Reviewed current extension setup workflow against the actual CLI/documented trust boundary; acceptance **not** yet performed on the maintainer's machine.
- [x] Confirmed full Windows software regression result on the tested `main` revision.
- [ ] Validate every active Markdown relative link and navigation instruction.
- [ ] Line-by-line review of all active experiment/modelling/calibration guides against current source.
- [ ] Confirm historical dated audits are visibly labelled historical and not presented as current instructions.
- [ ] Conduct a fresh Windows clean-install/upgrade/rollback rehearsal and record exact package lock/environment evidence.
- [ ] Perform laboratory hardware and protocol measurement review.

The checklist is deliberately not all checked: preliminary source
inspection does **not** constitute an exhaustive scientific or editorial audit.

## 4. Stable-release gates independent of Python tests

- **Rights:** maintainer/institution approves an actual software licence,
  contributor permissions, citations and bundled historical graphics licences.
- **Install/reproducibility:** clean **Windows Python 3.11** install, explicit
  package constraints and the bundled Pyglet/import precedence reviewed;
  second machine or fresh test environment must reproduce results without
  touching primary acquisition data.
- **Versioning:** `v0.3.0` is already a published **research pre-release**,
  not a stable certified lab release. Do not republish or move that tag.
- **Actual display:** measured active panel dimensions/distance, raster
  mapping and cpd on x/y, output precision and transfer function with a
  real photometer, photon onset/offset with a suitable photodiode,
  response/input timing and apparatus-specific uncertainty. No generic
  threshold for acceptable error without an approved protocol.
- **Scientific protocols:** review sample trials for each study, including
  first/second interval and spatial response identities, low and high
  digital strengths, probe minimum/ceiling behavior, flanker/ring
  composition and per-condition staircase completion. Store evidence
  with the exact monitor/profile revision.
- **Update safety:** data-backup, non-destructive update, archive/schema
  compatibility and documented recovery.

Do not infer research-grade threshold accuracy or unbiased performance
from an internal green test suite.

## 5. Future Work-AI depth/stress audit (do not run until the above gate is ready)

Request a **read-only first** inspection of the authoritative local Windows
checkout and its source/working-tree hash. No alternative checkout may be
silently substituted. Preserve the successful 1505-pass regression baseline
and all local configuration, external extension science and participant records.

Ask Work-AI to:

1. Map the source path from stimulus parameters → raster/presentation →
   human/synthetic response → adaptive state → canonical record → primary
   threshold/plot, with traceable source references for each official study.
2. Generate realistic boundary, randomised/property-based and fault-injection
   tests **only in isolated synthetic/test data roots**: missing files,
   interruption between record stages, bad field choices, numerical
   saturation/underflow, queue timing, stale hashes, repeated starts,
   concurrent IDs/writes and interrupted updates; don't fault-inject real
   participant sessions or interact with a physical display without approval.
3. Verify repeated seeded simulations, response-target balance, trial
   distributions, physical-unit conversions, deterministic analysis and
   original-record immutability across reanalysis.
4. Review Textual navigation on smallest supported terminals, source editor
   and saved drafts, environment install, local extension trust/ID/fingerprint,
   deferred errors, recovery and external data isolation.
5. Inspect the entire **active Markdown surface**, all internal relative
   links, source defaults, paradigm terminology, examples and command
   reproducibility; separately enumerate historical/stale archives.
6. Investigate scientific validity and code quality *separately*:
   report true defects, unproved scientific assumptions, docs inaccuracies,
   security/update risks, and merely optional refactors with severity and
   test evidence.
7. Propose **small reviewable PRs**, never auto-merge, never refactor a
   working experiment just for style, and never revise source values or
   threshold interpretation without explicit scientific sign-off.

Final deliverables: concise failure inventory, Windows proof commands and
logs, unchanged/corrected source hashes, impact assessment per experiment,
documentation link audit, tests, and the remaining physical verification
matrix. **A software stress pass never replaces laboratory measurements.**
