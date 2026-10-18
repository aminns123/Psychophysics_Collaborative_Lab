# PsyCoLab: International Manual Validation Handbook

**Version:** 1.0 | **GitHub baseline:** `ceda463b5cd5b6a6bf47c711ba3da8c22b888f04` | **83 manual acceptance cases** | **Date:** 18 October 2026

This is a printable and GitHub-readable acceptance plan for laboratory operators, scientific protocol owners, developers and independent sites.

> **Safety and scientific scope:** Passing software tests does not establish physical luminance, effective contrast precision, native panel depth, photon onset/offset, acoustic latency, experiment equivalence or scientific hypothesis validity. Green calibration pages reflect saved setup progress, not automatic physical verification. Do not use test photometry to qualify human acquisition.

## How to use this plan

1. Record the exact commit, monitor-profile revision/hash, operating system, driver, instruments and responsible people.
2. Protect real participant data. Use only fresh disposable test folders for corruption and abort cases.
3. Carry out routine software checks, then laboratory equipment checks and cross-site comparisons when possible.
4. For each case record PASS, FAIL, BLOCKED, NOT RUN or N/A, including evidence and the reviewer.
5. **Do not** infer human-study readiness from passing CI or uncalibrated presentation mode.

**Tiers:** R = routine software/digital checks; L = laboratory instrumental checks; X = cross-site deployment or equivalence checks. Laboratory tolerances must be preapproved and based on measurement uncertainty.

**Seven-stage calibration:** Display -> Geometry -> Spatial -> Luminance -> Output precision -> Timing -> Review.

**Critical Windows repeat-run check:** Execute E01, E02, E03 and T06 on actual GPU/monitor following the OpenGL invalid-enumerant failure. Confirm three launches in one process, A-B-A settings, abort-and-reopen and independent saved runs.

## 01 | Release identity and data protection

### R01 | Identify exact checkout and revision

**Tier:** R - ROUTINE

**Procedure:** Run git status, git rev-parse HEAD; record Python, NumPy, Pyglet, Textual, OS, GPU and driver.

**Pass if:** Commit and local environment are unambiguous.

**Evidence to save:** Terminal transcript and version sheet.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### R02 | Safeguard configuration and participants

**Tier:** R - ROUTINE

**Procedure:** Identify external data root and local profile/history. Create a disposable test workspace; never modify genuine participant data.

**Pass if:** Source, profiles and acquisition data remain intact.

**Evidence to save:** Before/after path inventory.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### R03 | Dependency health

**Tier:** R - ROUTINE

**Procedure:** Run project python -m pip check and python scripts/portability_check.py without changing pinned graphics packages.

**Pass if:** No unresolved dependency or portability errors.

**Evidence to save:** Interpreter path and complete logs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### R04 | Full local regression suite

**Tier:** R - ROUTINE

**Procedure:** Use a fresh pytest basetemp outside repo; run python -m pytest -q and save all warnings.

**Pass if:** Suite passes; each skip/warning explained.

**Evidence to save:** Log, counts and duration.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### R05 | Cross-platform CI

**Tier:** R - ROUTINE

**Procedure:** Inspect exact commit's Windows and Ubuntu CI and portability checks.

**Pass if:** Both platforms have traceable results; physical validation is not inferred.

**Evidence to save:** Run URL, timestamp, job results.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### R06 | Test statuses and owners

**Tier:** R - ROUTINE

**Procedure:** Agree PASS/FAIL/BLOCKED/NOT RUN/N/A; allocate study owner, hardware tester and maintainer.

**Pass if:** No unowned cases or unreasoned N/A; evidence required for PASS.

**Evidence to save:** Master test register.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 02 | Installation, launch and portability

### I01 | Clean Windows installation

**Tier:** R - ROUTINE

**Procedure:** Clone to a fresh path; double-click run_psycolab.bat; quit and relaunch.

**Pass if:** Environment and TUI start with documented steps.

**Evidence to save:** Launcher log and interpreter version.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### I02 | CLI forwarding

**Tier:** R - ROUTINE

**Procedure:** Try python -m psychophysics_lab --help, --list-experiments and launcher CLI arguments.

**Pass if:** Arguments reach CLI; no unsolicited TUI startup.

