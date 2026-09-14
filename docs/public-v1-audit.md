# Public framework audit — 14 September 2026

## Approved implementation update

The repository is a **general psychophysics framework**. CSF is its first
reference experiment, not its specification. The sections after this update
preserve the original audit as a historical baseline, not a list of outstanding
defects. The owner subsequently approved consecutive-response state, independent
completion, response ceilings and the C_disp argument-order correction.

Implemented:

| File | Responsibility/change |
|---|---|
| `Events/staircase.py` | Pure configurable streaks, stable independent staircase states, numeric reversal tracking and run lifecycle |
| `Events/adaptive_session.py` | Explicitly legacy CSF-specific event/file adapter, completion metadata and early queue exit |
| `Events/display_contrast.py` | Canonical digital C_disp conversions with keyword-only background/maximum arguments |
| `Events/adaptiveMethods.py` | Consume accepted responses once, delegate state, select only active IDs, preserve condition arrays and legacy conversion aliases |
| `Interface/config.py` | Correct reversed arguments; clearer internal contrast names with unchanged serialized keys |
| `Experiments/contrast_sensitivity_function.py` | Compose the session adapter, use existing queue/exit API and finalise metadata |
| `Functions/functionsForUse.py` | Import NumPy only inside geometry functions so response/file logic imports without display/scientific dependencies |
| `tests/test_staircase.py` | Consecutive-response, independent-state, reversal, completion and ceiling tests |
| `tests/test_adaptive_session.py` | Real legacy-file/event integration using a fake window and muted audio |
| `tests/test_display_contrast.py` | Formula/endpoints/round trips, legacy aliases, configuration correction and unchanged-default checks |
| `docs/public-v1-audit.md` | This implementation record, general architecture boundaries and thesis context |

The temporary AST-only audit probe was retired in favour of tests importing the
actual modules. No permanent package name has been chosen; the new pure modules
temporarily reside beside the legacy adapter, ready for an incremental move to
`adaptive/` and `config/` after naming approval.

Each staircase now requires a full consecutive run, includes the triggering
response once, clears the opposite streak and resets the triggering streak after
its step. Repeated key events cannot consume another response before the next
response phase. Only configured accepted keys reach the existing CSF response
mapping. The generic staircase receives a correctness boolean from its caller;
it knows nothing about arrows, intervals, locations or the number of alternatives.

Numeric updates are experiment-supplied callbacks. No step size, starting value,
contrast mathematics, timing, condition or response method is a framework default.
Per-staircase n_down, n_up and reversal limits are explicit configuration. The
run-wide response budget is a separate required parameter. An experiment using
constant stimuli or another adaptive procedure need not use this controller.

Reversal tracking preserves the legacy recorded-value convention: observe each
post-update intensity once, ignore flat changes, count a change of nonzero
direction, and exclude the initial placeholder row. The first recorded response
seeds the detector; the initial presentation is not added as a synthetic response.
Completion occurs at >= the configured count. No condition or state array shrinks;
active selection uses a separate set of unfinished IDs. Finished state is retained.

The existing CSF budget remains 30 responses, with its existing 2-down/1-up,
step sizes, 10-reversal criterion and all stimulus/display/timing values unchanged.
The experiment retains its bounded pre-generated phase queue and original random
position-generation order. Runtime condition selection is dynamic. On a terminal
response the adapter clears unused phases and calls the existing window.exit().
**No libC/Pyglet engine code was changed.** There is no requirement to exhaust the
queue or wait for an End screen. The generic engine still supports arbitrary
lists of phases and lists of simultaneously drawn stimuli.

New run-specific `<response-stem>.session.json` metadata records `completed`,
`max_trials_reached`, `aborted`, or `error` (with `running` during acquisition),
total responses, configured ceiling, per-staircase counts/streaks/reversals/final
value/configuration and completed/unfinished IDs. Completion on the final allowed
response is success if no staircase remains unfinished. Sidecar replacement is
atomic. Existing response files and saved JSON field names are not renamed.
Legacy response/history rewrites remain non-atomic; resume is not implemented.
Logger recording failures stop this run rather than allowing the legacy engine
to silently advance with inconsistent state. Display construction failures before
the event loop still require broader lifecycle/error-handling work.

