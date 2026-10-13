# PsyCoLab repository and experiment audit — 13 October 2026

## Outcome and scope

The calibration-to-experiment exclusion is reproduced and corrected. Available profiles now remain selectable even when unqualified. Configuration, shared Review and both virtual-observer launch paths retain the selected profile; human acquisition applies separate qualification and presentation checks. Changing display within configuration preserves the draft. Review hashes are checked against disk through scenario dispatch and each seed.

**Human production readiness: not established.** Software and GPU tests cannot supply optical or temporal evidence. In particular, the retained contrast protocol can exceed the shader's digital range, and synchronous feedback affects timing. The new conservative guard rejects unsafe human presentations rather than changing the scientific protocol. Human acquisition defaults were not changed: a previously accepted starting intensity may now be rejected for documented clipping risk.

**Pilot readiness:** ready for headless pipeline testing. A controlled human pilot is conditional on completing the hardware checklist, choosing a reviewed safe contrast configuration, and declaring laboratory qualification for the selected profile. The observed 44 mm ruler result alone does not authorize a human experiment or certify cpd/photometry/timing.

Baseline: clean local `main`, `6002235316ba3eac333fb34611925026be6dfd6f`, PR #13 merged. Branch: `fix/calibration-experiment-pipeline-audit`. No historical participant files, saved local profiles or prior simulation runs were edited. Test configuration and generated runs used fresh isolated temporary directories, including a synthetic/shared-root sentinel test. The actual local profile was inspected read-only.

The inventory covers the complete tracked Python source tree, legacy `Events/`, `Experiments/`, `Functions/`, `Interface/`, `libC.py`, launch scripts, registries, data/analysis and simulations. Deep behavioural checks focus on acquisition, geometry, recording and the reported workflow. This is a software/scientific-risk audit, not a formal proof of every unused legacy helper. See [control inventory](TUI_CONTROL_INVENTORY_2026-10-13.md) and [source/dependency inventory](audit_evidence/source_inventory.json).

## Evidence and validation

- Initial `pip check`: no broken requirements.
- Initial unchanged suite: stopped after three TUI initialization failures (375 passed before stop). A later full run reproduced blank/unmounted widgets and measuring a zero-sized pre-mount navigation region. Tests now await the relevant mount boundary. Queued selection messages during shutdown also caused a real `IndexError`; handlers now ignore the empty screen stack.
- **Final result: 490 passed in 142.74 seconds on Windows**; commands and evidence are recorded in `audit_evidence/test_results.txt`. The full suite includes fault injection, independent staircases/initial 1-down, canonical recorder/validator, portability, synthetic separation, condition conversion and TUI navigation tests.
- Exact reported workflow is covered at 80×24, 100×30 and 140×48 by `test_exact_local_profile_calibrate_configure_review_virtual_restart_flow`: save draft revision 1, bind revision 2, fixture fullscreen 5° bar, 44 mm ruler entry, select local profile, configure 2/4/8 cpd with two staircases per condition, Review, virtual run, snapshots, validate and restart. Fixture measurements are explicitly test evidence, not new laboratory observations.
- Windows read-only preflight succeeded for the user's existing local profile: 340×210 mm, 0.5 m, 1536×960 OS pixels, **59 Hz** reported and saved at audit time (the request described 60 Hz). It found the explicitly bound OS display. These are saved/manual and OS values, not independent physical measurements.
- Real Windows GPU probe: Intel UHD Graphics, OpenGL 4.6.0 build 32.0.101.7088. The actual production shader compiled/linked and drew six cases (cpd/legacy × horizontal/vertical/oblique) in an invisible 256×256 window. RGB readback matched independent CPU expectations with maximum error <0.0021, within tolerance 2/255. Non-square x/y pitch and an off-centre stimulus were exercised. Probe geometry/envelope were diagnostic inputs; no fullscreen, display-mode change, human acquisition or photometer was used. [Raw result](audit_evidence/shader_probe.json).
- `portability_check.py` and `git diff --check` passed. Windows and Ubuntu headless CI jobs are declared; results of future CI are separate from the local Windows run.

## Prioritized findings

### A01 — P0 — Confirmed defect: calibrated local display hidden from Experiment and scenarios (fixed)

