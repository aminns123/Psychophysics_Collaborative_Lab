# PsyCoLab authoring contract — one route

**This is the authoritative rule for all new experiments and visual stimuli.**

## The only normal researcher editing locations

- **Stimuli:** `src/psychophysics_lab/stimulus_library.py`. Add a
  `LibraryStimulus` class with `PARAMETERS`, `render(parameters,x_deg,y_deg)`
  and `SPEC`. Use a unique stable stimulus ID. Built-in shapes are complete classes in that file. Optional `Scene`
  utilities are imported from `core/scene_primitives.py`, a framework
  internal nobody must edit to add a class. No second registry, shape-dispatch
  edit, auto-generator or extra per-stimulus Python file.
- **Experiments:** `src/psychophysics_lab/experiments/<id>.py`, containing
  scientific defaults (`ConfigField`), conditions, geometry, trial ordering,
  timing, response meanings, adaptive choices and stopping rules. Companion
  JSON presets are optional. Export `SPEC` with its ID matching the filename;
  definitions are discovered without editing a registration list. A trial selects
  registered stimuli, places them in visual degrees, schedules `Show` and
  `CollectResponse`, updates scientific/adaptive state, and ends with
  `run.complete()`. A beep is an optional **experiment action**, never part of
  the pixel renderer.
- **External data:** the framework allocates participant/simulation runs and
  writes canonical output outside the Git checkout. The user never adds file
  writing to a `render()` method or a timed response callback.

## Required reading order and executable contract

Follow the [experiment folder guide](../src/psychophysics_lab/experiments/README.md)
and [implementation plan](EXPERIMENT_CONSISTENCY_PLAN.md). The current public experiment files follow the same seven-section narrative;
procedure details and loop structures remain experiment-owned, not artificially
standardised for convenience.
Conditions are named dictionaries; `prepare_stimuli(run, condition, state)` always
returns parameters by slot. `make_trial(settings, condition)` contains chronological
presentation, response collection and observation markers, with no update actions.
`interpret_response()` and `update_experiment()` execute explicitly inside
`run.trial()`, followed by the shared recording boundary. `is_finished()` owns
scientific termination. TUI-selected adaptive values remain authoritative.

The seven sections are settings/stimuli; conditions/order; stimulus preparation;
one trial; responses/updates/measurement fields; run/finish; framework connection.
Spatial 2AFC location tasks, single-interval binary judgment tasks and
**2IFC** (two-interval forced-choice) tasks use the same software contracts,
while stimulus presentations, response meanings and estimators remain explicit.
The two-response label alone is not evidence that two stimuli were presented;
see [scientific terminology](PSYCHOPHYSICS_METHODS_AND_TERMINOLOGY.md).

Only researcher experiment definitions belong at the top level of `experiments/`
(plus its required `__init__.py` and README). Framework machinery and saved-design
compatibility belong in `_internal/`. Normal researcher imports remain the public
`psychophysics_lab.researcher` API. The renamed public contrast-sensitivity source
retains its established saved-run ID through a documented internal source-name
map; new experiments still match their own filenames and IDs normally.

## Creation and validation

Write the code directly. The framework loads subclasses from the shared
library without editing registration files. To apply Draft/Test/Ready protection
to an experiment file, use:
`python -m psychophysics_lab --dev-stage experiment ID`;
`python -m psychophysics_lab --dev-test ID`;
`python -m psychophysics_lab --dev-ready experiment ID`.
Preview a visual renderer with `--dev-preview STIMULUS_ID`.

Published source fingerprints, calibration requirements and hardware
readiness are independent checks. Preview/virtual success does **not**
measure luminance, temporal precision or speaker onset.

## The CSF exception is internal, not a second authoring option

`ContrastSensitivityGrating` in `stimulus_library.py` exposes the new Gaussian grating
equation; `experiments/contrast_sensitivity.py` owns the new CSF settings and procedure.
The historical `CSFGrating` class still owns the reference GLSL shader source. The physical reference presenter,
file/event bridge and old staircase compatibility implementation live
**only** in `src/psychophysics_lab/_reference_csf/` until the shared
TrialTimeline/RunContext presenter is scientifically and physically
equivalent. Do not modify those internals to author a new experiment.

The top-level `Events/`, `Experiments/`, `Functions/`, `Interface/`
and `libC.py` paths have been removed. They are not competing public APIs.
The internal reference code is still scientifically active, not dead code.

See [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md) for the short walkthrough and
[CSF_ACTION_MIGRATION.md](CSF_ACTION_MIGRATION.md) for the remaining
validation gates.


## Scientific decisions retained internally

| Internal service | Why it stays central | Experiment-owned scientific choice |
|---|---|---|
| `core/scene_primitives.py` | Reuse shape/render equations across Scene compositions | Primitive types, sizes, amplitudes, positions, order and background |
| `adaptive/legacy_flanker.py` | One fixture-backed historical logarithmic update and reversal counter | Explicit n-down, log increments, initial phase, reversal/trial limits and global ceiling in each flanker experiment |
| `adaptive/staircase.py` | Shared consecutive-response counters and adaptive state | Selected n-down/n-up, initial phase and limits; numeric updates declared by each experiment, including thesis CSF |
| `core/timeline.py`, `core/trial_execution.py`, `researcher.py` | Resolve and execute the same phases for live and virtual responses; collect/save raw input and meaning | Ordered phases, durations, alternatives, correctness by index equality and update callbacks |
| `core/presentation.py`, `core/tone.py`, `config/` | Display creation/calibration, frame requests, devices and Windows beep output | When to display or beep and the requested tone parameters; no claim of measured photon/acoustic onset |
| `data/`, `core/runner.py` | Shared serialization, errors, immutable acquisition/provenance | Named scientific measurements and experiment source identity |
| `experiments/_internal/library_builder.py` | Interpret pre-existing saved JSON designs and test historical equivalence | New experiments use Python; the built-in spatial task is now `probe_above_below.py` |
| `_reference_csf/`, `simulations/csf.py` | Preserve the reference shader/event/adaptive bridge until physical/state parity is established | `_reference_csf/experiment_definition.py` retains the old phase queue and documents geometric/audio choices and virtual substitutions |

Base, Indirect Flanker and Ellipse 2D own independent procedure files; the
thesis-informed review documents further work needed for researcher readability.
Their matched scientific policies intentionally repeat; display, input, staircase
algorithms, audio and storage do not. Frozen pre-audit traces test the entire
trial plan, stimulus parameters, target/response meanings, adaptive states and
canonical trial rows, ignoring only relocated callback module qualifications.
The development acquisition blocks remain in force.


The thesis CSF is now a normal RunContext procedure, with its scientific sequence
in `contrast_sensitivity.py`. Historical CSF definition/validators live in
`_reference_csf/experiment_definition.py`; the old experiment ID remains available
for interpreting saved runs. Source consolidation did not make the older protocol
equivalent to the thesis, so their identities and acquisition qualifications remain distinct.

## Collaboration and local ownership

The current TUI supports local configuration presets, but the production
experiment loader does **not** yet import an external sibling
`PsyCoLab_Extensions/` source tree. Until that separately reviewed addition,
keep locally modified scientific Python on a branch/fork. See
[contributor workflow](CONTRIBUTING_EXPERIMENTS.md) and
[three-layer roadmap](INTERNATIONAL_LAB_ROADMAP.md).