Validation command: `python -B -m unittest discover -s tests -v`.
Result for this checkpoint: **37 tests passed** on the PATH MSYS2 Python 3.10.5;
all Python sources parsed and `git diff --check` passed.
Tests exercise actual pure/adaptor modules and temporary files; no fullscreen
window is opened. Rendering, audio timing and physical display accuracy remain
unverified, and this change does not certify the installation environment.

## Thesis context and generality checks

The attachment directory still contains no thesis PDF. A local candidate was
read at `../Latex/Papers_FOLDER/Thesis_PhD/thesis_corrections_tex/thesis.pdf`:
Alexander A. Minns, *Wave-Based Cortical Coupling as a Mechanism for Spatial
Frequency Selectivity and Gain Control*, 291 PDF pages, compiled 6 September 2026.
This is identified explicitly rather than assumed identical to the newly supplied
attachment. Relevant methods were read from Chapter 4 (printed pp. 121–143) and
Appendix A (including pp. 178, 183–184 and 205–206). No thesis files were modified.

Appendix A, equations A.1–A.2 (printed p. 178 / PDF p. 216), confirms:
`C_disp=(I_n-I_b)/(I_M-I_b)` and `I_n=I_b+C_disp*(I_M-I_b)`.
These describe normalized digital display contrast, not conventional Weber
contrast `(I_n-I_b)/I_b`. Runtime conversions implement this exact normalization.
The three reversed configuration calls are now fixed: start/max=1 and background=0
for the existing start-at-maximum configuration. This repairs metadata without
replacing the scientific definition or changing the configured starting drive.

Controlled naming migration:

1. New code uses `normalized_display_contrast` and
   `display_contrast_to_screen_intensity`; background/maximum are named arguments.
2. Keep `_to_weber` and the two older conversion function signatures as compatibility
   wrappers with explicit documentation of their actual C_disp meaning.
3. Rename local variables gradually in touched code; keep `weber_contrast_active`,
   `background_weber_contrast`, `max_weber_contrast` and the six legacy text-column
   meanings unchanged. Existing plotting code selects column 4 by position;
   downstream reference analysis uses a normalized-source contrast column.
4. Before any external rename, agree a versioned reader/export contract. Renaming
   saved JSON keys can break existing readers; the legacy text writer does not
   actually emit its supplied labels. Do not insert headers into old files or
   reinterpret post-update values as presented values.

The thesis clarification for increment probes does not, by itself, settle the CSF
grating shader: its current non-box branch uses `b + C_disp*m*sin(...)/2`, while
the inverse digital mapping yields `b + C_disp*(M-b)`. Keep that shader and its
gamut behaviour unchanged pending the owner's explicit decision. No calibration
measurements were imported as defaults. The thesis explicitly distinguishes
nominal 10-bit commands from certified end-to-end physical bit depth (pp. 205–206).

| Design stress test | Required boundary, not additional implementation now |
|---|---|
| CSF left/right localisation | Experiment supplies grating, spatial alternatives, phase timing and response correctness |
| Lateral base/flanker up/down localisation (Fig. 4.5, p. 128; p. 136) | Condition objects distinguish base/flanker and probe position; a phase can draw fixation, probe and flanker together |
| Ellipse two-interval task (Fig. 4.7, p. 141; pp. 142–143) | An experiment composes fixation, interval 1, ISI, interval 2 and response phases; auditory onset cues and keys 1/2 are experiment configuration |
| Multiple staircases per condition (Table 4.4, p. 130) | Stable staircase identity must be distinct from condition identity; no global one-staircase-per-condition assumption |
| Different rules (p. 138 and Appendix A Table A.1) | Per-experiment/participant configuration, never universal n-down defaults |
| Ring geometry/aspect ratio (pp. 139–140) | Stimuli accept their own geometry; neither core nor TUI requires spatial frequency or luminance fields for every stimulus |

