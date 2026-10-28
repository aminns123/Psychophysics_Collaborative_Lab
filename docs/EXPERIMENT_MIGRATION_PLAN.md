# Official experiment migration plan and scientific field map

**Prepared, not executed.** Governing proposal:
[version-1 authoring standard](EXPERIMENT_AUTHORING_STANDARD.md).
Baseline: main `a5aa56a9090340f5456b030c97d35ff1b2d1c371`.
All ten official source files and shared scientific implementations are unchanged.

## Inventory and compatibility assessment

Modes: O = original finite teaching; A = adaptive; F = constant stimuli.
“Compatible” means the current APIs can express the proposed structure, not that
a migrated implementation has already passed acceptance. No row authorises edits.

| Official ID | Modes/default | Scientific factors and target alternatives | Stopping / estimator; migration constraint |
|---|---|---|---|
| `example_experiment` | O/A/F; O | Selected line-offset magnitude; left/right targets; original alternates | O/A finite accepted count; F scheduled repetitions; no threshold. Retain the companion preset and original order. |
| `probe_above_below` | O/A/F; O | Selected vertical displacement; above/below targets; original balanced shuffle with selected `random_seed` | Finite responses / fixed schedule; no threshold. Retain simultaneous fixation/probe and observation markers. |
| `orientation_task` | O/A/F; O | Selected tilt magnitude; negative/positive targets, original selected-seed shuffle | Finite count / fixed schedule; no threshold. Preserve original stimulus-derived modulation versus added method strength. |
| `orientation_adaptive` | A/F; A | Same target signs/selected-seed shuffle; one adaptive teaching track | Finite accepted count, not reversal convergence. Preserve its own multiplier/floor behaviour and stimulus-derived starting strength. |
| `contrast_sensitivity` | A/F; A | Frequency; left/right targets; independent repeated tracks per frequency | Reversal completion; median last presented reversals, arithmetic mean across complete tracks; ceiling incomplete. Gaussian peak-to-peak digital modulation. |
| `contrast_sensitivity_windowed` | A/F; A | Frequency; left/right; same track policy, circular envelope controls | Same selected CSF estimator; circular aperture differs scientifically. Retain explicit one-way Gaussian-science reuse and both source dependencies. |
| `line_position_baseline` | A/F; A | Horizontal probe position; above/below target; required vertical displacement | Reversal completion; **geometric mean** of retained reversals, arithmetic across tracks. Probe increment, not grating modulation. |
| `line_position_flanker` | A/F; A | Horizontal position; above/below; separately selected flanker frequency | Same geometric estimator. Preserve local overlap/headroom resolution and background range [0.009, 0.991]; do not apply a remote flanker bound to non-overlapping probes. |
| `ellipse_centre` | A/F; A | Aspect ratio; probe/ellipse centre at x=0, ring present; first/second interval | Median reversal estimator. Preserve selected y/radius, ellipse inset/overlap limits, auditory cues at both onsets and required ring increment. |
| `ellipse_major_axis` | A/F; A | Horizontal position × aspect ratio × ring/base selection; first/second interval | Median reversal estimator. Preserve five-event two-interval order, common y coordinate, ring conditions and target interval meanings. |

All are **API-compatible by inspection** with A1/A2/B and the existing engine.
Future migrated implementations are **NOT VERIFIED**. The frozen main contract
fixture records exact fields/defaults, responses, safeguards, stimulus identities
and source hashes; this table is explanatory, not a replacement for that fixture.

The current teaching `SCIENTIFIC_SPEC` summaries retain some historical wording
(such as “None” for adaptation) while selected-method metadata describes the
actual added method. See [Stage C notes](STAGE_C_SCIENTIFIC_NOTES.md). Preserve
that distinction as baseline evidence; do not silently change scientific metadata
or repair unrelated error-message text during a structural migration.

## Condition / response / measurement field map

