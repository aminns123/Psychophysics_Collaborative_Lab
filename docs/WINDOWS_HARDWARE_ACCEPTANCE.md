# Windows laboratory acceptance — profile revision and protocol specific

For the **14 October 2026 spatial-observation and fullscreen-return changes**, first follow the focused [interrupted-Work acceptance checklist](INTERRUPTED_SPATIAL_WORK_FOLLOWUP_2026-10-14.md). It covers the new requirement to record a researcher assessment after fullscreen presentation, preserving Calibrate navigation and selecting saved luminance pairs. Both Windows/Linux CI suites pass, but these manual monitor checks remain outstanding.

This procedure separates software checks, ruler geometry, spatial frequency, photometry and physical timing. Record the actual result for each step. A saved/qualified flag is a laboratory declaration; software cannot supply missing measurement evidence.

## 1. Protect existing records and record the software

Review the draft PR before merging. Use the usual reviewed Git workflow; do not replace `local_psychophysics_config`, external data, old runs or local profiles. Use Python 3.11 from the project terminal:

```powershell
.venv\Scripts\python.exe -m pip check
$testDir = Join-Path $env:TEMP ("psycolab-audit-" + [guid]::NewGuid().ToString("N"))
.venv\Scripts\python.exe -m pytest -q --basetemp=$testDir
.venv\Scripts\python.exe scripts\portability_check.py
.venv\Scripts\python.exe scripts\windows_display_preflight.py --profile legacy_reference_display_local
```

Record `git rev-parse HEAD`, selected profile ID/UUID/revision/hash, OS/GPU/driver, resolution, Windows scaling, refresh and viewing distance. Use a fresh external **test** data directory for any new software checks; never select an old participant's run for acquisition.

The audit's read-only OS preflight found this existing local profile at 340×210 mm, 0.5 m and 1536×960 pixels, **59 Hz** (not the 60 Hz in the original request). Resolve that nominal-rate discrepancy before interpreting temporal diagnostics. These measurements were not independently taken by the agent.

## 2. Select and bind the intended monitor

1. In Calibrate, select the local profile. Measure the active illuminated area excluding bezels and the eye-to-screen distance with the apparatus in its actual position. Save an explicitly measured local revision.
2. Detect connected displays. Identify the physical screen; do not assume monitor 0. Bind and Save. Use detected resolution/refresh only deliberately. Detection does not measure width/height/distance/luminance.
3. Compare Windows Display settings, OS preflight and the actual fullscreen diagnostic dimensions. Investigate DPI scaling/logical-pixel versus framebuffer discrepancies. Do not force a profile number to match merely to pass a check.
4. For the reported setup, local ppd at gaze should be approximately X=39.424 and Y=39.893 if the stated geometry and pixel resolution are correct; Nyquist is approximately half those values. The physical/pixel aspect mismatch is about 1.19%. Re-measure both axes and check Windows image mapping; do not assume square physical pixels.
5. Keep the ruler evidence tied to the exact profile revision/hash. Geometry changes make earlier evidence stale. They should not be copied as current validation or silently promote qualification.

## 3. Ruler geometry: both axes, several sizes and positions

1. Launch horizontal centred bars at 1°, 2°, 5° and, if they fit, 10°. At d=0.5 m the centred lengths are approximately 8.73, 17.46, 43.66 and 87.49 mm, using `L=2d*tan(theta/2)`. Read the report's pixel-rounded realized length and measure that displayed image.
2. Repeat vertically. Record physical ruler uncertainty, positioning uncertainty and the realized px/mm conversion for each axis.
3. Record a measured bar length using the current-revision diagnostic. The user's earlier ≈44 mm result for 5° differs from ideal by ≈0.78%; it is consistent with a coarse ruler reading but does not establish a cpd or luminance result.
4. Repeat at ±5° and ±10° eccentricity where the bar fits. Displacement uses `x=d*tan(eccentricity)`, not the centred-size formula. Measure position from fixation and compare the actual endpoint angles. The current diagnostic uses centred-equivalent physical extent for a degree-sized bar; its report separately calculates off-axis angular extent.
5. **Proposed preliminary ruler tolerance:** absolute length error no more than `max(1 mm, 2% of realized length)`, with combined uncertainty recorded. This is a screening criterion to be approved by the lab, not research-grade proof. For a frequency-sensitive study use a tighter equipment/uncertainty budget, e.g. a reviewed ≤1% geometry error target when the apparatus can support it. Small bars cannot prove 1% precision with a 1 mm ruler.
6. If one axis or eccentricity fails, stop and resolve scale/distance/alignment. Do not average contradictory axis errors away. Save results/error estimates and a photograph/measurement notes locally with the diagnostic revision.

