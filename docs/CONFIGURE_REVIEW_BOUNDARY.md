# Configure and Review: researcher workflow

Configure contains common run setup: the declared method selector, run limits,
trial count and random seed, when supplied by the experiment. Participant,
experiment, display and run intent remain on the existing setup page. Local
presets remain available. Configure has no scientific parameter or stimulus
panels.

Review is the scientific interface. Its existing table resolves the selected
experiment's declarations and planning functions: effective inputs and units,
conditions, stimuli, response meanings, session and trial chronology, method
rules, saved measurements, results and source locations. A representative
adaptive trial is labelled as representative; it is not a prediction of future
responses or a precomputed adaptive schedule.

## Editing

1. Open Configure, select common run settings, then open Review.
2. Select a scientific row and choose **Edit selected value** to focus its
   controlling input. Alternatively choose **Edit inputs / stimuli**
   to browse all declared inputs and stimulus slots.
3. Change the value using the existing controls, then **Apply to Review**.
   Review is regenerated from those selected values. Invalid edits stay in the
   editor; the previous reviewed request is unchanged. Back cancels application
   of the edit and retains the draft for correction.
4. Source links, ordinary JSON editing/reloading, presets, stimulus default
   adoption and F5 refresh remain available. An experiment-controlled stimulus
   value links to its controlling input; a computed value is not presented as
   an independent editable setting.

Some experiments intentionally require an input with no scientific default
(for example an ellipse ring increment). Review can show that incomplete
draft and its declared inputs. All run actions remain blocked until the same
existing validators accept it. Derived scientific rows are generated only
after the inputs can be resolved. No value is guessed to make Review available.
Changed or missing selected files must still be restored/reloaded and reviewed;
opening Review does not approve them.

## One generic implementation

`ExperimentConfigScreen` selects only common field roles.
`ExperimentParametersScreen` is Review's generic editor. Both reuse the existing
form implementation, `ConfigField` types/bounds, stimulus panels, drafts,
presets and validators. There is no experiment-ID dispatch, new parameter
format or second scientific definition. Existing execution, recording,
calibration, extension Test/Ready and provenance checks are unchanged.

An author uses the existing public experiment API: declare fields (including
units and optional sections), response alternatives/keys, stimulus slots and
defaults, session events, `trial_events`, planning functions and measurement
units. See [the authoring standard](EXPERIMENT_AUTHORING_STANDARD.md). An older
extension without planning hooks still shows its literal inputs and source
inspection guidance, rather than invented derived science.

## Demonstration and regression evidence

Before this correction, Configure included expandable adaptive, condition,
timing and stimulus panels. The grouping was shared, but the location violated
the Configure/Review boundary. After this correction those same controls are
reached through Review; the console styling and scientific definitions are
unchanged.

`tests/test_configure_review_separation.py` exercises the real shared Textual
screens for:

| Experiment | Input edited through Review | Declaration source |
| --- | --- | --- |
| Gaussian CSF | Gaussian sigma, degrees | Official CSF |
| Ellipse Centre | Ring radius, degrees | Official Ellipse Centre |
| Ellipse Major Axis | Vertical target position, degrees | Official Major Axis |
| Independent alternating flash | Flash distance, degrees | Private test extension |

The independent test experiment is in
`tests/fixtures/review_independent_lab/experiments/auditlab__alternating_flash.py`.
It imports the public researcher API, not an official experiment. It declares
alternating left/right conditions, Z/X responses, SPACE readiness, a timed
flash and per-trial position/exposure measurements. No TUI file knows its ID or
custom parameter names. The test performs Test → Ready, generic Configure →
Review → edit → validation/cancellation, source navigation, two deterministic
simulations, saved-run reading/validation and source-change Ready invalidation.

### Both authoring locations, with a laboratory-owned stimulus

`tests/test_independent_authoring_routes.py` additionally runs a newly authored
annulus-before/after-cue experiment and its own numerical annulus renderer.
These sources are in `tests/fixtures/review_temporal_lab/`; neither imports an
official experiment. Scientific conditions are whole-millisecond cue gaps,
alternatives are before/after a visible CUE label with B/A keys, and saved custom measurements
include gap, radius, position, exposure, digital increment and target order.
It explicitly offers the existing finite teaching adaptive method and constant
stimuli; neither is presented as a validated threshold estimator.

The same definitions are exercised in fresh interpreters in both supported
layouts, with only their declared relative source paths adjusted:

- A Python experiment inside a disposable copy of `src/psychophysics_lab/experiments/`,
  plus its stimulus class in that copy's `stimulus_library.py`. Normal discovery
  finds them without a registry, contribution-list or TUI edit. This does not
  add a new curated official experiment to the released repository.
- A separate, explicitly trusted `PsyCoLab_Extensions/experiments/` folder and
  its own `stimulus_library.py`. Before Test → Ready, ordinary simulation cannot
  select the draft. Trust is mandatory; it is not inferred from opening Review.

For each layout and each method the tests exercise the actual shared screens,
generic input and stimulus editors, missing/invalid draft correction, local
experiment/stimulus preset save and reload, fresh-process F5 checking/restoration,
two deterministic canonical simulations, 20-column data, custom measurements,
provenance and saved-run reading/validation. Source links must open the exact
laboratory Python file, including when a same-named decoy exists in the project.
The external case performs actual synthetic Test → Ready and verifies deliberate
source-change invalidation and disabling trust. Unqualified human acquisition
remains blocked. All source/UI/registry bytes are checked for unexpected writes
before the deliberate private source-change test.

Existing tests of scientific inputs now target the Review editor. Their
scientific assertions, frozen references, bounds and safety checks are retained.
The new root-navigation tests additionally verify that Configure has no hidden
scientific widgets or stimulus panels. Refresh tests preserve selected files
and incomplete scientific drafts across a fresh interface.

These are automated Windows software interface tests. They do not establish
independent human usability, native display/keyboard acceptance or physical
apparatus qualification. The existing working installations are not changed by
this candidate.

## Short native acceptance exercise

For CSF and each ellipse experiment, open the candidate and use Configure →
Review. Confirm Configure contains only common controls. For an ellipse,
supply the required ring increment through Review before expecting derived
science or run availability. Edit one scientific value, apply it, inspect its
units/meaning/source and inspect a stimulus row. Attempt an invalid value,
confirm the draft is retained, then cancel and confirm the reviewed value is
unchanged. Switch adaptive/constant stimuli where supported and confirm the
table describes the selected method. Preview/Test and acquisition retain their
normal calibration, readiness and hardware requirements.
