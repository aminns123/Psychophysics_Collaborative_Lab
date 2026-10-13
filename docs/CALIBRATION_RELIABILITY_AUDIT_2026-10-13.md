# Calibration and repository reliability audit — 2026-10-13

## Base, scope and result

PR #18 was merged. Both local and remote main were `7d74a825f9ab81c55647f95da4273985292f8a37` when inspected; the local working tree was clean. Implementation uses `fix/calibration-evidence-lifecycle-reliability`, based directly on that merge. No earlier changes were discarded or duplicated. Main is not changed by this work.

The confirmed fullscreen failure was a deque slice in the timing summary after presentation, not evidence of a rectangle rendering failure. Fixes cover diagnostic termination, factual stage progress, ruler attribution, physical evidence compatibility, photometer durability, recovery output and additional repository failure paths. The six-page layout, experimental defaults, contrast definition, staircase rule and threshold convention remain unchanged.

The original baseline passed **533 tests** on Windows/Python 3.11 in 156.93 seconds. This demonstrated a missing regression case rather than proving the fullscreen workflow. Final results are recorded below.

## Calibration outcomes

| Stage | Saved state and behavior | Verification boundary |
|---|---|---|
| Display | Existing explicit discovery/binding, resolution/refresh checks, manual dimensions, versioned profile save/reload retained. Missing/ambiguous/mode-changed displays fail closed. | Windows device names identify OS outputs, not panel serial numbers. Physical active dimensions and eye distance still require measurement. |
| Geometry | Successful presentation shows `AWAITING MEASUREMENT`; saving length computes signed error and shows `AWAITING REVIEW`. The latest **ruler** report is selected even after spatial/timing tests. | Green requires measured evidence plus the existing explicit geometry verification declaration. No numeric tolerance or automatic acceptance is invented. |
| Spatial | Successful presentation appears immediately in active-page progress and common readiness. Angular sine sampling and independent axis pitches retained. Nyquist boundary is now rejected consistently because boundary patterns depend on phase. | Software completion does not certify spatial output. Complete geometry review and inspect actual cycles/orientation. |
| Luminance | Import still validates profile/revision, finite commands/readings, monotonic pairs and method/date/notes; fake examples remain rejected. Raw repeats persist first, with mean/count/sample SD in a derived pilot. Zero/one-command sessions are incomplete; interrupted sessions preserve readings and record error. Missing pilot exports can be rebuilt without overwriting researcher edits. | Saved observations/imported mappings remain unverified until explicit laboratory review. Digital commands are not cd/m². |
| Timing | Iterator-based intervals support lists/deques, empty/single buffers and bounded long sessions. Invalid/nonmonotonic samples fail explicitly. Escape, Enter and timeout save termination reasons, reports and software timing observations. | Nominal refresh, flips and suspected missed refreshes do not measure photon onset. Independent photodiode evidence is required for timing verification. |
| Review | TUI, readiness reports and run metadata share calibration progress/evidence calculations. Human qualification stays an explicit experiment-specific declaration; simulation validation does not require physical qualification. | No software test automatically qualifies an experiment. Existing legacy-reference compatibility policy remains for backwards compatibility. |

## Confirmed defects and repairs

| Severity | Root cause | Repair |
|---|---|---|
| High | `timestamps[1:]` assumed a sliceable sequence after timestamps became a bounded deque. | `itertools.pairwise`; retain statistics and the existing 6000-flip bound. Regression tests exercise real diagnostic control flow with mocked Pyglet. |
| High | Raw session save could succeed and pilot save fail, followed by removal of the reading from memory. | Raw `session.json` is authoritative; pilot filesystem failures produce visible export warnings without removing saved observations. Recovery regenerates missing exports. |
| High | Only the UI invalidated verification/qualification after physical edits; direct profile persistence could retain old certification. | Persistence also clears affected declarations and experiment qualification when geometry, binding, refresh or measured mapping changes. Metadata-only saves retain applicable evidence. |
| Medium | Stage flags conflated software progress with lab verification; spatial/timing completion was hidden. | Shared factual states and next-action text on active pages and Review, with existing red/green verification retained. |
| Medium | Ruler actions chose the latest diagnostic of any kind and used exact profile hash rather than physical compatibility. | Select latest ruler, enforce completed status and physical identity/configuration, retain measurement history and permit metadata-only revisions. |
| Medium | Evidence comparison omitted profile ID/UUID; otherwise identical different profiles could match. | Require identity, consistent snapshot hash and physical fields. Hash consistency is not a cryptographic certification of observations. |
| Medium | Photometry interruptions left `in_progress`; sessions with insufficient commands were labeled completed. | Record error/incomplete states, preserve observations and reject readings after session end. Unsaved keyboard entries must be saved or cleared before Escape. |
| Medium | Recoverable failures printed a traceback before also saving it; later generic launcher success text obscured failed operations. | Preserve full trace in one report, print concise error/report path, count failed operations at normal exit, and make batch exit wording neutral. Fatal exits retain diagnostic behavior. |
| Medium | CSF observer divided extreme finite conditions before logarithms; evaluator exponentiated unrepresentable model midpoints. | Difference of logarithms, finite diagnostic representations, explicit failed scientific check for unrepresentable midpoints. Ordinary model and estimator conventions retained. |
| Medium | A later scenario seed/evaluator exception omitted scenario-level results from already acquired runs. | Save a partial synthetic error report alongside acquired runs, preserve original exception and annotate secondary report failures. |
| Low | Failed figure save bypassed close; failed index replace left a temporary file. | `finally` cleanup; original index preserved. |
| Medium | Fresh environment validation failure escaped the install handler with an unhandled subprocess traceback. | Return actionable setup failure before saving success state. Mocked fresh/reuse tests cover paths with spaces, Unicode and ampersands. |