Future `ExperimentSpec` supplies ID, name, description, configuration definition,
validation and builder/runner. The TUI shell handles participant/session,
experiment selection, applicable display profile, selected experiment fields and
review. Its universal form must not contain CSF-specific adaptive or stimulus
fields. Profiles/calibration are reusable capabilities, not requirements for every
possible procedure. Paper presets, if requested, belong within CSF configuration.

Next migration steps: decide the remaining renderer/calibration/recording
questions in small groups; approve package naming/environment; move tested pure
logic; introduce registry and experiment-owned configuration; isolate reusable
stimuli/core; then implement the generic TUI shell and launcher. Do not introduce
new thesis experiments or rewrite the phase engine merely to anticipate them.

## Historical baseline audit (before the approved changes above)

## Scope and evidence

Audited the 31-file tracked inventory, including all nine Python sources, the complete
599-line `libC.py`, editor configuration, bytecode inventory and ZIP contents.
Baseline: `a953e4a`; implementation branch: `refactor/public-v1`.
The existing local edits to `Functions/save_staircase_as_plots.py` and six
bytecode files were present before this audit and are preserved.
No experimental behaviour has been changed. No applicable AGENTS.md was found.

The sibling `Access_PNAS_psy_data` was inspected read-only: `pyproject.toml`,
`run_psyview.bat`, `scripts/launcher_setup.py`, `src/psyview/__main__.py`,
the app composition/navigation, UI module inventory, dataset browser, and
relevant PNAS analysis code. Nothing in that repository was modified.

The two named September PDFs were not found under the supplied attachment
directory or Physics tree. The comparisons below use the protocol details in
the user's request, not independently read manuscript text. No scientific
decision should be inferred from this report.

Static parsing succeeded for all nine Python files. Isolated probes of the
original function definitions reproduced the response, history, conversion and
termination defects without a window. This is not an application/rendering test.
These probes were subsequently superseded by the actual-module tests listed above.

## Inventory and responsibilities

| Tracked location | Contents and current responsibility |
|---|---|
| `Interface/` | `main.py`: executable setup and dispatch at import time; `config.py`: scientific defaults, directories, initial state and output; `settings.py`: unused `RENDER_GRAPHICS=False`; four bytecode files |
| `Experiments/` | `contrast_sensitivity_function.py`: sole experiment, monitor geometry, stimulus parameters and trial composition; three bytecode files |
| `Events/` | `adaptiveMethods.py`: conversions, response rules, audio, state IO, trial classes, termination; `stimuliC.py`: grating shader, fixation dot and text; seven bytecode files, including old `libC` caches |
| `Functions/` | `functionsForUse.py`: prompts, paths, JSON/text IO, geometry; `save_staircase_as_plots.py`: disconnected plotting helper; three bytecode files |
| root | `libC.py`: rendering engine and miscellaneous older helpers; two bytecode files; `packages.zip`; `.gitattributes` |
| `.vscode/` | `settings.json`: mostly personal theme/font/Conda/editor preferences; basic type checking is potentially useful project configuration |

There are 19 tracked `.pyc` files, no tracked scientific response data, no
README, dependency declaration, test suite, dedicated launcher or license.
The entry script is `Interface/main.py`, not root `main.py`.

Direct application imports:

```text
Interface.main -> Functions.functionsForUse, Interface.config
Interface.config -> Functions.functionsForUse, Events.adaptiveMethods
Interface.main -> dynamically chosen Experiments.<filename>
Experiments.contrast_sensitivity_function -> Functions, Events.stimuliC,
                                           Events.adaptiveMethods, libC, pyglet, numpy
Events.stimuliC -> libC.*, Functions.read_JSON, pyglet, numpy
Events.adaptiveMethods -> Functions.functionsForUse, math; local random/winsound
Functions.functionsForUse -> numpy, os, json
Functions.save_staircase_as_plots -> Functions, Events.adaptiveMethods, matplotlib
libC -> numpy, pyglet/OpenGL, ctypes and standard library
```

`Interface/settings.py` and the plotting helper have no inbound application
imports. `libC.run_key` references an unimported `keyboard`; `mainloop` references
Python-2 `Queue` and undefined `Presentation`/`sleep`. Neither is called on the
CSF path. FBO, lattice/mask/batch utilities and remote control are also outside
the present CSF call path; being unused here does not prove they can be deleted.

