# Scientist-first authoring reference candidates (#165)

These are **executable external laboratory prototypes**, not replacements for
the ten official experiments. The framework, TUI, stimulus classes, adaptive
methods, recording schemas and installed laboratory sources are unchanged.
They require the current Python 3.11 Windows environment; follow the existing
[Windows environment guide](../../docs/WINDOWS_ENVIRONMENT.md).

## Read the science first

Each Python file follows the proposed
[version-1 standard](../../docs/EXPERIMENT_AUTHORING_STANDARD.md):
**Part A1 — Experimental choices** contains everyday parameters, factor levels,
targets, chronological events and measurements. **Part A2 — Scientific methods**
contains validated selection, scoring, effective stimulus conversion, updates,
stopping and estimators. **Part B — Framework integration** connects those
functions to the established runner and registry.
It does not define another condition system or execution engine.

| Researcher task | Gaussian CSF | Temporal before/after cue |
|---|---|---|
| Change the scientific factors | `frequencies_cpd`, `scientific_conditions` | `soa_ms`, `repetitions`, `make_conditions` |
| Change target alternatives/placement | `TARGETS`, `target_position` | `RESPONSES`, `target_x_deg`; target is temporal order |
| Select appearance | `GRATING_STIMULUS`; existing Gaussian class | `TARGET_STIMULUS`; existing line and fixation classes |
| Change timing/audio | `SESSION_START`, `trial_events`, two beep declarations | `SESSION_START`, `trial_events`, timing/audio fields |
| Understand the next stimulus | `choose_condition`, `change_contrast`, `update_experiment` | Complete seeded fixed schedule; no adaptive strength |
| Change what an answer means | `interpret_response` | `interpret_response`, `update_counts` |
| Identify saved measurements | `trial_measurements`, `MEASUREMENT_UNITS` | `trial_measurements`, `MEASUREMENT_UNITS` |
| Identify stopping/results | `is_finished`, `primary_rule`, selected reversal counts | Exhaust scheduled accepted answers; `results` |

Selected Configure/preset values override Python defaults. Changing a default
does not silently replace an existing selected value. Response keys follow the
declared alternatives in order. Inspect effective values in Review. Source edits
require restart and a new Test → Ready sequence.

CSF preserves the reference's frequency conditions, independent staircase
repetitions, seeded active-track/target draws, bounded log10 updates, reversal
convention and median/mean estimator. Fixed levels use the same existing planner;
they report cell accuracy without fitting a threshold. Digital peak-to-peak
modulation is not measured luminance contrast. Its two target rows can describe
a new spatial variation, but changing them creates a different protocol needing
its own review; that variation is not covered by baseline equivalence.

Temporal order uses signed **target onset minus visual-cue onset** in ms.
Negative means the peripheral line precedes the cue. The cue is a visible central
cross enlargement (0.2 to 0.7 degree arm length), not the unchanged fixation.
Both signs repeat equally; the complete schedule is shuffled once with the saved
seed. The first display's duration is included in the SOA; the intervening gap is
`abs(SOA) - first_duration`. Conditions with zero/overlapping/noninteger SOAs,
unpaired signs or excessive trial counts are rejected. It reports accuracy and
fraction “after” by SOA, **not** a fitted PSE/JND or validated temporal threshold.
Optional audio accompanies visual-cue onset and/or accepted answers. It requests
audio output; it does not establish acoustic synchronisation.

## Run in a disposable laboratory root

Copy this whole folder to a **new external folder**, separate from the checkout,
configuration and data directories. Do not copy over an existing lab. The
example namespace is `demolab`; both filenames exactly match `SPEC.id` and their
declared source paths:

- `experiments/demolab__csf_two_part.py`
- `experiments/demolab__temporal_order.py`

The old supplied `demolab__csf_readable.py`/`demolab__csf_two_part` mismatch is
resolved here; the original supplied file is untouched. Use a unique namespace
and matching filenames, IDs and source paths for a real laboratory's own work.
No experiment/stimulus is automatically promoted into the official repository.

From the disposable checkout, using its isolated Python environment (substitute
your new absolute lab path for `C:\PsyCoLab_Demo`):

```powershell
python -m psychophysics_lab --extensions-enable C:\PsyCoLab_Demo --trust-extension-code
python -m psychophysics_lab --dev-test demolab__csf_two_part --dev-values C:\PsyCoLab_Demo\presets\csf_check.json
python -m psychophysics_lab --dev-ready experiment demolab__csf_two_part
python -m psychophysics_lab --dev-test demolab__temporal_order --dev-values C:\PsyCoLab_Demo\presets\temporal_check.json
python -m psychophysics_lab --dev-ready experiment demolab__temporal_order
python -m psychophysics_lab --dev-list
```

