# PsyCoLab final repository audit — 17 October 2026

The local checkout now gives each supported Python experiment one file that owns
its scientific procedure. Stimulus classes remain in `stimulus_library.py`.
The reference CSF is the documented exception: its phase declaration and a
scientific summary are in its experiment file, while its physical renderer and
event/adaptive bridge remain internal until equivalence has been demonstrated.
No new experiment framework, DSL, generator or compulsory registry was added.

## Repository and scope

- Authoritative checkout: `C:\Users\alexz\Personal_Folder\Git_Folder\Psychophysics_Shanghi`.
- Starting branch: `main`; starting HEAD: `651b928371dc577717dbef96acdaa9c292d02c1a`.
- Starting working tree: clean. Working branch: `audit/researcher-facing-procedures`.
- Changes are local and uncommitted. Nothing was pushed, merged or deployed;
  `main` remains at the starting HEAD.
- Synced ChatGPT project sources and participant records were not modified.

The recursive per-file classification is in
[`final_repository_inventory_2026-10-17.tsv`](audit_evidence/final_repository_inventory_2026-10-17.tsv),
with directory and method details in
[`final_repository_inventory_summary_2026-10-17.json`](audit_evidence/final_repository_inventory_summary_2026-10-17.json).
It covers tracked paths, their removals and new non-ignored files. Implementation/reference text candidates were read by the structural scan,
Python files were parsed,
and binary resources were hashed. Generated inventory manifests omit their own self-hashes. Import relationships, literal references,
definitions and identical-byte groups are recorded. Dynamic SPEC/subclass
discovery, manifest/catalogue loading, runtime configuration and tests supplement
static searches; zero direct imports alone was not treated as proof of dead code.
Local environments, Git internals, preferences and generated logs remain local
tooling, not researcher authoring sources. The inventory is not a claim that
every scientific assumption has been experimentally validated.

## Scientific ownership after consolidation

| Experiment | Scientific source and evidence |
|---|---|
| Base Flanker | `experiments/base_flanker.py`: settings, literal geometry, line position, target schedule, active-condition selection, timing, UP/DOWN meaning, adaptive policy, stopping and measurements. Original complete software trace matches. |
| Indirect Flanker | `experiments/indirect_flanker.py`: the matched task including the left grating. Pairing tests still show the grating is the intended difference. Original complete software trace matches. |
| Ellipse 2D | `experiments/ellipse_2d.py`: ellipse/probe composition, explicit missing-source decisions, interval ordering, first/second response meaning, adaptation and stopping. Literal historical geometry quirks remain. Original complete software trace matches. |
| Orientation | `experiments/orientation_task.py`: balanced seeded tilt alternatives, four phases, durations, keys, correctness and response-count termination. No runtime timeline JSON lookup. |
| Adaptive orientation | `experiments/orientation_adaptive.py`: its own procedure plus 2-down/1-up, .8/1.25 contrast factors, [.001, 1] bounds and accepted-response ceiling. No delegation to orientation_task.py. |
| Built-in above/below probe | `experiments/probe_above_below.py`: former JSON procedure now explicit Python, including seeded balancing, +/-2 degree positions, phases, keys, correct-count update and termination. Both position timelines and update behaviour match the retained design. |
| Worked left/right line | `experiments/example_experiment.py`: already a local chronological procedure; retained. |
| Researcher's above/below line | `experiments/new_probe_vertical_line_stimulus.py`: retained as an independent managed experiment; remapped-key instructions fixed and Ready refreshed after a successful virtual run. |
| Reference CSF / flanker-response name | `experiments/contrast_sensitivity.py`: fields, response contract, five-phase declaration and documented geometry/audio/driver exceptions. `flanker_response.py` remains an internal name-disambiguation alias, not another registered experiment. |

Each direct Python procedure now belongs to its named experiment module. A new
Python file exports `SPEC` with an ID matching its filename and is discovered
without editing a module list. JSON presets are optional for new definitions;
existing selected presets retain their identities and provenance. Managed
Draft/Test/Ready files continue through fingerprint checks and are excluded from
plain discovery, so automatic discovery does not bypass that gate.

For a real example, the README connects `TeachingGabor` to
`orientation_adaptive.py`. `docs/LEARN_PSYCOLAB.md` is the beginner walkthrough.
TUI source inspection opens the actual owner file and labels old orientation
timeline JSON as a compatibility example rather than an executed definition.
Retired JSON authoring flags remain callable internally for saved-work
compatibility but are hidden from normal CLI help; their unused TUI widget is
removed.

## Shared mechanisms retained, with reasons