## Actual execution path

1. Import/execute `Interface/main.py`: change CWD, extend sys.path, create sibling
   `local_psychophysics_data`, automatically create `subject_1` if empty.
2. Enumerate all data-root entries as participants and all `Experiments/*.py`
   files as experiments. Use raw prompts; no typed validation or safe-ID contract.
3. NEW selects values; OLD reloads `experiment_defined.json`. Both subsequently
   configure a fresh run: OLD does not restore a staircase history or RNG state.
4. Import experiment module, rewrite participant setup, write global
   `user_experiment_config.json`; create run text and shared daily parameter files.
5. `run_experiment` rereads global config, opens fullscreen `ExpWindow`, obtains
   window dimensions and assumes physical monitor dimensions, constructs stimuli.
6. Prebuild a random left/right sequence for 30 response trials. Condition ID is
   selected separately at each `new_condition` event. Neither RNG state nor seed
   is saved.
7. `ExpWindow.on_draw_idle` emits TRIAL before starting the phase timer.
   `record_event` configures the next condition, reading/writing disk state.
8. Grating and fixation reread condition JSON in `draw`, including every frame.
9. Key events call the logger before checking the trial's accepted keys.
   The response callback loads history, beeps for 500 ms, calculates next value,
   rewrites conditions and the entire response file.
10. Timer uses `time.time()` and transitions on redraw; configured milliseconds
    are not measured screen-onset durations. A new-condition beep blocks the
    event callback before its phase timer begins.
11. A fixed queue ends in an indefinite End trial; Escape exits. The reversal
    flag is not connected to queue termination.
12. After `run()` returns, the first response row is removed and spacing rewritten.
    No `try/finally` protects this finalisation on failure.

## Priority table

| Priority | Independently verified finding | Consequence |
|---|---|---|
| CRITICAL | Response checker compares integer choice with global function; excludes current trial from filtered history | Adaptive sequence does not implement declared n-down/m-up rule |
| CRITICAL | Termination removes conditions but retains IDs; flag never stops trial queue | Wrong condition association or index failure; reversal stop not enforced |
| HIGH | Shader modulation, stored contrast and calibration have unresolved semantics | Physical stimulus contrast cannot be established from labels |
| HIGH | Config calls `_to_weber` with background/maximum reversed | Initial contrast metadata is wrong; runtime partly recomputes it |
| HIGH | Response rows contain post-update values; initial zero row affects ID 0 history | Trial/contrast alignment and reversal interpretation need confirmation |
| HIGH | Global config and same-day parameter files overwritten; non-atomic history rewrites | Reproducibility and crash recovery risk |
| HIGH | All response keys reach logger; exceptions are caught and converted into advancing behaviour | Unaccepted keys may update state, bad events may be skipped |
| HIGH | Per-frame disk IO, blocking sound, no onset/frame-drop records | Timing fidelity unverified |
| HIGH | No reproducible environment; import-order-dependent ZIP loading | Clean setup fails; installed graphics version may override bundle |
| MEDIUM | File-glob discovery, prompts, implicit participant, OLD is not resume | Unsafe extension and confusing researcher workflow |
| MEDIUM | No tests, documentation, explicit units/profile or package boundary | Difficult maintenance and contribution |
| MEDIUM | Plot helper uses `matplotlib` rather than pyplot and selects ID 2 twice | Helper fails and targets neither configured ID 0 nor 1 |
| LOW / cosmetic | Tracked caches and personal VS Code state | Repository noise; no evidence this itself invalidates trials |

## Scientific findings and decision boundaries

### Staircase rule and history

`Events/adaptiveMethods.py:184` (`subject_response`) binds a LOCAL variable named
`subject_response`. `_check_responses_history` at line 311 does not receive it;
its comparison resolves the GLOBAL function object. For normal integer choices,
the correct-response branch is unreachable. With n_up=1, a previous incorrect
response triggers an increase, previous correct triggers hold, and empty history
passes `all([])` and triggers an increase. The current response does not fix this.

