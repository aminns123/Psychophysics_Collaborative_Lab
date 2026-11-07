# PsyCoLab — One scientist-first authoring model

All ten official studies follow the scientist-first model integrated in
[PR #207](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/207).
Read one experiment Python file and the independent stimulus classes it names
in `stimulus_library.py` to follow the protocol and rendering. Use the
[authoring standard](EXPERIMENT_AUTHORING_STANDARD.md) for new studies.

## Scientific reading order

| Section | Authority | Purpose |
| --- | --- | --- |
| A1 — What, where and when | STIMULI, scientific conditions, SESSION_START, trial_events, responses | Visible objects, degree coordinates, layer order and timing |
| A2 — How and how much | prepare_stimuli, adaptive/fixed choices, steps, threshold estimation, units, stopping, SCIENTIFIC_SPEC | Definition of a scientific measurement |
| B — Existing shared execution | procedure, methods, validation, presentation, recording, analysis | Reuse validated universal machinery without duplicating science |

STIMULI is the **single** scientist-owned mapping from slot to independent
library class. Do not duplicate it with STIMULUS_SLOTS or STIMULUS_DEFAULTS.
The ordered Show(..., stimuli=(...)) list defines appearance and overlap.
The default blend is over; explicitly declare blend="add" for additive
digital increments. Stimulus classes own their own validation, geometry,
raster and alpha; experiments own spatial placement, conditions, response
interpretation and methods.

## Selected values in Review

Declare fields with meaningful units, ranges and help text. Configure supplies
common run controls. Review uses the selected study's declarations and trial
plan, and directs edits to the controlling input or stimulus parameter.
Researchers save selected values in local JSON. Python changes are for
developing protocol rules, rendering or reusable stimulus definitions.

The optional bright-probe explanation uses the official ellipse and line
protocols' declared contrast convention, step controls and planning hooks.
An independent study with its own intensity or background controls uses its
own declared meanings. See [Review parameter authority](REVIEW_PARAMETER_AUTHORITY.md)
and [sharing selected values](SHARING_CONFIGURATIONS.md).

## Probe semantics

The four ellipse/line studies adapt or present a raw nominal **digital
probe increment**, Delta_I = I_probe - I_background. That remains the
scientific unit of the saved contrast-related trial fields and thresholds.
The independently reusable ProbeLine displays a fraction of the available
digital headroom:

    ProbeLine.display_contrast = Delta_I / (1 - I_background)
    Delta_I = ProbeLine.display_contrast * (1 - I_background)

The experiment makes that conversion in prepare_stimuli. It must never
silently relabel this quantity as calibrated optical or Michelson contrast.

Adaptive and fixed preflight must evaluate the *actual ordered composed
phase* using the chosen target and monitor-pixel geometry. Ring/flanker
overlap, fixation attenuation, clipping and non-0.5 backgrounds matter.
Presentation must independently reject nonfinite or out-of-gamut pixels;
synthetic sampling is not a hardware qualification.

## Saved setup compatibility

Current slots are separate names: probe, ellipse, flanker and fixation.
Old configuration files sometimes stored a combined detection_scene in
first/second/fixation slots. The explicit version-bound importer in
config/stimulus_parameters.py translates unambiguous historical *setup*
dimensions, preserving source hashes and refusing conflicting widths,
lengths, backgrounds or mixed source versions. It does not infer trial
targets, per-trial positions or scientific strengths from old defaults.
Historical recorded runs stay byte-for-byte unchanged and remain readable
through the existing data readers.

## Frozen historical science

outdated_code/pre_atomic_207/ contains exact source blobs for the old four
experiments, old stimulus library and old methods, identified by original
Git hashes. It is not importable or registered as part of live PsyCoLab.
A test-only historical oracle extracts the frozen DetectionScene renderer,
without registering it, to compare actual pixels against independent
stimuli. Keep old evidence, source hashes and trial data immutable.

The new independent-slot serialization intentionally differs from the
old compound scene. An old and new JSON hash mismatch is not itself
proof of scientific drift, but it is not permission to discard the test:
compare event chronology, visual pixel commands, condition/target geometry,
state updates, thresholds and recordings semantically; report provenance
shape changes explicitly. Never rewrite frozen scientific fixtures.

## Scientific validation

- Ten official experiment authoring files use the single mapping and
  independently declared trial events and method parameters.
- All four migrated detection experiments pass adaptive and constant
  stimuli as appropriate, including headroom, background and overlap tests.
- Independent rendering is validated against historical pixels with no
  silent clipping; event timing and response outcomes are checked.
- Review navigation, refresh, saved-setting migration and old-data reading
  work without a live composite-scene dependency.
- Hosted Windows CI checks the software. Native Windows 11 acceptance and
  apparatus measurements are recorded separately for the scope they verify.