| Family | Established condition encoding / tracks | Responses and canonical target | Existing/additive custom observations and units |
|---|---|---|---|
| Gaussian/circular CSF | `frequency_cpd`; adaptive `id` + independent `repeat`; F has cell repetition and no adaptive track | Left/right, 0/1; default LEFT/RIGHT | Preserve `spatial_frequency_cpd` (cycles/degree), adaptive `staircase_repeat` and `grating_x_deg`; fixed `fixed_repeat`/presented strength. Additional position, target-name or envelope values must state degrees/digital units. |
| Two ellipse tasks | `value` string `x=...;ratio=...;ring=...`; adaptive `id`/`repeat`; F deduplicates tracks | First/second interval, 0/1; default 1/2 keys | Preserve adaptive `probe_x_deg`/`staircase_repeat` and fixed-repeat/strength/geometry keys. Add `target_interval` (explicitly 1/2), probe y (degrees), ratio (minor/major), ring-present boolean and requested probe increment. |
| Line-position tasks | Numeric horizontal position `value`, `x_deg`; repeated adaptive tracks | Above/below, 0/1; UP/DOWN | Preserve existing record meanings; add coordinates in degrees and requested **I_probe-I_background**, not peak-to-peak grating modulation. Target sign determines vertical placement, not a new condition/track. |
| Worked line example | Original `value` is signed offset; F shared planner uses the existing task label | Left/right, 0/1; F/J | Existing original `line_offset_deg`; finite method strength/counters remain automatic. Do not rename canonical condition semantics to fit a new factor vocabulary. |
| Above/below teaching | Original `value` names selected alternative; F uses existing task label | Above/below, 0/1; F/J | Existing original probe x/y in degrees; preserve per-method fixed-repeat/strength records. Additional uniform measurements must not delete existing method observations. |
| Orientation teaching | Original/A `value` may be signed orientation; F uses existing tilt-sign task label | Negative/positive, 0/1; F/J | Selected/resolved orientation in degrees and digital modulation. No threshold from finite adaptation. Preserve original/A starting-strength differences. |
| Temporal reference example (external only) | Signed target-minus-visual-cue SOA in ms; no adaptive track | Before/after, 0/1; F/J | Scheduled SOA, target position/durations, visible-cue geometry, repeat and optional-audio request. These are requested/software quantities, not photon or acoustic measurements. |

The legacy journal key `staircase_repeat` in the CSF prototype uses the selected
method's repeat: an independent track in A, a cell repetition in F. Its units and
method context must explain that historical name; it must not be used to claim
that fixed trials possess staircases. Existing official field meanings are not
retroactively rewritten.

Canonical columns remain: `trial_index`, `recorded_utc`, `event_time_s`,
`staircase_id`, `staircase_trial_index`, `stimulus_condition`,
`stimulus_position_px`, `target_alternative`, `participant_response`,
`response_key`, `correct`, `presented_display_contrast`,
`presented_screen_intensity`, `step`, `reversal`, `reversal_count`,
`next_display_contrast`, `next_screen_intensity`, `staircase_complete`,
`run_status`. Preserve blanks/unknowns and units as currently defined; software
timestamps are not physical latency measurements.

## Two-interval generality assessment

`ellipse_major_axis` already expresses the scientific sequence plainly:
fixation → interval one → ISI → interval two → response. The target interval
controls `probe_present` in its first/second slots. Position, ratio and ring state
define the scientific condition; independent repeats define adaptive tracks.
Two onset beeps remain at both intervals when enabled, without revealing which
contains the probe.

An isolated software test attaches the standard-shaped `trial_measurements` to
both its existing adaptive record and fixed probe record, preserving their old
keys and adding declared geometry/interval/strength values. Canonical trial bytes,
action plans, adaptive histories/session and primary results remain identical.
This proves compatibility of the measurement boundary with a two-interval task;
it is not an early migration or a new official ellipse implementation. No
ellipse source is written. Scientific changes remain subject to the future wave.

## Baseline evidence retained before any official edit

