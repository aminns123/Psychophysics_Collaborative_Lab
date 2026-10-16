# PsyCoLab: the beginner teaching workflow

**Researcher development:** Open the plain Python [USER_env terminal](USER_ENV.md). The normal TUI retains Build and source inspection; the optional `--dev-preview`, `--dev-test` and `--dev-ready` commands preserve Draft → Tested → Ready without a second graphical TUI.

This is the authoritative guide for new scientific components. The older
RESEARCHER_QUICKSTART and EXPERIMENT_AUTHORING_PROPOSAL describe earlier stages;
use this guide and PUBLIC_PROCEDURE_LIFECYCLE for the implemented public API.

## 1. Install and establish a rollback point

Use a checkout and Python 3.11. Create a virtual environment, activate it, then:

```text
python -m pip install -e ".[dev]"
python -m pytest
python scripts/portability_check.py
python -m psychophysics_lab --list-experiments
```

Record `git rev-parse HEAD`, the Python version and `python -m pip freeze` before
teaching. Once dependencies and this checkout are installed, the exercises need
no network connection. Keep acquisition data and machine calibration outside the
checkout. Do not copy calibration between physical setups as if it were verified.

To roll back, stop PsyCoLab, preserve the current checkout, and create a separate
checkout with `git worktree add ../psycolab-rollback VERIFIED_COMMIT`. Install its
dependencies in a separate environment. The pre-teaching-change reference is
`10695ea848b5c2b8606e4127864d224478b67ba2`; PR #35's tested P0 revision is
`aeef62f55496fa649428b314626eaaa1ca4d6834`. Do not reset/delete run data or local
calibration history. Older software may not understand new teaching experiments;
retain their producing version and immutable run snapshots.

## 2. Understand the three scientific components

| Component | What you edit | Framework responsibility |
|---|---|---|
| Stimulus | Parameter declarations and `render(parameters, x_deg, y_deg)` mathematics | Degree grid, monitor geometry, window, bounds checks, preview |
| Experiment | Conditions, order, task instructions, target interpretation and outcomes | Lifecycle, input events, timestamps, simulation, canonical saving |
| Adaptive method | How observations change a parameter | Registry, selection and persisted update history |

Scientific modules live under `src/psychophysics_lab/stimuli`, `experiments` and
`adaptive`. They import the public `psychophysics_lab.researcher` interface.
`configs/stimuli` contains shared default parameter JSON. `contributions.py` is the
documented registration list, not a framework registry implementation.
Normally do not edit `core`, `config`, `data` or `ui` to add an experiment.

The supported teaching renderer is a static grayscale raster with an ordered
phase-timeline wrapper. New experiments can sequence timed stimuli/blanks and a
response stage through `TrialTimeline` and `run.play_trial`. See
[EXPERIMENT_TIMELINES.md](EXPERIMENT_TIMELINES.md) for a fully worked authoring
recipe, CSF compatibility boundaries and the planned expansion to dynamic
flicker/SOA.

The underlying stimulus renderer is a static grayscale raster. The framework
provides angular coordinates and validates fit and spatial sampling. Pixel values
are normalized digital commands. Digital contrast is not calibrated optical
contrast; an experiment estimating optical contrast must declare luminance
requirements and use an appropriate scientific mapping. Per-frame animation, independently verified photon timing, special response
devices and advanced observer models remain separate extensions.

## 3. Run and inspect the reference exercise

Start `python -m psychophysics_lab`. On Experiment, choose **Orientation Task**,
select a display profile, and Configure. Set Accepted trials to 6 and Trial order
seed to 123. In Response mapping, `F,J` means negative then positive tilt;
letters, digits, arrows, SPACE and ENTER are supported. Escape always aborts.

Under **Stimulus Parameters**, choose the target stimulus. Select its default JSON,
then **Open / edit JSON**. Change `orientation_deg` to 45 or
`spatial_frequency_cpd` to 4. Enter a new preset name such as `tilt45` and choose
**Validate and save new preset**. Shared defaults are never overwritten. Select
the preset, inspect the summary, and **Reload and validate** after external edits.
An invalid/missing/changed file blocks Review until corrected and reloaded.