**Files/functions:** `config/preflight.compatible`, `ui/setup._compatible_profiles`, `reload_profiles`, root Configure handler; `ui/simulations.compose/_request`; `simulations/scenarios/run.run_scenario`; `core/runner.run_request`.

**Reproduce/root cause:** save a local geometry profile and bind it; geometry/binding edits clear `qualified_experiments`. CSF lists only the reference ID. A qualification predicate was used to remove the local profile from every normal selector, then choose the reference. Active local preferences were correctly saved but could not overcome the filter.

**Consequence:** configuration refers to the wrong physical assumptions or a valid headless test is blocked. This prevents the requested pipeline and could lead a researcher to use an unintended reference geometry.

**Correction:** availability includes all registered profiles. `validate_setup(mode=configuration|simulation|human)` separates checks. Configuration/simulation still validate numeric values, physical-frequency feasibility when resolution is known, calibration-pair consistency and reviewed hashes. Human mode additionally requires the retained explicit qualification policy, a bound local monitor, expected cpd resolution and a safe starting digital range. Selection never creates verification or qualification.

**Evidence/acceptance:** exact 12-step regression and current-revision readiness fixture; local ID, 340×210 mm, 0.5 m and revision 2 remain in all new synthetic artifacts. No monitor-ID special case was added. **Approval:** none for the workflow correction; laboratory approval remains necessary to qualify a human protocol.

### A02 — P1 — Confirmed defect: final virtual launch lost reviewed profile hash (fixed)

**Files/functions:** `core/simulation_request.SimulationLaunchRequest`, `ui/unified_run._launch_request`, advanced simulation Review, `app._main`, `simulations/run.simulate`, scenario runner.

**Reproduce:** open Review, save a new profile revision, then launch a virtual observer; the old UI request's profile ID was passed without its hash. A later disk revision could be loaded unnoticed, particularly across seeds.

**Correction:** handoff includes the reviewed hash. Unified and advanced launch reread disk. Scenario entry validates before running and pins the initial hash for every seed. Each run still owns its immutable snapshot; later changes do not overwrite prior artifacts. A mid-sweep profile edit rejects subsequent seeds while preserving completed runs; no rollback of acquisition is attempted.

**Acceptance/test:** stale Review/dispatch rejection, hash/snapshot equality, existing human profile hash tests. **Approval:** none.

### A03 — P1 — Usability issue: changing display discards context; calibration restart loses draft (fixed)

**Files:** `ui/setup.ExperimentConfigScreen`, `ChangeDisplayScreen`, `DisplayCheckScreen`, root composition, `config/local.preferences`.

**Reproduce:** enter conditions, navigate globally to Calibrate, return to root; profile selection and fields are separated and the prior configuration screen is gone. A fullscreen diagnostic closes Textual and loses in-memory drafts.

**Correction:** `Change display / Calibrate` opens a reversible picker with all profiles, readiness and Refresh. Apply keeps raw experiment values and requires Review against the newly selected profile. Cancel retains the prior selection. The dedicated workflow persists a local draft plus active-profile preference, so a fullscreen restart can restore it when Configure is reopened. Saved calibration revisions persist independently of Cancel; the wording makes this explicit.

**Acceptance/test:** Cancel/Apply, preserved condition list/count, small terminal, local draft readback and profile restart tests. **Limit:** arbitrary unsaved edits outside this dedicated calibration workflow remain session drafts; they do not automatically become presets. **Approval:** none.

### A04 — P1 — Confirmed defect: missing requested profile could fall back silently (fixed)

**Files:** root `compose`, `_refresh_experiment_context`, `_refresh_monitor_context`, Configure handler.

**Reproduce:** active local-profile preference points to a missing/corrupt profile. Loader warns and excludes it; previous root logic selected the first reference.

**Correction:** show an unavailable saved-profile option and actionable restore/reload message. Configure refuses it until the researcher explicitly selects another valid profile. Valid unqualified profiles remain available. **Test:** unavailable preference regression. **Approval:** none.

### A05 — P1 — Usability/interpretation defect: ruler report for old revision looks current (fixed)

**Files:** `core/geometry_check.latest_geometry_report`, `ui/setup.DisplayCheckScreen` preview/record handler, new `config/readiness`.