No evidence establishes an additional rectangle rendering defect from the supplied traceback. The PR #18 OpenGL rectangle changes are retained; actual display/driver behavior remains a hardware acceptance item.

## Evidence compatibility and persistence

Completed geometry/spatial/timing reports live under machine-local `diagnostics/display_geometry/<profile>/...`. Profile ID/UUID and width, height, viewing distance, expected resolution, display binding and refresh must match their consistent saved snapshot. A revision increment, notes or verification declaration alone does not invalidate them. This conservative policy intentionally rejects changed physical setups. Failed presentations never become completed evidence.

Ruler observations and history stay in the diagnostic. Luminance raw observations/pilots stay in `calibration_sessions`; imported means and provenance enter a new append-only profile revision only through explicit Save. Luminance imports retain the stricter exact profile/revision requirement. Changing a physical setup clears experiment qualification; geometry changes affect geometry declaration, refresh affects timing, binding affects all, and a mapping change affects photometry. Geometry edits do not themselves change measured command/luminance values. Laboratory applicability still needs review.

Run metadata includes the common progress snapshot with **relative local-config references**, not absolute machine paths. A run's saved monitor snapshot remains the source for interpreting that acquisition; current profile edits do not rewrite historical trials. Synthetic participant markers and external data-root separation remain enforced.

## Scientific checks

- Geometry: `L=2d*tan(theta/2)` with metres internally. At 1 m and a 610×350 mm active screen with 1920×1080 pixels, a 100 mm horizontal ruler rounds to 315 px / 100.078125 mm; vertical rounds to 309 px / 100.1388889 mm. Off-axis extent uses the difference between endpoint arctangents, not the centred equivalent angle.
- Spatial: independent x/y pitch, angular pixel coordinates, cpd versus degrees/cycle, orientation projections and Nyquist guards remain separate from photometry. Diagnostic sine orientation denotes the axis of phase variation. Production shader checks from the earlier audit are reference evidence, not newly repeated optical measurements.
- Timing: 59 Hz with a requested 10 Hz binary waveform rounds to a 3-frame half-cycle, giving 59/6 Hz. Sine phase is frame-index sampled; dropped frames alter physical timing. Existing rounding and nominal frequency conventions are unchanged.
- Photometry: arithmetic repeat mean, sample SD (null for one observation), retained raw values and black surround/6° square definitions are unchanged. No gamma curve, photon timing or universal acceptance threshold is inferred.
- Adaptation/analysis: independent staircase histories, configured counts/steps, introductory one-down, flats/reversals, response ceiling, synthetic clocks, final-80%-of-post-update-reversals and alternative derived estimates remain covered by existing tests. No experimental method/default was changed.