**Evidence to save:** Command exit codes and output.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### I03 | Startup after exits

**Tier:** R - ROUTINE

**Procedure:** Reopen after normal exit, Escape and window close on disposable tests.

**Pass if:** No stale processes, locked windows or persistent crash.

**Evidence to save:** Process inventory and session notes.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### I04 | Missing or invalid user settings

**Tier:** R - ROUTINE

**Procedure:** In disposable copied configuration, test missing profile, malformed preferences and restored valid file.

**Pass if:** Actionable error; existing calibration untouched; recovery possible.

**Evidence to save:** Messages and config diffs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### I05 | Linux and other systems

**Tier:** R - ROUTINE

**Procedure:** Try catalogue, TUI and synthetic mode on a supported alternate system.

**Pass if:** Software-only tasks run or explicit platform limits are shown.

**Evidence to save:** OS versions and logs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### I06 | Multiple screens/GPU/remote

**Tier:** R - ROUTINE

**Procedure:** Test laptop dock, discrete GPU and remote environment when available.

**Pass if:** Correct physical display bound; no silent primary-monitor substitution.

**Evidence to save:** Monitor identity and GPU report.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 03 | TUI, experiment configuration and authoring

### U01 | TUI navigation and dimensions

**Tier:** R - ROUTINE

**Procedure:** Navigate pages at 80x24, 100x30 and full screen using keyboard; inspect scroll and errors.

**Pass if:** Required controls remain accessible; no overlap or broken focus.

**Evidence to save:** Screenshots.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U02 | Participant/session and task setup

**Tier:** R - ROUTINE

**Procedure:** Select disposable identity, experiment, starting settings, run intent and monitor.

**Pass if:** Selected IDs remain consistent; human/test/synthetic identities separated.

**Evidence to save:** Review snapshot.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U03 | Input and units validation

**Tier:** R - ROUTINE

**Procedure:** Try negative/zero/out-of-range and nonnumeric values, incompatible units and correction.

**Pass if:** Invalid entry rejected clearly without erasing valid draft.

**Evidence to save:** Fields and error text.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U04 | Review equals execution

**Tier:** R - ROUTINE

**Procedure:** Edit parameters/conditions/stimulus then compare Review with actual run config and normalized settings.

**Pass if:** Every material configured value and unit matches saved run.

**Evidence to save:** Review screenshot; experiment_config.json.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U05 | Presets round-trip

**Tier:** R - ROUTINE

**Procedure:** Save, reopen, update and attempt duplicate or malformed preset.

**Pass if:** Preset values persist; monitor geometry and unrelated settings unaffected.

**Evidence to save:** Preset file and history.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U06 | Change monitor cancel/apply

**Tier:** R - ROUTINE

**Procedure:** Open calibration from config; cancel; repeat with applied local profile revision.

**Pass if:** Cancel preserves choice; Apply uses exact reviewed profile hash.

**Evidence to save:** Before/after profile IDs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U07 | Refresh and page recovery

**Tier:** R - ROUTINE

**Procedure:** Modify disposable source or a safe setting; use Refresh files then inspect resumed drafts.

**Pass if:** Fresh interpreter picks up changes and reports conflicts.

**Evidence to save:** Screenshots and logs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U08 | Single stimulus and experiment file

**Tier:** R - ROUTINE

**Procedure:** Read one class in stimulus_library.py and one public experiment file; preview disposable parameter change.

**Pass if:** Appearance and scientific timeline intelligible without auto-generation.

**Evidence to save:** Files and preview.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### U09 | Draft/Test/Ready gate

**Tier:** R - ROUTINE

**Procedure:** Alter a previously tested managed component in disposable USER_env; attempt Ready before retest.

**Pass if:** Changed fingerprint blocks publication; explicit retest needed.

**Evidence to save:** Status and source hashes.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 04 | Seven-stage calibration and monitor binding

### C01 | Seven-stage chronological navigation

**Tier:** R - ROUTINE

**Procedure:** Visit Display, Geometry, Spatial, Luminance, Output precision, Timing, Review; backtrack and resume.

**Pass if:** Saved data persists; UI never skips required evidence silently.

**Evidence to save:** Stage screenshots and local history.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### C02 | Bind intended physical display