Choice lists are appended before checking, but the staircase-ID list is appended
afterwards (line 279). `_get_single_staircase_history` indexes by that older ID
list, excluding the new response. The initial all-zero row masquerades as a
correct ID-0 trial. Even correcting the function comparison and alignment leaves
`min(len(history), n)` accepting too few observations and rolling windows
potentially reusing successes after a step.

Recommendation: pure per-staircase consecutive-success/failure counters, include
the current response exactly once, require the full run length, reset a streak
on the opposite outcome and reset it after a step. Keep step sizes and n/m
explicit. Alternative: overlapping recent-history windows, if deliberate.
This counter/reset rule was subsequently confirmed and implemented; see the update above.

### Contrast and calibration

`_to_weber(value, background_cpu, max_cpu)` computes q=(u-b)/(M-b).
This is a normalisation of display drive, not proof of luminance Weber contrast.
`Interface/config.py:122` passes `(u,M,b)` in all three calls. For b=.24, M=1,
it writes starting=-0, background=1, maximum=-0. However the active intensity
starts at 1 and new-condition/response paths recompute q with correct argument
order; the initial error does NOT establish that every displayed trial is zero.

The staircase multiplies q by powers of 10, reconstructs u=b+(M-b)q, clamps only
below b, and stores that drive. `Grating_ADM.draw` sends q to `contr`.
With `box=False`, the shader writes RGB `b + .5*q*Gaussian*sin(fs*x+phase)`.
Consequently q is also twice the peak sinusoidal drive amplitude. It is not the
recorded drive u used directly as the sinusoid's maximum. Values may exceed the
display gamut; no upper clamp/step-boundary policy is defined. Physical contrast
requires the laboratory's actual drive-to-luminance mapping.

`listLum` has 12 entries; `listCPULum` 11. UI selects maximum luminance,
background luminance and background drive independently. Physical background
luminance is retained in participant setup but not used in the active shader
conversion. No measured calibration function/profile is present. `box=True`
contains a different luminance encoding path but is inactive; current gamma=0
must not be repurposed as a calibration.

Recommendation: first confirm the intended numerical q and paired calibration,
then expose explicit quantities at the renderer boundary. Alternatives are
preserving drive modulation versus implementing calibrated luminance contrast.
Neither is selected here; do not invent a twelfth calibration observation.

Reference analysis uses `contrast_normalized_source`, detects reversals on that
quantity, and takes the median of the final N positive finite reversal values
(`psyview/analysis/interactive.py:50-87`); default N=8. It does not establish a
calibration for this repository or prove compatibility with its six-column files.
The current repository contains no threshold estimator or bootstrap procedure.

### Reversals and termination

`count_reversals_HighLow` ignores flat steps, records the last plateau point at a
direction change, and returns dummy [0] lists for <=1 point. The selection path
converts intensity to q, then `_count_staircase_reversals` converts it a second
time. With valid positive span the extra affine transform preserves directions,
so double conversion alone does not change reversal count; it remains semantically
wrong and obscures the variable's unit.

`_terminate_staircase_bool` requires `count > criterion`, not >=. Removing a
condition shortens the indexed list but not `staircase_Identities` or state arrays.
IDs can then index the wrong condition or fall outside the list. Last-condition
completion requires two checks, sets `[1]`, but fixation compares the whole list
to scalar 1 and falls through. Neither grating nor engine stops on the flag.

Recommendation pending approval: stable IDs plus active/completed sets, stop each
staircase at the confirmed reversal count, stop experiment when all complete;
record a separate incomplete/safety-cap outcome. Confirm reversal plateau
convention and whether 30 is an intentional cap before changing either.

### Geometry and manuscript comparison

`ratio_PIXEL_Meter` returns metres/pixel, opposite to its prose description.
Angle conversion implements symmetric extent `2*d*tan(angle/2)`; inverse uses
`2*atan(extent/(2*d))` and ignores its pixel-ratio argument. These are consistent
for a centred extent, not the exact formula for eccentricity `d*tan(angle)`.
Current code uses the extent conversion for displacement as well as width.