The small check inputs are explicit software-test overrides, not default-config
files or a revised official protocol. Trust executes Python with your privileges.
These examples use existing official stimuli, so no additional local stimulus
Preview/Ready step is required. `--dev-test` writes only clearly identified
synthetic records. Software Ready does not waive acquisition safeguards. Both
prototypes retain an acquisition block pending independent protocol acceptance.

Generic Review uses the same `trial_events` definition as simulation and the
software presentation path. The final `make_trial` alias supports older callers;
it is not a second event list. Existing Review still expects its historical
planning function names; the small aliases/functions in Part B satisfy those
hooks without changing the TUI.

The CSF reference candidate now imports **no official experiment module** and
needs no reference-source hash pin. Its previously hidden scientific
initialisation, validation and estimator choices are inspectable in A2, using
the same existing numerical methods. Equivalence tests compare it against the
accepted official CSF. Future migration cannot create an official/example
circular dependency. Normal extension source fingerprints, Test → Ready and run
provenance remain in force.

For a short editing exercise: change frequency levels in `frequencies_cpd` or
`scientific_conditions`; change position meanings/keys/signs in `TARGETS`; change
durations/audio in `trial_events`; add the same named key to `MEASUREMENT_UNITS`
and `trial_measurements`; change reversal/response goals in the declared settings
and review A2 stopping/estimation consequences. In the temporal study, signed SOA
and event order must agree with scoring. Restart and Test → Ready after source
edits, inspect effective overrides in Review, then inspect synthetic saved data.
No framework or TUI source edit is needed. Changes to scientific meanings create
a deliberately different protocol and require renewed validation.

## Measurements and optional derived export

The canonical `trials.tsv` remains exactly 20 columns. Conditions, responses,
correctness, strengths, steps and reversals retain their established meanings.
Additional scientific scalars are in
`trial_events.jsonl` → `presentation.measurements`; their units are saved in
`resolved_experiment.json` → `measurement_units`. Existing manifests, stimulus
snapshots, action records and source hashes remain authoritative. Missing,
nonfinite or nonscalar declared measurements are rejected before presentation.

An optional read-only exporter adds units to a separate analysis table:

```powershell
python C:\PsyCoLab_Demo\export_measurements.py C:\DemoData\path\to\run_001 C:\Analysis\measurements.tsv
```

It refuses existing output files, output inside the original run, mismatched
measurement keys, or incomplete/duplicated accepted-trial measurement rows. It
does not import current experiment source to reinterpret historical records or
modify canonical data. Partial unaccepted displays are not fabricated responses.

## Validation and remaining acceptance

Run `python -m pytest tests/test_scientist_first_examples.py` from this branch.
The tests use disposable lab/config/data roots and the actual extension loader,
Test → Ready, canonical runner/readers and existing injected-display harness.
They compare CSF trial bytes, every adaptive update, reversal histories,
termination, estimators and resolved stimuli with current reference, using both
teaching and psychometric observers, adaptive/fixed modes and opening on/off.
The external callback's qualified source name is intentionally different;
its function AST is verified identical before that one provenance label is
normalised for action-record comparison. No scientific output is discarded.

The temporal example has no matching established official reference protocol.
Its evidence verifies its explicit signed-SOA schedule, response mapping,
determinism, updates, saved measurements and estimators. It does **not** establish
equivalence to a previously accepted temporal experiment.

Software checks include generic Review, invalid conditions, source readiness,
changed-reference refusal, custom measurement validation, read-only export,
response-key overrides, once-only opening and Escape before Trial 1. Injected
display tests execute the real software phase player with fake clock/window and
audio commands; they are neither native human TUI acceptance nor measurements
of physical display, input or audio timing.

Recommendation: the A1/A2/B arrangement is the selected **design-freeze proposal**;
approve it and the reference through PR #167 before any official migration.
Ask an
independent scientist to explain and safely edit all five authoring tasks in
Issue #165, then run Test → Ready and inspect saved results without assistance.
Independent usability remains NOT VERIFIED. The accepted six-section official
sources remain untouched pending maintainer approval of the standard and each
later family migration. See the [migration plan](../../docs/EXPERIMENT_MIGRATION_PLAN.md).