**Tier:** R - ROUTINE

**Procedure:** Record connected physical device, illuminated width/height, distance, actual pixels, refresh and Windows scaling.

**Pass if:** Bound ID, OS mode and fullscreen dimensions agree.

**Evidence to save:** Monitor revision/hash and OS settings.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### C03 | Ruler size horizontal/vertical

**Tier:** R - ROUTINE

**Procedure:** Display centered 1,2,5,10 degree bars as fit permits, measure length physically both axes.

**Pass if:** Error within laboratory-approved tolerance accounting for pixel rounding and uncertainty.

**Evidence to save:** Expected vs observed mm.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### C04 | Off-axis placement

**Tier:** R - ROUTINE

**Procedure:** Measure bars at positive and negative eccentricity relative to fixation.

**Pass if:** Position and realized angle agree with flat-screen geometry.

**Evidence to save:** Offsets, ruler readings and photos.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### C05 | Spatial frequency observation

**Tier:** R - ROUTINE

**Procedure:** Show 2,4,8 cpd or feasible values in both orientations; count cycles, mark Yes/No/Uncertain.

**Pass if:** Reported cycle counts and units consistent; Nyquist respected.

**Evidence to save:** Observed spatial log.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### C06 | Luminance dataset provenance

**Tier:** R - ROUTINE

**Procedure:** Distinguish pilot/test vs photometer rows; accept unchanged, alter profile then confirm replacement on a copy.

**Pass if:** Old history retained; stale physical data not falsely verified.

**Evidence to save:** Version and provenance record.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### C07 | Output precision inspection

**Tier:** R - ROUTINE

**Procedure:** Inspect reported signal and GL framebuffer; optionally compare near-black and fine photometer sweeps.

**Pass if:** Unknown explicitly UNKNOWN; neither buffer depth nor readings assert native bit depth.

**Evidence to save:** Inspection JSON, meter readings.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### C08 | Timing diagnostic and final Review

**Tier:** R - ROUTINE

**Procedure:** Run timing/flicker diagnostic, inspect flip report, finish seven-stage Review and return to experiment.

**Pass if:** Completion distinct from physical Verified and human-ready qualification.

**Evidence to save:** Review/status screenshots.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 05 | Stimulus rendering and scientific visual correctness

### V01 | Preview and fullscreen agreement

**Tier:** R - ROUTINE

**Procedure:** Compare scientific preview vs actual fullscreen presentation at same settings.

**Pass if:** Intended geometry, polarity and appearance match; PNG quantization distinguished.

**Evidence to save:** Images and snapshots.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### V02 | Single-parameter changes

**Tier:** R - ROUTINE

**Procedure:** Change one size, location, contrast, orientation, frequency and background parameter per run.

**Pass if:** Only intended feature changes; saved values agree.

**Evidence to save:** A/B matrix and photos.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### V03 | Response mapping and orientation

**Tier:** R - ROUTINE

**Procedure:** Check left/right, above/below, first/second and horizontal/vertical alternatives.

**Pass if:** Visible alternative, displayed instructions and recorded correctness agree.

**Evidence to save:** Response trial logs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### V04 | Layering and scene composition

**Tier:** R - ROUTINE

**Procedure:** Show probe/flanker, fixation and annulus or ellipse combinations; observe overlap.

**Pass if:** Correct placement, layer ordering and no accidental occlusion.

**Evidence to save:** Screen captures and stimulus params.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### V05 | Digital bounds and clipping

**Tier:** R - ROUTINE

**Procedure:** Use valid near-bound and intentionally out-of-range commands in disposable testing.

**Pass if:** Out-of-range rejected without silent clipping; partial data preserved.

**Evidence to save:** Guard diagnostic and numeric bounds.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### V06 | Spatial units and eccentricity

**Tier:** R - ROUTINE

**Procedure:** Vary cpd, degrees/cycle, orientation, screen axis and near-Nyquist value.

**Pass if:** Frequency and eccentricity correct on selected measured geometry.

**Evidence to save:** Resolved frequency and geometry.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### V07 | Very low contrast behavior

**Tier:** R - ROUTINE

**Procedure:** Inspect tiny positive command differences through float stimulus preparation and fullscreen tests.