`fs` multiplies normalised texture x in sine WITHOUT 2*pi; its unit is radians
across the quad. Values 2*31.5=63 and 8*31.5=252 span approximately 10.03 and
40.11 cycles across a nominal 5-degree quad: roughly 2.01 and 8.02 cpd. Thus 31.5
may approximate 2*pi*5, NOT pixels/degree. Replacing it with measured PPD would
be an unjustified behavioural change. Central local frequency and angular extent
also differ slightly under exact perspective geometry.

| Parameter | Current code | Protocol supplied in request |
|---|---|---|
| Staircase | 2-down/1-up; broken implementation | 4-down/1-up |
| Log steps | +.35 / -.19208 | +.36 / -.30294 |
| Fixation/stimulus | 250 ms fixation; 250 ms blank/new-condition; 200 ms stimulus; 250 ms blank; response fixation; extra initial fixation | 500 ms fixation; 300 ms stimulus; response fixation |
| Position | Random left/right, nominal +/-5 degrees | +/-0.5 degree |
| Envelope | 5-degree quad; sigma .05 of width (~.25 degree), FWHM ~.589 degree | Approximately 1-degree spatial spread; definition needs manuscript |
| Conditions | Two IDs, one each for fs=63/252 | Up to four independent staircases per SF |
| End | 30 queued responses total; ineffective reversal flag, strict >10 | 10 reversals per staircase |
| Geometry | 610 x 350 mm assumed; current fullscreen resolution; distance 1 m | 27-inch 3840x2160; active 2560x1440; distance 1 m |
| Refresh/precision | 60 Hz parameter; actual mode/bit depth not verified or explicitly selected | 60 Hz, 10-bit grayscale |
| Keys | Advance constrained to arrows; logger additionally accepts shifts/up/down | Left/right arrows |
| Threshold | No estimator in this repository | Final 8 reversals; uncertainty samples 8 of 10 without replacement |
| Calibration/room | No measurement metadata or room instruction | LS-150 calibration, dark room |

These differences are not automatically errors. Recommend a generic CSF definition
with explicit protocol configurations, preserving a documented current-parameter
configuration and adding a paper configuration only after verification. For each
row the owner must choose historical reproduction, intentional alternative, or
configurable variants; do not assume which is the launch default.

## Data and compatibility

Output root is the repository's sibling `local_psychophysics_data`. Run folders:
`<participant>/DW2_UP1/<experiment>/max_cdm2_<integer>/<background>/<date>/`.
The response filename gets a numeric prefix. `parameters/Records_Parameters.json`
and `Records_condition.json` do not: later same-day runs overwrite them.
`user_experiment_config.json` is global across participants, and participant
`experiment_defined.json` is replaced on launch. Computed monitor geometry is
not saved with the response record.

The six numeric, headerless text columns are condition (shader fs), probe choice,
human choice, staircase ID, POST-UPDATE q, POST-UPDATE reconstructed drive.
`create_Text_columns` uses labels only to count zero fields. Normal exit removes
the first row unconditionally. Repeated cleanup would remove real data; a crash
may retain the sentinel. Whole-file rewrites are non-atomic and `zip(*data)` can
silently truncate unequal columns. No presented-vs-next distinction, timestamps,
RNG state, termination reason or schema version is recorded.

Recommendation: preserve a documented legacy reader/export, add immutable
per-session metadata and a versioned trial record distinguishing presented and
next quantities. Agree those meanings before new writes. Do not silently change
old files, relabel their columns, or claim OLD resumes a run.

## Dependencies, archive and reference lessons

`packages.zip` contains 233 entries: 232 under pyglet (including directory
entries), version string 1.5.19, and `wmi.py`. `libC` prepends this relative archive
to sys.path, but the normal experiment imports pyglet BEFORE libC, so the archive
does not reliably supply pyglet for startup. A direct libC import can resolve a
different version. No application WMI import was found.

The public upstream archive comparison was attempted but network access from the
shell was denied. Local modifications/unique bundle assets have NOT been ruled
out; preserve packages.zip until comparison succeeds.