Choose Review → Run simulation → the teaching demo → Run. This uses a seeded
virtual observer; its accuracy is configurable. It renders through the same
scientific function without opening a hardware window. Simulation never qualifies
human acquisition. Orientation Adaptive runs the same stimulus with the existing
consecutive up/down staircase and saves each parameter update.

Inspect the resulting run directory:

- `manifest.json`: completion/abort/error, source hashes and provenance.
- `experiment_config.json`: exact experiment and response-key configuration.
- `stimulus_parameters.json`: independent slot identities, resolved JSON and hashes.
- `resolved_experiment.json`: trial order, task and presentation interpretation.
- `trials.tsv` and `trials_readable.txt`: accepted responses.
- `trial_presentations.json`: actual per-trial parameter overrides and reaction
  times in seconds, explicitly identified as virtual or software times.
- `procedure_lifecycle.json`: expected/accepted response counts and end state.
- `adaptive_history.json`, for the adaptive example: algorithm and update history.

Run `python scripts/validate_run.py PATH_TO_RUN`. PASS means the saved record is
internally consistent; inspect `status` to distinguish completed from aborted.
Changing a preset later cannot reinterpret an already saved run.

For a visible image without a monitor experiment:

```text
python -m psychophysics_lab --preview-stimulus teaching_gabor --preview-output gabor-preview.png
```

Open the resulting PNG. Add `--stimulus-json PATH_TO_PRESET` to preview your preset.
The TUI Preview button also creates a PNG in the local configuration's previews
directory and shows its path. Preview dimensions are illustrative, not physical
calibration. Existing CSF uses its established preview/presentation facility.

## 4. Create a new stimulus for an existing experiment

```text
python -m psychophysics_lab --scaffold my_grating --blueprint stimulus
```

The **Build Stimuli** TUI page also scaffolds the same pair of files. This
copies the working Gabor science into `stimuli/my_grating.py` and generates
`configs/stimuli/my_grating.json`. Edit the clearly marked PARAMETERS or render
sections. The declaration is the only source of parameter types, units and ranges.
Update JSON values to match any declaration changes. The framework supplies x/y
coordinates in degrees; return an array with the same shape and values in [0,1].

In the activated USER_env terminal, run `python -m psychophysics_lab --dev-preview my_grating` and `python -m psychophysics_lab --dev-ready stimulus my_grating` to test and publish the draft. Registration is automatic; manual editing of `contributions.py` is no longer required for new generated modules. Its
`family="orientation_patch"` makes it selectable in Orientation Task. Preview it,
select it in Stimulus Parameters, then simulate. Duplicate IDs fail explicitly.
Do not change the family merely to bypass scientific incompatibility.

## 5. Create a new experiment using an existing stimulus

```text
python -m psychophysics_lab --scaffold my_task --blueprint experiment
```

The **Build Experiments** TUI page provides this action as well. The scaffold
creates `experiments/my_task.py` and `configs/experiments/my_task.json`.
Edit `experiments/my_task.py` and its chronological phase JSON. The procedure
already reuses `teaching_gabor`, collects mapped
responses, saves data and supports simulation. Change trial count, ordering,
conditions or interpretation in the labelled sections. In the activated USER_env terminal, run `python -m psychophysics_lab --dev-test my_task` and `python -m psychophysics_lab --dev-ready experiment my_task`; then select the experiment in the normal TUI.

Use `--blueprint pair` (the default) to generate both a stimulus and an experiment
plus their JSON. This is a convenience, not a requirement to duplicate stimuli.
Existing files are never overwritten, including when one target already exists.

Declare calibration with `calibration_requirements=("geometry", ...)` and
`monitor_capabilities=("display_binding", "resolution")`. A scientifically justified
nonvisual procedure can explicitly declare `calibration_not_applicable="reason"`
and `monitor_capabilities=()`. Stimulus requirements are combined automatically;
a weaker experiment declaration cannot remove them. Simulation bypasses physical
measurements, not parameter validation. CSF retains its existing requirements.