**Pass if:** Digital float values remain distinct; photometric resolution not falsely claimed.

**Evidence to save:** Command evidence and precision status.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 06 | Physical luminance and contrast qualification

### L01 | Photometer traceability

**Tier:** L - LABORATORY

**Procedure:** Record calibrated meter, integration time, room illumination, warm-up; repeat black readings.

**Pass if:** Stability, noise and instrument uncertainty documented.

**Evidence to save:** Instrument certificate and readings.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### L02 | Background and transfer curve

**Tier:** L - LABORATORY

**Procedure:** Measure background and several real screen commands repeatedly.

**Pass if:** Expected monotonic transfer and uncertainty quantified for used range.

**Evidence to save:** Raw cd/m2 curve.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### L03 | Halving near-black sweep

**Tier:** L - LABORATORY

**Procedure:** Use 1, 1/2, 1/4 to 1/65536 and zero; collect repeated readings.

**Pass if:** Near-black floor characterized; no native bit-depth inference.

**Evidence to save:** Session JSON and black drift.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### L04 | Fine adjacent command sweep

**Tier:** L - LABORATORY

**Procedure:** Test neighboring nominal 8/10-bit steps around background and other anchors, with repeats.

**Pass if:** Resolvable difference or INCONCLUSIVE justified by uncertainty.

**Evidence to save:** Fine-step readings and assessment.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### L05 | Driver/HDR/LUT/display changes

**Tier:** L - LABORATORY

**Procedure:** Change only a documented disposable video mode, re-inspect and remeasure key values.

**Pass if:** Old verification declared stale as appropriate.

**Evidence to save:** Paired setting/reading matrix.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### L06 | Actual grating modulation

**Tier:** L - LABORATORY

**Procedure:** Measure production grating peak/trough and background, not only uniform square.

**Pass if:** Weber/Michelson luminance contrast distinguished from digital command.

**Evidence to save:** Lmax, Lmin, Lbackground.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### L07 | Reference CSF physical parity

**Tier:** L - LABORATORY

**Procedure:** Compare reference shader and any new intended shared renderer for envelope, gamma, cpd, eccentricity and phase timing.

**Pass if:** No interchangeability assumed without optical and temporal parity measurements.

**Evidence to save:** Paired display traces.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 07 | Timing, input and acoustic cues

### T01 | Frame duration quantization

**Tier:** R - ROUTINE

**Procedure:** Use exact and inexact requested flicker rates at measured refresh (59/60/120/144 where possible).

**Pass if:** Frame-count plan and realized nominal timing documented.

**Evidence to save:** Hz and frame table.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### T02 | Flip intervals and dropped frames

**Tier:** R - ROUTINE

**Procedure:** Execute many repeat trials, inspect recorded software flip intervals.

**Pass if:** No unexplained missing frames by study tolerance.

**Evidence to save:** Time-series and event logs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### T03 | Photodiode photon timing

**Tier:** R - ROUTINE

**Procedure:** Record visible phase onsets/offsets/ISI with calibrated detector over many trials.

**Pass if:** Measured distributions meet study-approved jitter and duration tolerances.

**Evidence to save:** Photodiode traces.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### T04 | Response key and debouncing

**Tier:** R - ROUTINE

**Procedure:** Test accepted keys, held keys, rapid repeats and unrelated keys.

**Pass if:** Exactly one accepted response per trial; no invalid adaptive update.

**Evidence to save:** Trials.tsv and key trace.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### T05 | Late answers and timeout

**Tier:** R - ROUTINE

**Procedure:** Respond before and after response deadline; include self-paced case.

**Pass if:** Late input excluded; timeout does not fabricate a row.

**Evidence to save:** Timed phase journal.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### T06 | Escape/close safety

**Tier:** R - ROUTINE

**Procedure:** Escape before, during and after stimulus onset and immediately launch another disposable run.

**Pass if:** Abort status correct; partial data kept; window closes and reopens cleanly.

**Evidence to save:** Manifest, journal, process state.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### T07 | Windows beep playback

**Tier:** R - ROUTINE

**Procedure:** Enable optional audio and verify audible signal; test no-speaker failure when safe.

**Pass if:** Request is not mistaken for confirmed sound; failure noted.