The engine uses immediate-mode GL_QUADS, matrix stacks, ARB shader entry points,
and old batch APIs. Upstream documents incompatible OpenGL/context/batch/event-loop
changes in pyglet 2; it is not a drop-in environment choice:
https://pyglet.readthedocs.io/en/pyglet-2.0-maintenance/programming_guide/migration.html

PATH Python is MSYS2 3.10.5, with no discoverable NumPy, pyglet, matplotlib, Textual
or pytest distribution. Windows py launcher reports a 3.8 registration, which is
not evidence that it works. Cache tags 3.9/3.10/3.11/3.13 do not prove support.
NumPy and pyglet are runtime requirements; matplotlib belongs to optional plotting;
Textual will be a setup-UI requirement. No PsychoPy dependency was found.
No Python/NumPy/Pyglet combination is certified by this audit. Establish the
laboratory's working interpreter/package versions and test an isolated environment
before finalising constraints. The bundled 1.5.19 is a baseline candidate, not an
already verified installation recommendation.

Reuse reference patterns: module entry point, validated result returned by
`DatasetBrowser.run()`, OptionList navigation, clear errors/footer and responsive
layout. Its large fitting/plotting/threading machinery is unnecessary here.
Launcher lessons: repository-relative paths, compatible .venv reuse, dependency
hash and interrupted-setup marker, unchanged offline startup, log files, pip check,
fresh-process verification after editable install, preserved incompatible venv.
Do not copy its >=3.12 requirement or broad analysis dependencies.

## Minimum-risk migration

Proposed layout (package name requires owner approval):

```text
src/<approved_package>/
    __init__.py, __main__.py
    ui/           # Textual setup returns validated session configuration
    experiments/  # explicit ExperimentSpec registry and CSF composition
    stimuli/      # grating, fixation, modest draw/resource-lifecycle contract
    adaptive/     # pure state transitions, no window/audio/filesystem
    core/         # legacy engine initially preserved behind a boundary
    config/       # typed session/protocol/display/calibration structures
    data/         # run paths, records, legacy reader/export
scripts/          # Windows setup helper and audit aids
tests/            # pure units + separate optional display integration
README.md, pyproject.toml, run_psychophysics.bat, .gitignore
```

1. Preserve audit/baseline and existing edits; remove tracked caches from the
   index only and add scoped ignore rules as a separate housekeeping checkpoint.
2. Resolve staircase semantics, then write full-sequence/headless tests and fix
   approved behavioural defects separately from moves. Cover interleaved IDs,
   streak resets, reversal plateaus, bounds and complete/incomplete termination.
3. Resolve contrast/calibration, geometry/protocol, presented-vs-next data and
   environment decisions in small groups. Add round-trip/validation tests.
4. After name approval, introduce package and explicit registry; retain temporary
   entry/import shims. Initially move libC as a unit, not a graphics rewrite.
5. Introduce session-owned configuration/records and monitor profiles. Put physical
   dimensions/refresh/calibration in display profiles; timing, steps, cap and
   reversal count in protocol; condition/envelope in experiment; ID/path/seed in
   session; FOV/pixel conversions in derived geometry; graphics resources in core.
6. Build small Textual setup, exit it before constructing Pyglet resources; keep
   a non-UI runner. Do not expose resume until its state contract exists.
7. Add tested local setup/launcher, dependency consistency and import checks.
8. Document new-experiment/stimulus contracts, file schema, calibration, tested
   platforms and contribution steps. Obtain a license choice rather than inventing
   one. Validate on the actual laboratory display before public release.

Working milestone proposal toward 19 October: scientific decisions/environment
baseline by 21 September; tested core/config/data boundaries by 2 October;
TUI/launcher/docs by 9 October; laboratory validation and release fixes through
16 October, leaving the final days for the release review. This depends on timely
scientific decisions and access to the experiment display.

Naming recommendation for discussion: `psychophysics_lab` communicates scope more
clearly than generic `psychophysics`; availability/conflicts still need checking.
No distribution name, GitHub rename, license, calibration, protocol default or
backwards-incompatible data format has been selected.