The complete decision/mechanism table is in
[`AUTHORING_CONTRACT.md`](AUTHORING_CONTRACT.md#scientific-decisions-retained-internally).

- `core/scene_primitives.py` implements reusable drawing equations once;
  experiments select primitive types, dimensions, amplitudes, placement and
  layering. Ordinary new stimulus maths still belong in their library class.
- `adaptive/staircase.py` and `adaptive/legacy_flanker.py` implement counters,
  state and historical logarithmic/reversal algorithms once. The experiments
  declare their chosen settings, contrast transforms and stopping policy.
- `researcher.py`, `core/timeline.py`, `core/trial_execution.py` and presentation
  services execute the same Python procedure for live and virtual response
  sources, interpret declared alternatives, and save raw keys and meanings.
- `config/`, display/input/audio services and `data/` retain calibration,
  scheduling, Windows Beep output, serialization, lifecycle and provenance.
- `_reference_csf/`, including `packages.zip`, remains scientifically necessary.
  The archive is an actual legacy runtime dependency, not a redundant source
  backup. Its bundled Pyglet/import-order and physical parity limitations remain
  documented; it was not silently replaced by the installed Pyglet or a raster.
- `experiments/_internal/library_builder.py` and the old design JSON interpret existing
  saved designs and support compatibility/parity tests. They are not the new
  built-in above/below procedure or the normal authoring UI.
- Specialized calibration/readiness/data/analysis documents remain distinct
  operational or scientific references. Dated audit records retain historical
  filesystem mentions; those are not current imports or installation directions.

The matched flanker files intentionally repeat readable scientific policy so
each can be inspected independently. Display, input, rendering primitives,
adaptive algorithms, audio and file-writing mechanisms were not duplicated.

## Files and directories removed or relocated

| Path | Reason |
|---|---|
| `src/psychophysics_lab/experiments/flanker_protocol.py` | Removed the scientific-policy hub after moving policy to the three experiment owners and demonstrating frozen software-trace equivalence. |
| `src/psychophysics_lab/ui/library_builder.py` | Unused and unmounted alternative-authoring widget; import/reference searches and TUI tests confirmed it was not needed. |
| `examples/minimal_experiment.py` | Relocated to `tests/_legacy_adapter_fixture.py`. It exercises the four-path bridge; presenting it as a researcher authoring example conflicted with the agreed architecture. Both consuming regression suites remain. |
| `docs/START_HERE_EXPERIMENTS.md`, `docs/RESEARCHER_QUICKSTART.md`, `docs/TEACHING_GUIDE.md` | Duplicate short directions to the same beginner guide; current links now lead directly to LEARN_PSYCOLAB.md. |
| `docs/STIMULUS_LIBRARY_EXPERIMENT_BUILDER.md` | Superseded alternative-authoring description; compatibility rationale is in the current contract and this report. |
| `docs/EXPERIMENT_AUTHORING_PROPOSAL.md`, `docs/history/EXPERIMENT_AUTHORING_PROPOSAL_OLD.md` | Superseded proposal and its redirect; current architecture replaces them and Git retains their history. |
| `docs/history/2026-09-15-overlay/OVERLAY_MANIFEST.txt`, `PSYCOLAB_UPDATE_NOTES.md`, `README.md` | Obsolete overlay instructions, verified unchanged and recoverable from Git before removal. The empty history directories were then removed. |
| Local `Events/`, `Experiments/`, `Functions/`, `Interface/` remnants | Contained only ignored `.pyc` files under `__pycache__`. Absolute paths and contents were verified before removing these retired-directory caches. No participant or uncommitted source files were deleted. |

Current source imports, configuration and active documentation links were checked
after removal. Historical audit inventories and the fixture-capture script may
name old paths explicitly as historical records, not runtime dependencies.

## Bugs fixed

1. **Ready publication crashed after a successful test.** The adaptive-dependency
   loop iterated a pair instead of a sequence of pairs. Corrected it and tested
   successful publication with/without adaptation, stale-source rejection and
   rejection of an untested adaptive dependency. The real researcher experiment
   completed `--dev-test`, then `--dev-ready` successfully.
2. **Researcher probe instructions ignored remapped keys.** They always displayed
   F/J while input used the configured mapping. Instructions now use the actual
   response keys; target indices and scientific meanings remain unchanged.
3. **Reference CSF looked in the wrong configuration directory after relocation.**
   Its package-relative JSON lookup could fail on physical launch. Its unchanged
   five-phase contract now comes directly from `trial_timeline()` in the
   experiment file, eliminating the erroneous lookup and an external policy owner.
4. **Windows launcher discarded CLI arguments.** It launched the TUI even for
   `--list-experiments`. Arguments now reach the application. An isolated Windows
   regression verifies a quoted argument containing spaces, and the actual
   launcher catalogue command exits successfully.
5. **Developer storyboards could replay a retired orientation JSON sequence.**
   Python procedures no longer generate an illustrative storyboard from an old
   JSON plan. Executed actions remain the scientific record; a regression prevents
   the stale preview path.
6. **Experiment authoring required a separate list and compulsory settings file.**
   Added small discovery to the existing atomic loader, removed the unconditional
   companion requirement, and tested that managed drafts remain gated. Direct
   imports of flanker definitions also resolve their built-in adaptive mechanism.

## Validation and reproducibility

**Complete final Windows suite: 943 passed, 1 expected mocked-loader warning, 200.59 seconds.**
The warning comes from the test that intentionally substitutes a mismatched
component SPEC while exercising atomic registry loading; it is not a failed run.
The full run includes the two new storyboard/Windows-launcher regressions.
No test was removed to obtain this result.

| Check | Result |
|---|---|
| Original baseline on this Windows PC | 923 passed, 1 failed. Failure was only the retired-root bytecode cache directories; those were inspected and cleaned. An initial run with temporary calibration folders inside the source tree was discarded and rerun with the suite's required external temp locations. |
| Architectural acceptance regressions | 19 passed, including the actual Windows batch forwarding test, fixture equivalence, Python-only discovery/staging, Ready gating, phase parity and remapped-key instructions. |
| Full scientific flanker traces | All three match fixtures captured from starting commit `651b928…`: canonical trial rows, full normalized action-trace SHA-256 and complete final adaptive snapshots. Only relocated callback module qualifications are normalized. `scripts/capture_procedure_reference.py` reproduces the original-commit capture. |
| Reference CSF action replay | initial_one_down: 20 responses; response_ceiling: 5; reversal_completion: 17. Exact adaptive snapshots and numeric agreement within 1e-12. Authoritative shader identity tests remain intact. |
| Virtual output validation | All nine discovered experiments ran; all 18 checks passed for every run (162 successful checks). Nonadaptive tasks completed four responses each. Adaptive CSF and flanker smoke runs correctly reported their accepted-response ceiling. |
| Stimulus previews | All 14 raster-capable stimuli rendered; montage visually inspected. Hardware-specific CSF/diagnostic renderers deliberately received no substitute raster. |
| TUI | Full suite exercises source inspection/editor fallback, navigation, calibration/configuration, presets, review, virtual launch, lifecycle and small-screen layouts using Textual's headless driver. |
| Windows launcher and CLI | Real launcher `--list-experiments`, normal catalogue/help, developer simulation/Ready and CSF replay exercised. The aborted pre-fix launcher smoke exposed argument loss; no physical experiment was run. |
| Static/portability/dependencies | Python compilation, `scripts/portability_check.py`, `git diff --check` and `pip check` passed. No repository lint tool is configured; no claim of an unrun linter. |
| GitHub Actions | Existing Python 3.11 Windows/Ubuntu matrix retained. Remote CI was not run because this branch was not pushed and the user reserves pushing/merging. |

Portable smoke results are in
[`final_verification_2026-10-17.json`](audit_evidence/final_verification_2026-10-17.json).
Detailed logs, the visually inspected montage, CSF replay records and the local
temporary virtual-data location are under `.psycolab_logs/researcher-audit*`.
Synthetic folders are reserved/marked and were not mixed with human records.

## Remaining scientific and hardware limits

Base, Indirect Flanker and Ellipse 2D remain explicitly development-only and
blocked for human acquisition. Missing ellipse conditions/decision content must
be supplied explicitly; historical alpha/shader/audio/RNG and delayed-termination
equivalence remain unproven. A matching software trace preserves the existing
reconstruction; it does not validate that reconstruction against participants or
physical historical stimuli.

CSF simulation reuses the retained response handler/adaptive session but
substitutes positions, response delivery and virtual time. It does not run the
physical phase queue. The internal driver remains necessary until shader,
geometry, event, photometric and timing equivalence is demonstrated. No measured
display, keyboard latency, acoustic onset or perceptual equivalence was established
by these software tests. Existing calibration and acquisition blocks remain.

Dependency versions, archive import order, resolution/monitor binding and
photometric/timing qualification still require laboratory review on the intended
display. Automatic previews and simulations are not substitutes for that review.

## Final local status

Branch `audit/researcher-facing-procedures`; HEAD and `main` remain
`651b928371dc577717dbef96acdaa9c292d02c1a`.

`git diff --shortstat` (tracked paths): **55 files changed, 1842 insertions(+), 798 deletions(-)**.
There are **9 new untracked files**, including the new Python experiment,
regression fixtures/tests, capture script and audit artifacts; **64 changed paths total**.
Tracked deletions include the example relocated into a new test fixture.
All changes are unstaged and available for local review.

The per-file inventory supplies the full retained/removed list and rationale.
There are no staged changes, commits, pushes or merges from this audit.