**Evidence to save:** Audio observation/microphone.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### T08 | Sound-onset and photon-onset relation

**Tier:** R - ROUTINE

**Procedure:** Measure relevant audio-visual onset delays with instruments.

**Pass if:** Study owner reviews asynchrony and latency; no unsupported sync claim.

**Evidence to save:** Microphone + photodiode traces.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 08 | Adaptive experiments, repeat runs, lifecycle

### E01 | Three identical fullscreen launches

**Tier:** R - ROUTINE

**Procedure:** Run same settings three times from one TUI process without restart.

**Pass if:** Each window opens/closes; no GL invalid-enumerant or stale handlers.

**Evidence to save:** Run UUIDs, manifests and window log.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E02 | Changed parameter A-B-A sequence

**Tier:** R - ROUTINE

**Procedure:** Run baseline, altered settings, restored baseline without restarting.

**Pass if:** All three launch; correct visual changes; independent snapshots.

**Evidence to save:** A-B-A screenshots and IDs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E03 | Switch experiments repeatedly

**Tier:** R - ROUTINE

**Procedure:** Run two different built-in tasks then the first again in one session.

**Pass if:** Stimulus, responses and timing do not leak between tasks.

**Evidence to save:** Run and phase traces.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E04 | Condition and staircase ownership

**Tier:** R - ROUTINE

**Procedure:** Use multiple conditions, repeats and staircase selection.

**Pass if:** Saved IDs and response counts agree with declared schedule.

**Evidence to save:** Trial table and adaptive history.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E05 | Initial one-down and reversals

**Tier:** R - ROUTINE

**Procedure:** With deterministic synthetic observer manually compute response streak, reversal and adaptation.

**Pass if:** Step signs, first reversal and value basis agree with independent oracle.

**Evidence to save:** Annotated per-trial table.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E06 | Completed/ceiling/censored outcomes

**Tier:** R - ROUTINE

**Procedure:** Create completed, very short, incomplete and boundary-affected synthetic runs.

**Pass if:** Official thresholds only for fully eligible conditions; censoring visible.

**Evidence to save:** Primary results and manifest.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E07 | Experiment scientific narrative review

**Tier:** R - ROUTINE

**Procedure:** Read one experiment file and its stimulus class; explain conditions, scoring, timing, stopping, exclusions and estimator.

**Pass if:** Scientist can explain what is actually drawn and inferred.

**Evidence to save:** Signed comprehension sheet.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E08 | Human-readiness gates

**Tier:** R - ROUTINE

**Procedure:** Attempt unqualified profile/test photometry in human mode, then select test/simulation.

**Pass if:** Human acquisition safely blocked; no green setup stage upgrades test evidence.

**Evidence to save:** Readiness blockers.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### E09 | Long and repeated session stability

**Tier:** R - ROUTINE

**Procedure:** Run long disposable sequences; vary session/participant and inspect disk/memory/process usage.

**Pass if:** No overwrites, stale state or unclosed graphics resources.

**Evidence to save:** Resource metrics and run IDs.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 09 | Simulations, data products and scientific analysis

### D01 | Fixed-seed simulation reproducibility

**Tier:** R - ROUTINE

**Procedure:** Rerun a specified synthetic scenario with identical seed; compare to new seed.

**Pass if:** Identical seed reproducible; different seed traceable.

**Evidence to save:** Scenario metadata, hashes.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### D02 | Observer probability and units

**Tier:** R - ROUTINE

**Procedure:** Vary threshold, slope, lapse, preference and start strength individually.

**Pass if:** Expected qualitative/statistical effect and consistent units.

**Evidence to save:** Observer config and estimates.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### D03 | Per-run artifact completeness

**Tier:** R - ROUTINE

**Procedure:** Check manifest, trials.tsv, monitor_profile.json, experiment_config.json, runtime_display and scientific source hashes.

**Pass if:** Applicable files exist; real/test/synthetic labels consistent.

**Evidence to save:** Directory inventory.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### D04 | Canonical run validator

**Tier:** R - ROUTINE

**Procedure:** Run python scripts/validate_run.py on disposable complete run.

**Pass if:** Validation succeeds and does not modify run files.

**Evidence to save:** Validator output and SHA256.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### D05 | Official estimator parity

**Tier:** R - ROUTINE

