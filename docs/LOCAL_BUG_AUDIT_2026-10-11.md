# PsyCoLab local bug audit — 11 October 2026

The Windows geometry/test-stimulus crash is fixed and verified on the affected machine. The local audit identified and corrected the issues below. This is software verification, not certification of psychophysical stimulus accuracy.

## Baseline and preservation

- Authoritative checkout: the user's local Psychophysics_Collaborative_Lab repository.
- Branch: main. HEAD before and after: `1902a11ea76ebe2d2fd890c9aadef66dd29e36f4`.
- Initial Git status: clean; no uncommitted, staged or nonignored untracked work.
- Recorded initial status, HEAD, binary diff and SHA-256 inventory before source edits. Backed up each source file before its first change. Each patch checked its expected pre-edit hash before writing.
- Final changes: 20 existing source files, one new regression-test file, and this report. No existing source files removed. Source changes are unstaged and uncommitted.
- No push, pull, fetch, commit, branch creation, reset, stash, remote change or history change. Public GitHub was not accessed. The project mirror's synced sources were not modified.
- Test data, temporary local profiles, hardware diagnostic reports and portability-copy outputs were isolated under the chat's `psycolab-audit` scratch directory. No participant acquisition was started; existing acquisition records and normal local monitor configuration were not edited.

## Confirmed findings and local fixes

Locations refer to the final local source. Severity describes potential impact, not a claim that every issue had occurred in an existing run.