**Reproduce:** measure revision 2, save revision 3 with a changed viewing distance. Lookup is by profile ID alone.

**Correction:** status includes current/stale revision/hash; UI prevents recording a new measurement as if a stale report represented the selected profile. Readiness looks for a completed measured report matching the exact content hash. It records evidence/error without automatically declaring geometry verified. **Tests:** exact revision match and stale measurement rejection. **Approval:** none.

### S01 — P1 — Scientific risk/confirmed digital-range defect: contrast may clip (guarded; protocol decision remains)

**Files/functions:** `Events/display_contrast`, `adaptiveMethods._update_probe_weber_contrast/_weber_contrast_to_cpu_intensity`, `Events/stimuliC.Grating_ADM.draw/frag_source`, `stimuli/contrast_validation`, human preflight.

**Numerical reproduction:** `C_disp=(I_n-I_b)/(1-I_b)`. The production `box=False` branch draws `RGB=I_b+m*C_disp*sin(phase)/2`, not `I_n`. At I_b=.374 and starting I_n=1, C_disp=1; envelope maximum 1 gives the conservative interval [-.126,.874]. At a trough in the configured grating, negative values can occur and be saturated by the framebuffer. One .35-log10 up step gives C_disp≈2.23872 and surrogate I_n≈1.77544. The lower-bound conversion never supplies a corresponding upper presentation guarantee. Recorded I_n is an adaptive surrogate; it must not be called the actual fragment luminance.

**Correction:** conservative human preflight/draw rejection, no clamping and no staircase/default change. With background .374, a sufficient safe bound is C_disp≤.748, corresponding to surrogate I_n≤.842248. This is a digital-range bound, **not** a recommendation for a scientific threshold protocol. A later unsafe update is recorded normally, but its subsequent presentation is stopped and the run finalizes as error; accepted responses survive.

**Evidence/tests:** numeric bounds/inverse, mode-specific validation, GPU readback; probe does not measure physical contrast. **Open decision:** approve an experiment-owned ceiling/termination policy, alternative starting contrast, calibrated modulation definition and any corresponding estimator changes. Human approval required before changing those protocols. The conservative guard may reject a mathematically in-range finite patch whose envelope never reaches its global bound; this tradeoff is explicit.

### S02 — P1 — Scientific risk: digital contrast is not Weber/Michelson luminance contrast (open)

**Files:** shader `box` branches, `_validate_monitor`, profile calibration model, deferred stimulus review.

**Reproduce:** compare saved physical background/max luminance entries to the shader formula. `box=False` uses digital commands; `box=True` uses different gamma/channel encoding, with experimental parameters including gamma=0 and a `BRTRR` key different from shader `BTRR`. The normal CSF path keeps `box=False`.

**Consequence:** a background/end-point table and a verified flag alone do not calibrate the full grating modulation, gamma, clipping or device channel mapping. The Gaussian envelope also makes spatial contrast vary across the patch.

**Recommendation/acceptance:** photometer measurements across the actual command range, calibrated modulation and envelope definitions, device-specific validation before enabling alternate `box` mode. New resolved metadata explains the active digital formula. No gamma/contrast/envelope rewrite. **Test status:** digital formula tested; physical luminance unmeasured. **Approval:** required for scientific changes.

### S03 — P1 — Scientific risk: feedback and file IO perturb event-loop timing (open)

**Files:** `adaptiveMethods._beep/subject_response/state_new_condition_for_stimulus`, `libC.ExpWindow.on_draw_idle/on_draw_trial`, trial file IO.