**Procedure:** Recompute a condition from retained presented reversals, compare saved primary and post-hoc outputs.

**Pass if:** Declared geometric mean or median as applicable, across-staircase mean matches.

**Evidence to save:** Manual arithmetic vs JSON.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### D06 | Exploratory analysis isolation

**Tier:** R - ROUTINE

**Procedure:** Create last N, 80 percent and presented/next derived analyses.

**Pass if:** Versions and labels distinct; raw canonical trials byte-identical.

**Evidence to save:** Before/after SHA256 and plots.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### D07 | No reversal and censored plots

**Tier:** R - ROUTINE

**Procedure:** Inspect no-reversal or insufficient-reversal runs and boundary-affected scenario.

**Pass if:** Missing estimates stay missing; exported plots warn clearly.

**Evidence to save:** Scenario report and PNG.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### D08 | Multi-condition and seed isolation

**Tier:** R - ROUTINE

**Procedure:** Run multiple conditions, staircase repeats and random seeds.

**Pass if:** No merging or overwrites; each run indexed correctly.

**Evidence to save:** Folders and index CSV.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 10 | Crash recovery, persistence and file integrity

### F01 | Abort and restart persistence

**Tier:** R - ROUTINE

**Procedure:** Escape during disposable experiment; restart and review prior run.

**Pass if:** Prior error/abort record persists; new run is separate.

**Evidence to save:** Manifest, trials, new UUID.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### F02 | Snapshot independence across changes

**Tier:** R - ROUTINE

**Procedure:** Save A run, modify setting/profile, save B, then compare A and B saved values.

**Pass if:** A retains original scientific configuration.

**Evidence to save:** Per-run resolved snapshots.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### F03 | Validator corruption detection

**Tier:** R - ROUTINE

**Procedure:** Copy a run and corrupt one value in COPY; run validator only on copy.

**Pass if:** Corruption flagged; original untouched.

**Evidence to save:** Validation error and original hash.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### F04 | Missing or stale runs index

**Tier:** R - ROUTINE

**Procedure:** In disposable data root simulate absent or stale runs_index.csv while preserving run folder.

**Pass if:** Canonical acquisition remains; Data page limitations documented.

**Evidence to save:** Disk folders, UI result and index.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### F05 | Profile revision conflicts

**Tier:** R - ROUTINE

**Procedure:** Try competing/stale revision saves and unsaved calibration drafts.

**Pass if:** Conflict explicit; prior physical readings protected.

**Evidence to save:** Revision before/after.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### F06 | Export and inspection integrity

**Tier:** R - ROUTINE

**Procedure:** Open saved TSV/JSON/PNG and derived plots with standard tools, incl. regional locale.

**Pass if:** Readability and units survive, viewing does not edit raw bytes.

**Evidence to save:** Open check and checksums.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### F07 | Partial cross-file write caveat

**Tier:** R - ROUTINE

**Procedure:** Read documented exception handling and existing fault injection tests; never corrupt real participant workspace.

**Pass if:** Nontransactional failure identified as error; recovery policy documented.

**Evidence to save:** Failure manifest and test issue.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## 11 | International deployment and cross-site comparability

### G01 | Site operator and protocol roles

**Tier:** X - CROSS-SITE

**Procedure:** Record site ID, workstation, technician, study owner and software reviewer.

**Pass if:** Every claim is attributable; approval scope defined.

**Evidence to save:** Signed site sheet.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### G02 | Locale, path and number formatting

**Tier:** X - CROSS-SITE

**Procedure:** On controlled systems try comma decimal, unicode/long paths, restricted filename and alternate locale.

**Pass if:** Parser behavior reproducible and errors actionable.

**Evidence to save:** OS settings and filenames.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### G03 | Timezone and DST

**Tier:** X - CROSS-SITE

**Procedure:** Inspect UTC trial timestamps and local date folder rollover near midnight/DST.

**Pass if:** Run UUID/time interpretation unambiguous across timezones.

**Evidence to save:** Manifest timestamps.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### G04 | Screen aspect, resolution, DPI

**Tier:** X - CROSS-SITE

**Procedure:** Repeat physical geometry at different sizes and DPI scaling where available.