## 4. Production GPU and spatial-frequency checks

The audit already ran the production GLSL shader in an invisible window on Intel UHD graphics; six cpd/legacy cases passed RGB readback. This does not prove the physical panel's frequency response or actual fullscreen mapping. Repeat after a GPU/driver change using a **new** test output folder:

```powershell
.venv\Scripts\python.exe scripts\windows_shader_probe.py --output "$env:TEMP\psycolab_shader_probe_new"
```

The folder must not exist; keep `shader_probe.json`. No fullscreen, display mode change or participant files are used.

1. Use Calibrate's spatial sine diagnostic with known 2, 4 and 8 cpd, both orientations, below Nyquist. At 5° centred extent these correspond to 10, 20 and 40 cycles. Count cycles in a sufficiently clear pattern or use calibrated imaging/spectral measurement; a visual impression alone is insufficient. Record realized angular extent because pixel rounding/off-axis positioning changes total cycles.
2. Repeat off centre. Compare angular-coordinate phase with the expected cycles across the actual endpoints. A pattern measured in millimetres must be converted using actual viewing geometry.
3. After contrast and qualification review, verify the **production Gaussian-enveloped stimulus** separately: orientation, 5° nominal width, ±5° eccentricity, visible clipping, full patch fit and displayed cpd. It is not the same drawing path as the diagnostic's unenveloped sine. Square pixel quads may have different physical extents on x/y when pitch differs.
4. In legacy mode retain historical phase coefficients and labels. Never call 63/252 legacy coefficients measured cpd. Period entries such as .5/.25/.125 degrees/cycle resolve to 2/4/8 cpd in new canonical records.
5. Adopt an instrument-supported frequency tolerance with the lab (a preliminary 2% screen can detect gross mistakes; tighter study-specific requirements need an uncertainty budget). GPU/readback tolerances are digital quantization criteria, not optical-frequency tolerances.

## 5. Contrast and luminance: required before scientific interpretation

1. Use a calibrated photometer to measure background, command range, gamma/nonlinearity and actual grating peaks/troughs. Keep date, apparatus, method, spatial location and uncertainty. OS brightness/RGB or a ruler cannot provide cd/m².
2. Distinguish `C_disp=(I_n-I_b)/(1-I_b)` from Weber `(L-Lb)/Lb` and Michelson `(Lmax-Lmin)/(Lmax+Lmin)` contrast. The current `box=False` shader draws `RGB=I_b+Gaussian*C_disp*sin(phase)/2`; the recorded I_n is an adaptive surrogate, not actual fragment RGB.
3. The old default I_b=.374, starting I_n=1 gives a conservative negative RGB trough. Human launch now rejects it. A sufficient safe digital bound at this background is C_disp≤.748, surrogate I_n≤.842248. This calculation is not a new scientific starting-value recommendation.
4. Review and explicitly choose safe starting parameters/steps with the experiment owner. Do not simply reduce values to bypass validation without protocol review. Repeated incorrect responses can cross the digital range; the guard stops the next unsafe presentation and preserves accepted rows. Decide the desired scientific ceiling/termination policy before production use.
5. Keep the alternate `box=True` branch disabled unless its device-specific channel/gamma/luminance mapping has been separately approved and tested. Do not infer its validity from the successful `box=False` probe.

## 6. Timing and human interaction