The reference procedure calls `initialise`, `play_trial` and `complete`.
`play_trial` resolves the ordered phase JSON, validates/renders stimulus parameters,
collects a configured response, records its correctness and saves per-phase
observations. The earlier self-paced `present` API remains available. Use `abort` or `fail` when appropriate. Do not
catch these merely to label incomplete work successful. See
[PUBLIC_PROCEDURE_LIFECYCLE.md](PUBLIC_PROCEDURE_LIFECYCLE.md).

## 6. Reuse or create an adaptive method

Inspect `experiments/orientation_adaptive.py`: it selects the registered
`consecutive_up_down` implementation without copying the algorithm. The procedure
uses `run.adaptive(...)` and `run.update_adaptive(...)`; the latter persists each
update associated with its accepted trial.

For a new algorithm:

```text
python -m psychophysics_lab --scaffold my_step --blueprint adaptive
```

The generated module implements `respond(identity, correct, update_value)` and
`snapshot()`, and exports `AdaptiveAlgorithm`. Add its module to ADAPTIVE_MODULES.
Select it with `AdaptiveSelection("my_step")` in your experiment. The blueprint's
one-up/one-down rule is educational, not a validated replacement estimator for CSF.
Algorithms with additional constructor/control requirements must document them;
existing `AdaptiveSelection.controls` checks their declared configuration fields.

## 7. Resolve calibration on the relevant page

Use Calibrate → Display → Geometry → Spatial → Luminance → Timing → Review.
Luminance → Review or add saved luminance readings → Add any edited pair →
Accept luminance values → Timing records selection of the active mapping.
Acceptance does not turn synthetic readings into measured photometry. Human
Review identifies required physical checks and links to their relevant page.
Amber means saved but unverified physical evidence; green means the stated check
is satisfied. Setup record completion is still separate from human readiness.
Do not create new revisions just to navigate; acceptance and unchanged saves are
idempotent. Existing raw readings and historical revisions are retained.

## 8. Laboratory dry run (hardware status: NOT TESTED by this change)

1. Install the tested revision; run the offline teaching simulation and validator.
2. Detect and bind the actual monitor. Check resolution, refresh, OS scaling,
   physical screen dimensions and viewing distance.
3. Present the ruler. Measure it physically, record the error, and explicitly
   review Geometry. Run Spatial and record the observed pattern.
4. If the experiment requires luminance, collect genuine meter readings on
   Luminance, accept the mapping and record the separate photometer declaration.
5. If it requires timing, measure display onset independently and review Timing.
   The teaching task is self-paced; its software reaction times are not calibrated
   display/input latency measurements and must not be analysed as such.
6. Verify every configured response key, rejected keys, held-key behavior, Escape
   and window-close cancellation on the laboratory computer.
7. Review experiment-specific requirements, then qualify the setup where required.
8. Run a short permitted human session, one deliberate abort and inspect/validate
   both outputs. Record operator, hardware, revision, observations and date.

Do not describe this installation as qualified for human experiments until its
applicable physical checks pass. A failed hardware check prevents the affected
human workflow; offline authoring and simulation remain available.

## Troubleshooting

| Message/problem | Action |
|---|---|
| Missing/unknown JSON parameter | Match the Python parameter declaration; use numeric JSON values for numbers |
| JSON changed since load | Reload and validate, inspect the summary, then Review again |
| Duplicate ID/file | Choose a new module/preset name; remove no existing evidence |
| Unknown stimulus/experiment | Add its module to the appropriate contribution list and restart |
| Missing calibration declaration | Declare the actual requirements or a scientifically justified nonapplicable reason |
| Human acquisition blocked | Follow Review's first missing requirement; simulation is a separate mode |
| Procedure returned without complete | Record all planned accepted responses, then complete; abort explicitly if stopped |
| VS Code unavailable | Use the read-only TUI source viewer; edit scientific files in your installed editor |
| CSF condition error | In target JSON, keep number_conditions equal to the comma-separated condition count; preserve explicit units |

Practical exercise: create a new stimulus, set 45° and 4 cpd in a named preset,
create a new six-trial experiment reusing it, map responses to LEFT/RIGHT, simulate,
validate and find those exact settings and six response rows in the saved data.