`tests/fixtures/authoring_standard_main_a5aa56a.json` records all ten exact current
source contracts and hashes of the shared runner, methods, renderer, event
execution and primary estimator. It references the unchanged Stage C frozen
scientific fixture by hash. That pack contains **46 cases**: all supported modes,
including original modes, with seeds 0 and 19. Existing tests compare those cases
with both empty and standard openings, including complete scientific traces,
and execute the real software phase player with the injected-display harness.

Keep those fixtures immutable as historical evidence. Before each migration
wave, capture that wave's **actual latest merged main**, complete effective
settings, seed/observer, condition/track plans, trial bytes, resolved stimuli,
adaptive histories/results, journal and source identities. If main's science has
changed since this checkpoint, establish a fresh reviewed baseline; do not use
an obsolete fixture as authority. Update the source-unchanged checkpoint test
only for explicitly approved migrated files, replacing it with stronger
before/after behavioural comparison rather than disabling equivalence checks.

## Five family-based PRs, after approval

| Wave | Files | Additional proof required before proposing merge |
|---|---|---|
| 1 | `example_experiment`, `probe_above_below` | O/A/F; alternating versus selected-seed shuffled targets; state counters/markers; preset overrides; explicit measurement declarations preserving method-specific records. |
| 2 | `orientation_task`, `orientation_adaptive` | All supported modes, their different starting-strength sources and finite stopping; zero/subnormal/upper-bound behaviour; tilt mapping and old saved-run meaning. |
| 3 | Gaussian and circular CSF | A/F; both envelopes, source dependency direction, active-track/target draw order, peak-to-peak convention, estimator and incomplete/boundary flags. No prototype import in official source. |
| 4 | Both line-position tasks | A/F; geometric estimator, required displacement/frequency, local flanker overlap/sampling and additive headroom, optional onset/accepted-response cues. |
| 5 | Both ellipse tasks | A/F; all position/ratio/ring cases, first/second mapping, interval/ISI timing and both cues, local headroom, centre/major-axis geometry and median estimator. |

Each PR remains small and retains one Python source file per public ID. Review
one wave's complete evidence before approving/merging it. Do not automatically
start or merge the next. Scientific corrections or shared-method extraction need
separate justification/regression review, not inclusion for file-length reduction.

## Per-wave acceptance and final repository qualification

For every migrated file require:

1. Identical defaults/bounds, condition values/order, track identities, resolved
   stimuli/parameters/placements, events/audio and calibration requirements.
2. At least the frozen seed/method/observer matrix, repeat determinism, canonical
   trial-byte comparison and every accepted-response adaptive state transition.
3. Complete/reversal, fixed schedule, finite count, safety ceiling, abort/timeout
   and error cases; matching scientific summaries and estimator eligibility.
4. Old/current readers and validation; 20 unchanged columns; retained existing
   journal observations plus separately tested, additive values/units.
5. Generic Review from the authoritative factory, selected/default/preset
   priority, response remapping and execution using the injected display path.
6. Test → Ready and source-change invalidation, official/external identity and
   provenance protections, with no grandfathered stale source approval.
7. Targeted checks, complete Windows suite, portability and final Windows CI for
   the exact reviewed head and current integration base.

If source paths/hashes, descriptive wording or additive measurements differ,
enumerate and assert those exact differences. Never drop all provenance, event
data or journal fields to obtain a green comparison. Synthetic trial time bytes
should match when their declared schedule/observer are unchanged. Real wall-clock
timestamps differ naturally; compare their meaning/validity, not fictitious
physical equivalence.

Only after all ten reviewed migrations: audit scientific readability across
families, repeat the complete Windows/portability and expanded deterministic
matrix, verify archived readers and byte-preserved laboratory roots, and publish
an experiment-by-experiment final equivalence report. Record every intentional
difference and remaining human/hardware item. No merge, release or tag follows
automatically. Independent Stage 4 usability, Stage 5 rollback and laboratory
physical qualification remain explicitly separate evidence.