| Severity | Finding | Location | Correction and evidence |
| --- | --- | --- | --- |
| High | Windows default-screen launch crash | [src/psychophysics_lab/core/display.py](../src/psychophysics_lab/core/display.py), line 35 | Reproduced the exact Win32Screen ValueError on this machine. Pyglet get_default_screen() calls get_screens() again and returns a fresh object. Select by device ID, or unique geometry when no device ID is available, and return the original enumerated handle. Empty/missing/ambiguous displays fail clearly. Only the existing legacy reference permits this default policy; explicit bindings never silently fall back. |
| High | Setup refresh silently changes monitor | [src/psychophysics_lab/ui/setup.py](../src/psychophysics_lab/ui/setup.py), line 1169 | Textual set_options() resets the value even when still valid. Restore the compatible selection explicitly after rebuilding options. |
| High | Detect displays silently rebinds local profile | [src/psychophysics_lab/ui/profiles.py](../src/psychophysics_lab/ui/profiles.py), line 70 | Preserve the current physical binding across detection and reordering. A missing binding leaves a blank choice instead of selecting the first display. Require a selection when connected candidates are available. |
| Medium | Malformed local profiles crash profile loading/editor | [src/psychophysics_lab/config/monitor.py](../src/psychophysics_lab/config/monitor.py), line 12 | Validate the top-level JSON object, calibration list/items and qualification list before using them. Invalid local profiles follow the existing warning-and-skip path. |
| Medium | Non-text device IDs can never match enumeration | [src/psychophysics_lab/config/models.py](../src/psychophysics_lab/config/models.py), line 67 | Reject non-text device IDs at profile validation rather than allowing an unusable saved binding. |
| Medium | Diagnostic uses a changed fullscreen resolution | [src/psychophysics_lab/core/geometry_check.py](../src/psychophysics_lab/core/geometry_check.py), line 92 | Recheck the actual window dimensions after creation, not only the earlier screen enumeration. Close the diagnostic window on failure. |
| Medium | Off-axis diagnostic metadata does not describe rendered pixels | [src/psychophysics_lab/core/display_tests.py](../src/psychophysics_lab/core/display_tests.py), line 68 | Calculate angular endpoint extent and cycles across the patch from the rounded rendered centre. The diagnostic drawing and CSF mathematics are unchanged. |
| High | Primary recording errors can be hidden | [Events/adaptive_session.py](../Events/adaptive_session.py), line 185 | Protect the pre-response snapshot inside the error handler. Preserve the original exception when error-state persistence or window exit also fails; attach secondary errors as notes and stop the queued trials. |
| High | CSF screen/window startup bypasses adaptive finalisation | [Experiments/contrast_sensitivity_function.py](../Experiments/contrast_sensitivity_function.py), line 45 | Move selection/window creation into the existing guarded lifecycle, retain the original exception, save adaptive error state and handle cleanup when no window was created. |
| High | Ctrl+C can leave success-like run metadata | [src/psychophysics_lab/core/runner.py](../src/psychophysics_lab/core/runner.py), line 400 | Record an interrupted run as an error, finalise surviving records and re-raise the original interruption. The CLI still returns its existing cancellation code. The CSF and geometry handlers also preserve interrupts through cleanup and record diagnostic errors. |
| High | Zero-duration keyless CSF phases never advance | [src/psychophysics_lab/experiments/contrast_sensitivity.py](../src/psychophysics_lab/experiments/contrast_sensitivity.py), line 67 | Reject timeFixate=0, timeInterval=0 and timeAB=0 before acquisition. The existing engine interprets T=0 as waiting indefinitely, but these phases have no accepted keys. Positive durations, phase order, and timeT=0 self-paced responses are unchanged. This is an explicit input-validation change, not a new timing procedure. |
| Medium | Existing incompatible trial table accepts canonical appends | [src/psychophysics_lab/data/trials.py](../src/psychophysics_lab/data/trials.py), line 300 | Check an existing nonempty trial header before opening it for canonical use. Reject incompatible files without changing their contents or the historical schema. |
| Medium | Bad saved workspace values crash setup | [src/psychophysics_lab/data/workspace.py](../src/psychophysics_lab/data/workspace.py), line 57 | Ignore a malformed reusable request whose experiment_values is not an object. |
| Medium | Removed experiment breaks Load Data Workspace | [src/psychophysics_lab/ui/setup.py](../src/psychophysics_lab/ui/setup.py), line 1222 | Resolve monitor compatibility against the selected registered experiment when an old workspace references an experiment no longer available. |
| Medium | Rejected data path creates configuration subfolder first | [src/psychophysics_lab/ui/setup.py](../src/psychophysics_lab/ui/setup.py), line 1184 | Validate source/config/data separation before creating the selected directory. |
| Medium | Preflight accepts mismatched experiment identity | [src/psychophysics_lab/config/preflight.py](../src/psychophysics_lab/config/preflight.py), line 13 | Reject requests validated against a different experiment specification. |
| Medium | Analysis can read a run still being written | [src/psychophysics_lab/analysis/thresholds.py](../src/psychophysics_lab/analysis/thresholds.py), line 145 | Reject configuring/configured/running records before reading trials or writing derived outputs. Existing final-status and older missing-status records retain their prior treatment. |
| Medium | Relative environment data path depends on launch directory | [src/psychophysics_lab/paths.py](../src/psychophysics_lab/paths.py), line 46 | Resolve a relative PSYCOLAB_DATA_DIR against the repository parent, consistently with TUI paths; enforce the existing separation policy. |
| Medium | Malformed preset values can crash preset loading | [src/psychophysics_lab/config/local.py](../src/psychophysics_lab/config/local.py), line 73 | Offer only presets containing a values object. |
| Medium | Windows display identity fails canonical portability validation | [scripts/validate_run.py](../scripts/validate_run.py), line 263 | Accept only a device_id field matching the Win32 display-device pattern (for example \.\DISPLAY1 with its Windows device prefix). Ordinary UNC and absolute file paths remain rejected. |
| Medium | Malformed launcher state causes attribute error | [scripts/launcher_setup.py](../scripts/launcher_setup.py), line 75 | Treat valid JSON with a non-object top level as missing setup state. No installer or dependency update was run. |
| Medium | Legacy parameter mapping helpers raise NameError/TypeError | [libC.py](../libC.py), line 201 | Correct mapping overrides in copy_params and stim_factory. Defaults remain unchanged; the active CSF Params-object path and shader code are unaffected. |

## Root cause and display-selection policy