Primary references checked: [Python 3.11 pairwise](https://docs.python.org/3.11/library/itertools.html#itertools.pairwise), [Psychtoolbox display dimensions caveats](https://psychtoolbox.org/docs/Screen-DisplaySize), [photodiode flip timing test](https://psychtoolbox.org/docs/FlipTimingWithRTBoxPhotoDiodeTest), [photometer luminance measurement](https://psychtoolbox.org/docs/MeasXYZ). The independent geometry checks follow elementary flat-screen trigonometry; these sources do not certify this hardware.

## Broader audit coverage and limits

Reviewed the current entrypoint/diagnostics, profiles/preflight/local state, display plans/lifecycle, all main TUI action areas, public contributor/registries/editor integration, CSF specification and retained acquisition/render adapter, adaptive state/event logger, external data paths/locks/index/trial durability/finalisation, threshold analysis, virtual observer/scenario provenance and Windows launcher. Existing repository audits and control inventory supplied the earlier architecture map; current changes and tests were checked against it. This is targeted static and executable coverage, not a claim that every function/native failure mode was exercised.

Remaining operational/scientific limits:

- No new physical ruler, photometer, photodiode or human-participant measurements were performed. Multi-monitor docking/DPI/output identity and actual fullscreen keyboard/driver behavior need laboratory acceptance.
- Legacy synchronous Windows Beep and wall-clock phase scheduling remain; changing feedback/timing is a protocol decision, not a silent audit correction.
- Legacy and canonical acquisition files are independently durable, not a multi-file transaction. Abrupt power loss can require manifest/raw-record inspection; no historical participant records were repaired.
- Acquisition uses process-wide legacy state; parallel acquisitions must use separate controlled processes. Advisory locks do not certify network/cloud-sync storage.
- The alternate legacy display-box/gamma branch remains uncalibrated. Shader range guards reject unsafe human presentations instead of clamping or changing scientific defaults.
- Packaging builds successfully but the legacy adapter still requires a checkout; this is not a standalone wheel deployment certification. Fresh installation was tested through isolated command mocks, not replacement of the user's working environment or an offline install.

## Verification

| Verification | Actual result |
|---|---|
| Windows final complete pytest, Python 3.11 | **586 passed, 0 failed, 0 skipped**, 161.67 seconds |
| Added regression cases versus baseline | 53 |
| Final photometry/lifecycle targeted rerun | 64 passed, 3.43 seconds |
| Dependency check | No broken requirements |
| Portability checker and diff whitespace | Passed |
| Syntax parsing | 136 Python source/test files passed; no bytecode generated |
| Headless startup/environment reuse | Passed; NumPy 1.26.4, Pyglet 1.5.27, Textual 1.0.0 |
| Wheel build without dependency installs | Passed, psychophysics_lab 0.2.2 |
| Fresh launcher/reuse/write failure command tests | 3 passed; isolated mocks, no replacement of working environment |
| Linux/Windows GitHub CI | Requested through the PR; check remote job results separately |
| New physical hardware/lab measurements | Not performed |

No unexpected warning summary was emitted by the final suite. Export-warning tests deliberately capture the expected warnings.

Reproduce from the repository with Python 3.11:

```powershell
$psycolabTestRoot = Join-Path $env:TEMP ("PsyCoLab-review-" + [guid]::NewGuid())
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=$psycolabTestRoot
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\portability_check.py
.venv\Scripts\python.exe -m psychophysics_lab --diagnose
.venv\Scripts\python.exe scripts\launcher_setup.py
git diff --check main...fix/calibration-evidence-lifecycle-reliability
```

The unique test root is disposable synthetic test data; these checks do not access participant recordings. GitHub Actions runs Python 3.11 headless pytest/portability on Windows and Linux. Actual remote results must be checked on the PR; no unavailable Linux result is assumed.

## Windows laboratory acceptance

1. Bind the intended panel, verify actual framebuffer pixels/DPI and OS refresh; disconnect/change modes and confirm fail-closed behavior. Measure active width/height and eye distance.
2. Present horizontal/vertical centred/off-axis rulers; Escape/Enter; verify saved completion, enter physical length, inspect error and review against explicitly chosen lab criteria. A metadata-only save should retain evidence; changing distance should show stale.
3. Present known-cpd patterns and production gratings; independently check axes/orientation/cycles/aliasing and pixel rounding. No software-only grating certifies spatial output.
4. With a calibrated photometer, check the 6° square/readout placement and black surround, collect repeated readings, inspect immediate raw saves/mean/SD, import and explicitly Save/reload. A fake demo must be rejected. Inspect actual experiment background/peak/trough luminance and digital range.
5. Use a photodiode for photon onset/offset and requested/realized timing; software flips alone remain unverified. Confirm returned TUI progress and clean window/callback cleanup.
6. Use a disposable reviewed pilot to verify responses, abort/ceiling/completion and raw records. Declare verification/qualification only after the experiment owner's requirements are met.

## Review and merge

Review the dedicated branch and PR diff/tests first. No auto merge is performed. After approval, merge through GitHub or manually from a clean local main:

```powershell
git switch main
git pull --ff-only
git merge --no-ff fix/calibration-evidence-lifecycle-reliability
```

These merge commands are for the researcher; they were not executed during the audit. No actual profiles, participant/photometer records, machine paths or generated runtime logs are included in the commits.