**Reproduce:** each accepted response calls Windows Beep for 500 ms; new-condition entry beeps for `timeInterval`. Calls occur synchronously on the event-loop path, before canonical recording or before the phase deadline is set. The Windows API documents that it waits until sound completion. [Microsoft Beep reference](https://learn.microsoft.com/en-us/windows/win32/api/utilapiset/nf-utilapiset-beep).

**Consequence:** nominal timings exclude parts of feedback/IO delay; frames/input dispatch can pause. The engine uses `time.time()` deadlines, draws a phase before checking its expiry, and transitions on later draw calls. Setting refresh/callback frequency cannot prove stimulus-onset accuracy. All four configured phase timing values are used; interval is used in two separate phases, with a further new-condition feedback delay. Finite response timeouts can finish the queue with fewer accepted responses and result in an abort rather than max-responses completion.

**Recommendation:** instrument actual onset/offset with a photodiode, record software event durations, decide whether audio belongs within the scientific interval, then review an asynchronous feedback/monotonic-clock/frame-scheduling change. No timing protocol changed here. **Tests:** mapping/lifecycle tests pass; no physical latency measurement. **Approval:** required before altering timing/feedback behaviour.

### S04 — P1 — Scientific risk: panel/framebuffer aspect mismatch and square pixel quad (open)

**Files:** `stimuli/geometry`, `spatial_calibration`, `display_tests`, production renderer.

**Evidence:** fixture 340/210=1.61905 versus 1536/960=1.6 gives ≈1.19% unequal x/y pitch. This may reflect approximate ruler measurements, logical pixels/DPI, or real image mapping. OS preflight reports pixels; it cannot distinguish these causes physically. cpd shader evaluates independent axis pitch and per-fragment atan; actual square-pixel grating width still comes from the horizontal 5° extent, so vertical physical extent can differ. Fixed 5° eccentricity uses d*tan(theta), while centred size uses 2*d*tan(theta/2).

**Correction status:** formulas checked; cpd/legacy production shader GPU readback succeeded at non-square pitch and off-centre position. Nonfinite orientation is rejected rather than bypassing the sampling check. No resizing/geometry reinterpretation was silently applied.

**Acceptance:** horizontal/vertical multiple-size and off-axis ruler measurements, actual framebuffer/DPI check, known cpd pattern measurement. See hardware document for tolerances and uncertainty. **Approval:** needed for changes to physical shape, eccentricity or stimulus extent.

### A06 — P2 — Confirmed interpretation defect: unit help and scenario/analysis labels stale (fixed)

**Files:** configuration condition help; CSF parser messages; `simulations/scenarios/csf.evaluate_csf`; `analysis/thresholds._plot/analyse_thresholds`; Data run summary.

**Reproduce:** select cpd or degrees/cycle while configuration says all values are legacy scalars; run cpd scenario and read evaluator's hard-coded legacy-unit claim; inspect generic Condition axis.

**Correction:** dynamic help distinguishes cpd, period and explicit legacy modes. Trials in period mode are canonical reciprocal cpd. Scenario units and analysis labels derive from the run snapshot, never current registry defaults. Historical missing-unit runs remain uncalibrated legacy. Data inspection shows profile revision and hash. **Tests:** unit-switch help, condition conversion, scenario cpd labels and legacy analysis checks. **Approval:** none; raw values and historical files untouched.

### A07 — P1 — Confirmed interpretation defect: incomplete estimate visually lacks quality warning (fixed)

**Files:** threshold plotting and derived summaries.

**Reproduce:** response ceiling ends an unfinished staircase but an ordinary-looking threshold figure is generated. JSON already marks incomplete status; exported image can lose that context. Staircases with no reversals are omitted without an explicit list of missing estimates.

**Correction:** figures identify synthetic data and incomplete/censored runs; summaries record missing staircase estimates from saved adaptive identities. No absent threshold is invented. Last-N/fraction and presented/next choices remain independent versioned derived analyses; no acquisition estimator change. **Tests:** short runs, censored summaries and missing-estimate test. **Approval:** none.

### E01 — P2 — Confirmed reliability issue: TUI events during shutdown and tests before mount (fixed)

**Files:** root reactive handlers; simulation and navigation integration tests.

**Evidence:** zero-sized pre-mount region and transient blank select reproduced; diagnostic tracing showed `_value=contrast_sensitivity` while the widget was not mounted, followed by normal selection on mount. A queued profile Select message after the app had popped its screen stack caused `IndexError`.

**Correction:** ignore shutdown messages and transient blank scenario events; integration tests wait for the meaningful mount boundary. No replacement of valid values merely to satisfy tests. **Acceptance:** full suite and small-size flow tests. **Approval:** none.

### E02 — P1 — Regression risk: multi-file accepted-response update is not transactional (open)

**Files:** `adaptiveMethods.subject_response`, `adaptive_session.logger`, `TrialLog`, runner finalization.

**Trace:** accepted event → correctness/feedback → in-memory adaptive update → conditions JSON rewrite → legacy response rewrite → canonical append/fsync → adaptive snapshot → termination. A failure after one write can leave artifacts disagreeing; later canonical rows are not invented. Logger stops acquisition and attempts error-state saving, and runner preserves primary/cleanup errors. Validator detects mismatches.

**Recommendation:** reviewed transaction/recovery journal design; canonical-first event sourcing is a separate migration because compatibility files currently participate in live drawing. Do not auto-repair historical runs. Existing disk-failure/lifecycle tests exercise stop/error semantics, not complete atomicity across files. **Approval:** needed for a data-contract migration; no new recovery applied.

### E03 — P2 — Regression risk: current validator uses current dictionary definitions (open)

**Files:** `scripts/validate_run.dictionary_check`, registry trial overrides.

**Reproduce:** validate historical schema-1 runs after changing the registry's text definitions; checks compare their saved dictionary to today's definition. This can reject an internally consistent historical run without proving its raw data were wrong.

**Recommendation:** pin dictionary/schema definitions by source version or validate saved definitions/hashes independently. Current raw schema and dictionary text were left intact in this audit. Use the acquisition checkout when validating older runs until a versioned validator is reviewed. **Tests:** current finalized records pass; historical compatibility beyond fixtures remains open. **Approval:** required for changing validation/data interpretation contract.

### E04 — P2 — Engineering/dependency risk: bundled archive and old graphics stack (documented)

**Files:** `packages.zip`, `libC.py`, packaging/launcher, CI.

**Evidence:** archive inventory and hashes are saved without extraction/execution of archive tools. A source checkout remains necessary. Python 3.11, NumPy 1.26.4 and Pyglet 1.5.27 are deliberate compatibility pins; `pip check` verifies installed requirements, not archive licensing/provenance or graphics validity.

**Correction:** portability now scans simulation runtime sources. CI includes Windows and Ubuntu headless jobs. Added an explicit real production-shader probe separate from CI. **Open:** the archive has 233 entries under bundled `pyglet` and `wmi.py`, with no license/copyright-named entries found. This does not establish licensing status; dependency origin, version and licensing need explicit review. Archive minimization and modernization require equivalence tests. No dependency upgrade or archive replacement. **Approval:** normal reviewed engineering follow-up; scientific approval if rendering/timing changes.

### E05 — P2 — Deferred improvement: authoring, concurrency and lifecycle boundaries

Registries explicitly reject duplicate IDs and load listed contributor modules atomically; scaffolds refuse existing paths. `RunContext` is a useful minimal bridge but does not enforce a universal scientific trial procedure. Simulation-specific models/evaluators remain separate. Local run allocation uses exclusive mkdir, and profile/index writes use advisory locks. `_legacy_runtime_context` changes process-wide cwd/import paths and synthetic output redirection changes global stdout; concurrent acquisition threads in one process are not supported. Independent processes on local filesystems are the tested model; cloud-sync locks are not a distributed guarantee. No speculative framework rewrite.

Acceptance: keep separate processes for simultaneous studies; design experiment-specific lifecycle/preview hooks before a builder. [Authoring proposal](EXPERIMENT_AUTHORING_PROPOSAL.md). Approval: separate follow-up review, not part of this patch.

### E06 — P2 — Confirmed failure-report limitation and extreme-observer risk (open)

**Files/functions:** `simulations/scenarios/run.run_scenario`, `simulations/scenarios/csf.evaluate_csf`, outer application exception handling.

**Reproduce/root cause:** inject an exception into a scenario runtime or analysis/evaluator after a run has been allocated. The runner saves its canonical error manifest where possible, but the scenario loop propagates the exception before writing the aggregate `scenario_report.json`. A very narrow observer tuning width can also make `threshold*exp(0.5*offset²)` overflow in the evaluator even though the acquisition probability is computed safely in log space.

**Consequence:** surviving canonical data and local crash diagnostics remain, but the usual scenario report may be absent; this is not a successful scenario. Earlier completed seeds must not be discarded or rerun automatically. Standalone `simulate()` has run provenance/analysis but does not promise an aggregate named-scenario report.

**Recommendation/acceptance:** a separate failure-report finalizer owning only newly allocated run paths, with fault-injection tests for runtime, analysis, evaluator and disk failure; explicitly report unrepresentable model ground truth without fabricating a finite value. Preserve numerical comparison formula until its scientific reporting convention is reviewed. **Status:** error preservation is covered by existing simulation/runner tests; aggregate failure reports and extreme evaluator coverage remain open. **Approval:** engineering correction can be reviewed separately; changes to model interpretation require scientific review.

## Adaptive, acquisition and scientific contracts retained

Conditions/count and staircases-per-condition are validated before configuration. Each identity owns streaks, reversals, introductory phase and stopping state. Initial 1-down exits after its own first incorrect response or accepted-response limit; that first wrong response follows n-up. Flat updated values do not count reversals; the first recorded post-update value seeds reversal history. The accepted-response ceiling remains global. Review warns when the budget cannot service all staircases or is below the indicative completion budget. The latter warning is not a guaranteed statistical completion forecast.

Correctness remains spatial left=0/right=1; only LEFT/RIGHT are acquisition response keys, even though historical helpers retain aliases. Escape records `aborted_by_user` without inventing a response. Recording errors stop the queue, and cleanup preserves the original failure. Introductory defaults, step magnitudes, reversal convention, legacy shader radians, cpd formula, Gaussian envelope and trial data hierarchy were not changed.

Step-size ratios are conditional literature settings, not n-down/n-up count ratios. Finite-step bias depends on more than the counts; a CSF observer midpoint is not guaranteed to equal the reversal estimator's target. See [García-Pérez's study](https://pubmed.ncbi.nlm.nih.gov/9797963/) and `docs/ADAPTIVE_METHODS.md`. No recalculation or scientific target is silently substituted.

## End-to-end acceptance matrix

| Stage | Expected result | Automated evidence | Windows manual check / artifact |
|---|---|---|---|
| Save/reopen/bind | Versioned local profile; no reference overwrite | profile persistence and exact regression | saved ID/revision, active dimensions and monitor identity |
| Diagnose/measure | Result and uncertainty attached to exact revision | fixture report/hash and stale-check tests | horizontal/vertical rulers, `geometry_check.json` |
| Configure | all profiles visible; conditions/count and units agree | local-profile flow at three sizes | change display without losing fields |
| Review | same geometry/hash; qualification separate | stale Review/dispatch rejection | displayed ID/revision, ppd, reasons and safe starting contrast |
| Human preflight | qualification, binding, resolution and digital range checked | validators, display-missing/mode tests, RGB guard | explicit target monitor and actual framebuffer |
| Production renderer | cpd/legacy GLSL executes and matches numeric model | six Windows GPU readbacks | known cpd patterns, size/eccentricity, physical luminance |
| Responses/termination | accepted records only; independent staircases; clear end state | adaptive/session/lifecycle/fault tests | LEFT/RIGHT, Escape, timeout, completion vs ceiling |
| Virtual acquisition | identical configured scientific parameters; model/seeds separate | exact local-profile scenario; seeded/multi-condition tests | synthetic marker, deterministic virtual clock, no hardware claim |
| Canonical data | snapshots, context, raw trials and hashes consistent | `validate_run`, durability and error tests | inspect manifest/config/revision and source hashes |
| Analysis | units from snapshot; explicit censored/synthetic warning | legacy/cpd/missing-estimate tests | inspect PNG and versioned summary with chosen estimator |
| Restart/Cancel | saved changes persist; canceled selection does not apply | preference/draft and Cancel/Apply tests | restart after calibration; reopen Configure |
| Missing/stale/invalid | actionable rejection; no silent fallback or raw repair | missing requested profile, invalid frequency/contrast tests | disconnect/mode change using a test profile only |

## Windows procedure and next decisions

Follow [WINDOWS_HARDWARE_ACCEPTANCE.md](WINDOWS_HARDWARE_ACCEPTANCE.md). Return the completed observation table with the selected profile UUID/revision/hash, measuring equipment and uncertainty. Physical measurements, calibrated stimulus contrast, feedback/timing policy and a lab-specific qualification decision remain necessary. No measurement status was promoted by software during this audit.
