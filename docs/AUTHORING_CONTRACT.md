# PsyCoLab authoring contract (version 2)

**Read this before changing any generator, experiment or teaching text.**
One system, two ways to describe a trial. Do not silently copy one
experiment's scientific choices into another.

## Architecture (stable roles)

| Role | Source of truth | Researcher edits | Engine owns |
|---|---|---|---|
| Simple visual stimulus | `src/psychophysics_lab/stimulus_library.py` | One function per primitive; geometry/intensity arguments | Validation, immutable drawing recipes, calibrated rasterisation |
| Composition | `Scene` in the same library | Ordered drawings on one background | Safe recipe serialization; `composed_scene` registry adapter |
| Registered stimulus adapter / existing authored module | `src/psychophysics_lab/stimuli/<id>.py` + `configs/stimuli/<id>.json` | Parameter schema/defaults or compatibility rendering | Existing IDs and TUI loading remain supported |
| Simple spatial two-choice experiment | `configs/experiment_designs/<id>.json` | Stimulus library selections, condition positions, ordered actions, response labels/keys, timings | Shared `library_builder.py` procedure; no new experiment Python file |
| Advanced procedure | `src/psychophysics_lab/experiments/<id>.py` + `configs/experiments/<id>.json` | Condition algorithm, `TrialTimeline`, scientific state/adaptation | `RunContext.play_trial`, response collection, saving |
| Optional adaptive method | `src/psychophysics_lab/adaptive/<id>.py` | Adaptive mathematics | Tracking, integration and histories |
| Authoring status | `authoring/components.json` (Python) or `authoring/library_experiments.json` (JSON) | TUI/CLI Draft → test → Ready actions | Fingerprints, validation and publication |

**Identifiers:** for registered adapters, filenames, JSON IDs and `SPEC.id` must match. Public primitive functions share the single library and do not need individual files. A stimulus ID
names a reusable drawing component; an experiment ID names the *task*, not the
stimulus. Use names such as `white_line_probe` and `probe_above_below`, NOT
`new_probe_vertical_line_stimulus` for an experiment.

**Division of responsibility:** the stimulus defines **what** appears. The
experiment defines **when**, **where**, **which conditions**, **what a response
means**, and **how the scientific state changes**. The framework owns input,
monitor conversion, validation, provenance and data. No participant file I/O
inside `render()` or a timed action.

**Composition first:** `Scene(fixation(), line(x_deg=0, y_deg=2))` combines
drawings without per-object background rectangles. Pass `scene.parameters(8)`
for a slot selecting `composed_scene`, then use the usual `Show`/`CollectResponse`.
One slot has fixed parameters within a trial; use distinct scene slots for
different interval contents. Import primitives directly from
`psychophysics_lab.stimulus_library` so authoring fingerprints include that source.

**Compatibility placement:** `Stimulus("probe", x_deg=0, y_deg=2)` places an existing
registered stimulus in degrees relative to screen centre. Do not encode
between-condition position by editing the stimulus's internal pixel geometry.
Opaque patches are drawn in listed order: draw fixation first, probe last.

**Science is never implicitly selected:** the left/right example is a WORKED
EXAMPLE, not a blank experiment. New advanced Python scaffolds intentionally
raise `NotImplementedError` at the unfilled science sections; researchers
must define scientifically meaningful conditions and trial chronology before
simulation. For an immediately runnable basic experiment, use the JSON builder.

**Ready is not physical qualification:** preview and simulation do not show
photons or measure human key latency. Real participant runs require applicable
calibration, human readiness checks and hardware verification.

## Before adding anything new

1. Check the existing stimulus and experiment libraries for equivalent work.
2. Prefer a function in the shared library and compose it with `Scene`. Add new
   simple drawing mathematics in that one module. Registered specs and per-ID
   Python modules remain adapters or compatibility routes, not the preferred
   place to duplicate a line/ellipse/grating definition.
3. Prefer a JSON-only experiment for supported simple two-choice spatial tasks.
   Use an advanced Python procedure only for new scientific algorithms/actions.
4. New registered work gets a unique ID, two files for a Python authoring component or
   one JSON file for a simple library task. Never overwrite another author's
   `Ready` sources or rewrite historical runs.
5. Run software preview or virtual simulation, inspect outputs, then Mark Ready.
   A source/JSON edit invalidates the previous tested fingerprint.
6. Launch human acquisition only after separate monitor/protocol preflight.

## Existing lookalike experiments (do not delete)

| ID | Type/status | Interpretation |
|---|---|---|
| `probe_above_below` | Built-in Ready JSON design | Canonical reusable-library demonstration |
| `new_probe_vertical_line_stimulus` | Researcher-created Python experiment (Ready manifest entry) | User's above/below task; retain for past records. A later edit can make the source fingerprint stale, preventing loading until retested |
| `new_probe_fixation_test` | Researcher-created Draft Python experiment | Older copy partially changed from left/right to up/down; **not** a validated above/below experiment |
| `example_experiment` | Built-in Ready Python worked example | Left/right scientific demonstration, NOT a generator skeleton |

Do not silently remove a published experiment ID or migrate its scientific
semantics. A future archive/rename workflow must preserve historical
provenance and require explicit researcher approval.

## Authoritative reading order

Start at [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md). This contract defines
the permanent roles; [TRIAL_ACTION_ARCHITECTURE.md](TRIAL_ACTION_ARCHITECTURE.md)
describes the action system; [CSF_ACTION_MIGRATION.md](CSF_ACTION_MIGRATION.md)
states the separate, unfinished CSF hardware-equivalence boundary.

The source audit and development flanker/ellipse protocols are documented in
[LEGACY_STIMULUS_MIGRATION.md](LEGACY_STIMULUS_MIGRATION.md). Their human block is
deliberate: unresolved source choices and unproven display/audio equivalence
cannot be promoted Ready through calibration alone. Existing CSF remains the
authoritative acquisition implementation. `RunContext.complete_adaptive()`
records an owned algorithm's actual stopping status and retains the response
ceiling. Optional `record_from_state` projects declared scalar scientific state
into canonical non-engine-owned trial columns; response identity/correctness
remain owned by the runner.