The installed Pyglet 1.5.27 `Win32Display.get_screens()` constructs new Win32Screen instances on each enumeration. Its inherited `get_default_screen()` calls `get_screens()` again. The previous `screens.index(screen)` therefore depended on equality between distinct screen objects and raised the user's exact ValueError at the original display.py line 44.

The fix holds one Display instance and one enumerated snapshot, matches the fresh default handle using its device name, and returns the matching original handle. If device identity is unavailable, only one exact geometry match is accepted. There is no arbitrary screen-zero recovery for missing/ambiguous monitors. Explicit profiles continue to use their saved binding; reordered enumeration is supported where device identity matches. Expected resolution and explicit-profile refresh-rate validation remain enforced.

Windows display names identify OS display devices, not verified panel serial numbers. A dock/driver/topology change may require reselection. The unbound legacy reference remains explicitly marked `legacy_default_unverified`.

## Tests and observed results

| Check | Result |
| --- | --- |
| Baseline Python 3.11.15 full pytest suite | 279 passed, 25.40 s |
| Final Python 3.11.15 full pytest suite | 326 passed, 23.59 s; no skipped tests reported |
| Added regression cases | 47; includes distinct handles, missing/ambiguous displays, reordered explicit binding, mode mismatch, profile/TUI selection, malformed local files, interruption/error finalisation, geometry metadata, incompatible trial headers, Windows provenance, input validation and concurrent profile revisions |
| Existing full-suite coverage retained | Fixed navigation at multiple terminal sizes; source opening with project context; synthetic CSF completion/ceiling/abort/error; staircase and contrast rules; snapshots/hashes; data dictionary/readable exports; run validator; concurrent index writers and unique run allocation |
| Before-fix regression evidence | Separate saved runs reproduced the original failures before each principal patch group; baseline did not contain these cases |
| Portability checker | Passed |
| Dependency consistency (`pip check`) | No broken requirements found |
| Syntax compilation | All inspected project, example and test Python files compile under Python 3.11, without generating bytecode |
| Final diff whitespace check | Passed; Git may print its existing LF/CRLF conversion notices |
| Relocated synthetic pipeline | Passed from an isolated source copy with spaces, ampersand and Unicode; non-repository working directory; relative data override; all 16 read-only run-validator checks passed |
| Actual Windows monitor selection | Passed: one detected display, 1536 × 960, OS-reported 59 Hz |
| Actual fullscreen static diagnostics | Three completed and closed: legacy size, explicit-profile size, explicit-profile spatial grating; one second requested each; reports stayed in isolated configuration |
| Actual CSF graphics components | Unchanged grating shader and fixation component compiled/drew in a hidden Windows OpenGL window with no GL error; no acquisition or responses |

The three short static checks observed 34, 38 and 39 flips, respectively. Median software intervals were approximately 30.19, 30.85 and 28.79 ms; maxima approximately 31.66, 32.29 and 35.70 ms. The diagnostic's existing estimator flagged 18, 25 and 22 suspected missed refreshes. These are short software observations in this desktop session, not photon-onset measurements or calibrated refresh estimates. They do **not** establish reliable 59/60 Hz presentation. The scheduler, temporal waveforms and CSF timing implementation were not changed.

## Scientific and data contracts preserved

Byte-for-byte baseline checks confirm that `Events/staircase.py`, `Events/adaptiveMethods.py`, `Events/display_contrast.py`, `Events/stimuliC.py` and `Interface/config.py` are unchanged. In particular:

- Staircase update/termination procedures, random condition selection, retained 31.5 spatial scaling, shader contrast expression and normalized display-contrast units are unchanged.
- Canonical trial schema version/columns and historical six-column response schema are unchanged; no historical data migration or rewrite occurred.
- Positive CSF phase durations and `timeT=0` self-paced behavior are unchanged. Zero-duration keyless phases are now rejected explicitly because they could not advance.
- The new geometry calculation corrects diagnostic metadata for rounded position; it does not alter the CSF stimulus.
- Stored diagnostic status/verification flags remain unverified. Saving an explicitly bound local profile does not certify its physical dimensions, luminance mapping or timing.

