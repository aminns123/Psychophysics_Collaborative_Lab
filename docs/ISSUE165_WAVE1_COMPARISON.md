# Issue #165 Wave 1 — finite teaching experiments

Reference: remote `develop`, `93efe9cdc1e868b2898186b6f44f5482a2c72944`.
Only `example_experiment` and `probe_above_below` are migrated. Main/develop are
not modified. The other eight experiments and all shared mathematical methods,
recorders, stimuli, calibration and TUI code remain unchanged.

## Before and after

| Scientist's task | Six-section baseline | A1/A2/B implementation |
| --- | --- | --- |
| Find conditions | Target codes in `make_conditions`; fixed cell label inside planner | A1 explains target versus factor versus track, declares the fixed canonical label, and retains A2 schedule construction |
| Change placement | Sign mapping inside selection/preparation; vertical placement also in schedule construction | A1 `target_position` owns the same formula, called by those existing paths |
| Change responses | Paradigm near parameters, response event and prompt elsewhere | A1 alternatives, keys, authoritative events and participant prompt together |
| Change duration/order | Parameters and chronological events separated by session section | A1 keeps all timing fields, once-only opening and repeated `trial_events` visible |
| Find recorded measurements | Original-mode values embedded in recording callback | A1 `trial_measurements(settings, condition)` plus units; B projects the existing dictionary |
| Inspect stopping/results | Stopping section and shared method constructors | A1 states finite goals; A2 retains method selection policies, limits, scoring, updates and finish; no threshold estimator is introduced |
| Register/execute | Scientific initialization mixed with run setup | A2 `scientific_resolution`/`initial_state`; B initializes, records and connects the existing runner and registry |

Example, original line task:

```python
# Before: recording callback mixed requested geometry with infrastructure.
"measurements": {"line_offset_deg": offset}

# After, in A1 (same saved key/value):
MEASUREMENT_UNITS = {"line_offset_deg": "degrees"}
def trial_measurements(settings, condition):
    return {"line_offset_deg": condition["offset_deg"]}
```

Above/below similarly declares existing `probe_x_deg=0.0` and signed
`probe_y_deg`, in degrees. Requested geometry is not measured physical position.
The line magnitude still comes from the selected SimpleLine stimulus parameters;
the probe distance still comes from `probe_vertical_offset_deg`. Changing
stimulus appearance requires inspecting the corresponding stimulus class.

## Preserved science

- Public IDs, fields/defaults/bounds, slots/presets, keys and qualification
  declarations are unchanged. Both keep original, adaptive and fixed methods.
- Original line targets alternate 0/1. Probe targets are balanced then shuffled
  with the existing `random_seed`; odd counts retain the extra above target.
- These scheduled target rows are not independent staircase tracks. Finite
  adaptation retains one shared owned track, the existing n-down/n-up steps,
  0..0.5 increment bounds and accepted-response goal. No reversal threshold is
  estimated. Fixed mode keeps its original seeded levels/repetitions and target
  balancing, including odd-repeat policy and historical canonical cell labels.
- Original rendering uses selected stimulus intensity. Adaptive/fixed rendering
  still uses intensity `0.5 + selected increment`. Geometry/timelines/audio,
  accepted response interpretation and updates are unchanged.
- Ready SPACE and 1000-ms settling run once. Readiness is not a scientific
  response. Original event lists, RecordState markers and UpdateState names stay
  intact; `make_trial` remains the central legacy adapter to `trial_events`.
- Exactly the same 20 canonical columns, existing journal measurements, units
  metadata, results and incomplete-run semantics are retained. **No additive
  journal fields or new estimators are introduced.**

## Reference and comparison method

The two complete reference source files were copied **before editing** from the
verified develop worktree. Their SHA-256 hashes and reference commit are frozen
in `tests/fixtures/issue165_wave1/baseline.json`. Fixtures are test-only; official
experiments import neither fixtures nor prototypes.

`test_issue165_wave1.py` executes those frozen scientific callbacks through the
same current tested runner, using the original public module identity and source
location so resource/preset resolution and callback identity remain comparable.
It compares baseline, migration and a repeated migration run. Consequently its
runtime provenance resolves the current checkout; this test does **not** claim
that a migrated file retains its old source hash. The separately pinned reference
file hashes establish which original code is executed.

The comparison includes all three methods, three seeds/observer accuracies,
odd original counts and fixed repetitions, zero/max strengths, selected timing
and vertical-placement overrides, and openings enabled/disabled. It requires:

- byte-identical canonical TSV and complete trial journals;
- identical actions, full adaptive state/history, resolved experiments, effective
  stimulus parameters, event plans, saved results and run status;
- deterministic repeats, 20-column reader compatibility and run validation;
- unchanged fields/response paradigms/qualification requirements, seeded schedules,
  event definitions and invalid-setting rejection;
- readiness abort (zero accepted), third-response abort (two accepted), and
  timeout (zero accepted/error evidence with the existing propagated exception)
  for each experiment/method, preserving surviving records and adaptive state.

The existing Stage A frozen scientific fixture is not changed. Existing teaching,
session, Review/configuration, historical-reader and extension protections remain
part of the Windows regression suite. Source-reading tests now explicitly enforce
A1/A2/B for these two IDs while retaining the previous contract for the others.

Intentional differences are source layout, new readable declarations/functions,
module explanatory text, and resulting source hashes/line locations in provenance
or exception tracebacks. Scientific records are not normalized or broadly filtered
to permit differences. No shared scientific equation or old saved file is edited.

## Researcher acceptance and remaining boundaries

Version 1 works for these two finite teaching tasks: choices and the actual
chronology can be read first, and scoring/selection/stopping remain inspectable
nearby. Line count is not the acceptance criterion. No new DSL, runner, class
hierarchy or parameter store was introduced.

The original-mode measurement hook is editable in A1. Adaptive and fixed modes
retain their **existing** measurements in the shared teaching methods: adaptive
canonical/journal state comes from `adaptive_trial_record`; fixed records include
`fixed_repeat` and `presented_display_contrast` (digital increment). Adding custom
observations specifically to those shared methods still requires deliberate
method-hook knowledge. This migration does not disguise that limitation with an
unused all-method hook or introduce adapters to remove it.

Advanced changes to the adaptive engine, fixed schedule or canonical projections
still require shared-method/recording knowledge and scientific validation. B
retains the established callback signatures for compatibility. The historical
SCIENTIFIC_SPEC strings are preserved verbatim; their original-path wording must
not be mistaken for a claim that adaptive mode is unavailable.

Independent novice comprehension and native laboratory operation are **NOT
VERIFIED** by automated tests. Software tests do not establish physical display,
input or audio qualification. Maintainer review decides adoption of this wave;
no further wave, merge, version tag or release follows automatically.

Final test counts and exact-head Windows CI evidence are recorded in the PR.