**Pass if:** Bound actual framebuffer/physical dimensions correct; no assumed square pixels.

**Evidence to save:** Ruler/OS data.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### G05 | Refresh and graphics vendor diversity

**Tier:** X - CROSS-SITE

**Procedure:** Repeat graphics and timing tests across at least two refresh modes and GPUs.

**Pass if:** Differences documented; no unjustified equivalence.

**Evidence to save:** GPU and Hz matrix.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### G06 | Platform-dependent audio

**Tier:** X - CROSS-SITE

**Procedure:** Compare Windows cue output with non-Windows restriction.

**Pass if:** Unsupported acoustic presentation not silently called qualified.

**Evidence to save:** Audio/OS results.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### G07 | Restricted network/permissions

**Tier:** X - CROSS-SITE

**Procedure:** Launch offline; exercise read-only or permission-limited disposable folders.

**Pass if:** Normal offline function works; write failure clear; no genuine data loss.

**Evidence to save:** Permission and log.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

### G08 | Cross-site frozen equivalence bundle

**Tier:** X - CROSS-SITE

**Procedure:** Exchange exact source commit, spec, settings, stimuli, units, seeds and independent site calibration reports.

**Pass if:** Digital protocol reproducible; optical/timing equivalence independently approved.

**Evidence to save:** Cross-site sign-off.

**Outcome:** [ ] PASS [ ] FAIL [ ] BLOCKED [ ] NOT RUN [ ] N/A.  **Owner/date/evidence ref:** __________________

## Printable evidence worksheets

### Annex A - Master case register

Case ID | tier | status | tester | date | evidence link | defect ID | retest status.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex B - Graphic repeat-run matrix

Run sequence A / A / A / B / A | selected monitor ID | experiment | changed parameter | launch/close outcome | run UUID | screen photo | traceback.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex C - Geometry/spatial

Profile UUID/revision/hash | active width/height | viewing distance | resolution | refresh | axis/eccentricity | requested degrees/cpd | realized | measured +/- uncertainty.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex D - Photometry/precision

Meter serial/calibration | integration | ambient | display mode/LUT/HDR | normalized commands | replicate cd/m2 | mean/SD | black drift | physical uncertainty.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex E - Timing/input/sound

Requested vs quantized frame count | software flips | photodiode onset/offset | latency/jitter | dropped intervals | key and accepted response | microphone cue onset.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex F - Scientific/adaptive trace

Condition | staircase | target | response | correct | n-down/up | presented strength | post-update value | reversal | completion | primary estimator.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex G - Artifact integrity

Run UUID | kind human/test/synthetic | manifest status | accepted count | saved snapshots | validator output | trials SHA256 | derived outputs.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex H - Defect and regression record

Issue ID | severity | reproducible steps | expected/observed | commit, GPU, profile, OS | logs/screenshots | PR | regression | field retest.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex I - Cross-site comparison

Site A / B | source + protocol hashes | measured monitor geometry | gamma, contrast, precision | photon timing | scientific equivalence decision.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex J - Qualification decision

Protocol study owner must sign: measured physical requirements met? Any blockers? Exact selected experiment and monitored profile hashes? Test data never promoted.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

### Annex K - Final sign-off

Site | tested commit | date | scope: demos / virtual / uncalibrated fullscreen / pilot / qualified human | PASS/FAIL/BLOCKED/N/A totals | restrictions | approvals.

**Record / measurement:** _________________________________________________

**Evidence location:** _____________________________________________________

**Date / person / reviewer:** ______________________________________________

## Additional repository references

- [Chronological calibration workflow](CHRONOLOGICAL_CALIBRATION_WORKFLOW.md)
- [Output precision laboratory guide](OUTPUT_PRECISION_CALIBRATION.md)
- [Windows hardware acceptance](WINDOWS_HARDWARE_ACCEPTANCE.md)
- [Human readiness](HUMAN_EXPERIMENT_READINESS.md)
- [Scientific redesign](SCIENTIFIC_REDESIGN.md)
- [Experiment consistency](EXPERIMENT_CONSISTENCY_PLAN.md)

**Version guidance:** The commit above identifies the original audit baseline; record the *actual* later git SHA for every run and retest. This checklist is a site validation plan, not proof of hardware calibration.