## Audit coverage and remaining limits

Reviewed the package entrypoint/paths/config/preflight, TUI screens/editor/profile workflow, monitor resolution, diagnostic plans/render lifecycle, experiment/stimulus registries and extension adapter, CSF wrapper and legacy renderer/helpers, adaptive session/staircase/contrast code, data paths/locks/index/trial writers, provenance/finalisation, threshold analysis, validation, launcher and portability tooling. Existing tests plus the new cases exercise the supported pipeline with synthetic data. Not every function or native failure mode has been executed.

Remaining items require laboratory or deployment validation:

1. **Timing:** investigate the observed software frame intervals on the intended display/GPU/session. Use a photodiode to validate binary and sine modulation, refresh stability, dropped frames, onset and offset. No visible flicker test or participant acquisition was run.
2. **Multiple monitors and DPI:** only one physical monitor was available. Exercise an explicit secondary monitor, negative desktop coordinates, swapping primary display, reconnecting/docking, duplicate models, resolution/refresh changes and Windows scaling. Reordering/missing/ambiguous behavior is covered with fake screen objects, not multiple physical panels.
3. **Geometry/photometry:** measure bar length and position with a ruler, check viewing distance and actual active screen dimensions, and validate spatial cycles with appropriate measurements. Reference dimensions used for smoke tests are not a calibration of this display.
4. **Deferred CSF science:** retain the existing shader and legacy spatial convention pending the review documented in `docs/DEFERRED_STIMULUS_REVIEW.md`. Digital values can exceed the display range under the existing contrast/step expressions; bounds, clipping policy and physical contrast interpretation require an explicit scientific decision. This audit does not silently repair those procedures. The retained wall-clock/phase scheduling is not frame- or photon-certified.
5. **Concurrency:** tested independent OS-process writes to the local run index (existing test) and competing profile revisions (new test: one winner, one stale-edit rejection). File locks are advisory local-filesystem locks. Cloud-sync/network filesystem behavior and simultaneous real acquisitions were not certified. The legacy runtime changes process-wide working directory/import state and uses global random/window state; it is not a thread-safe multi-acquisition API. Run acquisition in separate controlled processes and avoid contending for one display.
6. **Deployment/UI:** Linux/macOS native display backends, fresh offline installation, actual VS Code window reuse and manual terminal interaction were not exercised. Editor arguments and fixed navigation are tested headlessly. Dormant legacy remote-control entrypoints and abrupt OS/process termination remain outside the exercised runtime path.
7. **Failure limits:** fault injection covers selected read/write/setup/cleanup/interrupt errors. It does not prove recovery from every disk-full, power-loss, driver or native GPU failure. No real existing acquisition dataset was opened for repair or validation.

## Manual acceptance sequence

1. Launch the local TUI; scroll/resize each page and confirm top navigation stays fixed. Open two source files and verify they appear in the intended VS Code project.
2. Create an unverified local display profile using measured dimensions and the intended monitor. Detect again and confirm selection stays on that monitor; change/disconnect it and confirm clear rejection rather than fallback.
3. Run size/position/spatial diagnostics on the intended display, verify with measurements, record the results, and reopen the TUI to confirm saved profile/revision and diagnostic availability.
4. Investigate timing with external measurement before qualifying temporal presentation or CSF acquisition. Do not infer timing quality from these smoke tests.
5. With laboratory approval, conduct a clearly labeled non-participant CSF practice run in a fresh test data root; check Escape, completion/ceiling states, saved records and `scripts/validate_run.py`. Existing participant records need not be touched.

Raw local evidence is retained in the chat scratch audit directory: baseline status/HEAD/diff/hash inventory, original source backups, before/after regression logs, final full-suite output, three hardware diagnostic JSON reports, shader smoke output, relocated pipeline output and integrity summary. These artifacts contain local paths and synthetic data and were not placed in shared source directories.