1. Check the announced nominal frame quantization using binary flicker exactly representable at the current OS rate and a deliberately inexact request. At 59 Hz, 10 Hz is not exactly a 3-frame half-cycle: the planned realized rate is 59/6≈9.833 Hz. Save reported software flip intervals/dropped-frame suspicions.
2. Measure stimulus photon onset/offset and dropped refreshes with a photodiode or equivalent instrument. Use repeated phase samples at the configured 250/250/200 ms values and any modified values. Record distribution, latency, jitter, missing refreshes and equipment error. Proposed acceptance: no unexplained missing frames and a preapproved frame/latency tolerance suitable to the experiment; do not equate millisecond UI values with achieved accuracy.
3. Feedback uses synchronous Windows Beep (500 ms after an accepted answer; new-condition beep also consumes time). Measure its effect on both onset scheduling and keyboard dispatch. Decide and approve whether audio belongs in the experimental interval before implementing asynchronous feedback or changed timings.
4. With a reviewed pilot protocol/test identity, verify LEFT=0 and RIGHT=1, a single accepted key produces one row, nonresponse keys do not advance adaptation, and Escape creates `aborted_by_user` without a fabricated row.
5. Test self-paced response and a finite response timeout. Confirm timeout/queue exhaustion does not claim successful staircase completion. Test response ceiling separately from completion and compare every staircase's saved counts/state.
6. Interrupt only a disposable pilot run to verify surviving records and clear error/abort semantics. Do not fault-inject disk failures on a real participant workspace; automated tests handle those in isolation.

## 7. Configuration, persistence and virtual pipeline

1. At 80×24 and 100×30, choose the local display from Experiment; unqualified profiles remain visible with reasons. Enter count=3 and conditions=2,4,8 cpd; choose multiple staircases and review the **global** trial budget.
2. Open Change display / Calibrate. Cancel and confirm the prior display stays selected; Apply and confirm fields remain. Save a calibration revision, return, Refresh profiles and re-Review. Fullscreen restarts retain the dedicated draft; reopen Configure to verify it.
3. Save a new preset, reopen it, Update selected preset and inspect local `.history`; Load invalid parameters must fail before changing the current draft. Presets store experiment fields rather than a second geometry definition.
4. Review ID/revision/hash, size/distance/ppd and readiness. While Review is open, explicitly edit a test profile revision; Run must reject the stale hash. Return, Refresh and Review anew. Missing requested profiles must be shown as unavailable rather than replaced by the reference.
5. Choose Run simulation. Check observer-only threshold/slope/preferred condition and seed fields; run independent seeds and a one-response censored case. No qualification is needed for this headless test, but assumed geometry and units must match Review and remain unverified by the simulation.
6. Keep synthetic runs in the same external hierarchy under reserved `synthetic_` identities with markers. They must not replace human settings or appear as human participant choices. Inspect canonical timestamps' deterministic virtual-clock label, model parameters and scenario success/failure report.

## 8. Run-record and analysis acceptance

1. Inspect `monitor_profile.json`, manifest, `experiment_config.json`, `trial_context.json`, `runtime_display.json` and `resolved_experiment.json`: the selected ID/revision/hash and geometry must agree. Use the saved snapshot, not today's profile, to interpret an old run.
2. Run `.venv\Scripts\python.exe scripts\validate_run.py <new_test_run_folder>`. PASS is internal consistency, not optical/psychometric validity. Historical dictionary validation may need its acquisition source version; never repair old files merely to make a current validator pass.
3. Inspect accepted counts, independent staircase histories and canonical presented/next values. Inspect per-condition staircase PNGs and a threshold summary only if there are reversal observations. Missing estimates must remain missing.
4. Confirm cpd plots label cycles/degree; historical plots retain legacy labels. Incomplete/censored and synthetic warnings must survive exporting the PNG. Last-N versus fraction and presented versus next choices must create separate derived analysis versions and preserve raw trials/checksums.

## Laboratory observation record

| Test | Profile revision/hash | Requested/realized | Measured ± uncertainty | Error | Pass/fail and evidence |
|---|---|---|---|---|---|
| H/V centred rulers (each size) | | | | | |
| Off-axis size/position | | | | | |
| Actual framebuffer/DPI | | | | | |
| Known cpd patterns / production Gaussian | | | | | |
| Gamma/background/grating peaks/troughs | | | | | |
| Refresh/onset/feedback/input timing | | | | | |
| LEFT/RIGHT/Escape/timeout/ceiling | | | | | |
| Virtual scenario / canonical validator | | | | | |

Record the experiment owner's scientific decisions separately. Mark a local profile qualified for an experiment only after the corresponding lab requirements are met. The audit does not consider this workstation certified for production-quality human psychophysics until those measurements and protocol decisions are supplied.
