# Stage C: all official experiments in chronological Python

Stage C migrates the eight remaining official experiments and both bundled
laboratory starters. Gaussian CSF and Ellipse Major Axis retain their accepted
Stage B implementation. The [code philosophy](CODE_PHILOSOPHY_AND_CONTRIBUTIONS.md)
remains authoritative. There is no new runner, registry, parameter store,
event type or experiment-specific TUI code.

## Accepted starting point and scope

At intake the authoritative checkout was clean `main` at
`359bf663b233178b25a338ab09332357bb57bd78`, also the freshly fetched `origin/main`.
PR #155 was merged at that commit; its reviewed implementation was `5269b74`.
Stage A (#153) and the philosophy document (#154) were already merged.
Work uses the isolated `event-first-stage-c-20261027` worktree and
`feat/event-first-stage-c-20261027` branch. The active laboratory checkout,
installed extensions, calibration and participant records are outside this work.

The only intended behavioural addition is the approved once-only opening in
the eight migrated experiments and the new starter templates. Existing trial
events, defaults, cue policies, geometry, strength equations, condition RNG,
updates, stopping and results are preserved. Stage A/B fixtures are retained
unchanged. No physical qualification is inferred from the evidence below.

## Inventory and per-experiment equivalence

All rows use PARAMETERS → SESSION START → TRIAL EVENTS → SCIENTIFIC RULES →
STOPPING AND RESULTS → FRAMEWORK REGISTRATION. The table's event order omits
nonvisual RecordState markers, which are retained in the actual declarations.
Each row passed frozen full-run comparisons with opening disabled and enabled.

| Official identity | Migration | Repeated display/response order | Methods tested | Frozen comparisons, off/on |
| --- | --- | --- | --- | --- |
| contrast_sensitivity | Stage B retained | fixation → Gaussian grating → left/right | adaptive, constant stimuli | 4 / 4 pass |
| contrast_sensitivity_windowed | Stage C | fixation → circular grating → left/right | adaptive, constant stimuli | 4 / 4 pass |
| ellipse_centre | Stage C | fixation → interval 1 → ISI → interval 2 → first/second | adaptive, constant stimuli | 4 / 4 pass |
| ellipse_major_axis | Stage B retained | fixation → interval 1 → ISI → interval 2 → first/second | adaptive, constant stimuli | 4 / 4 pass |
| line_position_baseline | Stage C | fixation → probe → above/below | adaptive, constant stimuli | 4 / 4 pass |
| line_position_flanker | Stage C | fixation → probe with flanker → above/below | adaptive, constant stimuli | 4 / 4 pass |
| orientation_adaptive | Stage C | fixation → tilted Gabor → blank → negative/positive | adaptive, constant stimuli | 4 / 4 pass |
| orientation_task | Stage C | fixation → tilted Gabor → blank → negative/positive | adaptive, constant stimuli, original | 6 / 6 pass |
| probe_above_below | Stage C | fixation → displaced probe → blank → above/below | adaptive, constant stimuli, original | 6 / 6 pass |
| example_experiment | Stage C | fixation → line → blank → left/right | adaptive, constant stimuli, original | 6 / 6 pass |

Contrast/detection staircases retain their existing reversal-completion criteria,
safety ceilings and estimators. The four teaching experiments have finite
accepted-response goals; their adaptive variants do not estimate scientific
thresholds. Constant-stimuli runs exhaust the selected schedule and retain their
existing performance reporting, without introducing a fitted threshold.

## Final researcher-facing API

```python
# 2. SESSION START — ONCE
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]

# 3. TRIAL EVENTS — REPEATED
def trial_events(settings, condition):
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("probe", slot="first", duration="stimulus_ms"),
        CollectResponse(actions=("above", "below"), slot="fixation"),
    ]
```

This shortened line-position illustration omits its existing optional cue
expression; actual source retains it. Change the key/duration literals or set
`SESSION_START=[]` without adding a Configure field or touching the TUI.
Register the pure session fixation slot in PARAMETERS. Gaussian fixation follows
the selected background for contrast/detection protocols. Geometry-only teaching
protocols use the existing fixation cross on grey 0.5. No opening contains a
grating, probe, ring or flanker, and no luminance requirement is added to teaching.

The experiment calls `run_contrast_experiment(trial_events=trial_events, ...)`,
or passes the list to the existing `run.trial()` boundary. Each condition's
effective strength is prepared from the latest scientific state. The framework
executes the same definition for acquisition, simulation and generic Review.
The final registration retains `make_trial = legacy_trial_factory(trial_events)`
for callers using the older TrialTimeline interface. No compatibility code is
removed and no second definition is maintained.

## Before/after and the researcher edit map

Before Stage C, most files declared `make_trial()` returning
`TrialTimeline((...))` after their condition/preparation helpers; scientific
declarations and registration were interspersed with the procedure. The circular
CSF exposed `make_trial = csf.make_trial`, hiding its display order in another
experiment. Neither group exposed the approved once-only opening locally.

After Stage C, each file presents its opening and flat repeated sequence before
its selection/update rules. For example, Ellipse Centre visibly retains:

```python
return [
    Show("fixation", slot="fixation", duration="fixation_ms"),
    Show("interval_one", slot="first", duration="stimulus_ms", beep=cue),
    Show("inter_interval", slot="fixation", duration="isi_ms"),
    Show("interval_two", slot="second", duration="stimulus_ms", beep=cue),
    CollectResponse(actions=("first", "second"), slot="fixation"),
]
```

The circular CSF now shows its local fixation/grating/left-right list and signed
`grating_offset_deg` placement directly. Its circular aperture, edge mode and fade
remain in PARAMETERS and `prepare_stimuli`. Named shared CSF functions still own
the common frequency/side selection, adaptation and estimation. These shared
scientific functions, common ConfigFields and the existing method objects are
the deliberate remaining abstractions: copying their mathematics would make
maintenance less reliable. The circular and Gaussian identities remain distinct.

The beginner starter demonstrates ordinary list composition:

```python
def fixation_events(settings):
    return [Show("fixation", duration="fixation_ms", instructions="+")]

def trial_events(settings, condition):
    return fixation_events(settings) + [
        RecordState("before_line"),
        Show("line", slot="target", duration="stimulus_ms", beep=None),
        Show("blank", duration="interval_ms"),
        CollectResponse(actions=("left", "right"),
                        timeout="response_timeout_ms", beep=None),
        RecordState("response_received"),
    ]
```

Replace `beep=None` with `Beep(550, 35)` on Show for an onset request, or
`Beep(750, 35)` on CollectResponse for an accepted-answer request. These examples
do not enable new official trial sounds. The existing official cue choices and
their response meanings are preserved exactly.

| Researcher question | Source location in the six sections |
| --- | --- |
| Which parameters and response keys may I choose? | PARAMETERS: FIELDS, RESPONSES and stimulus slot/default declarations |
| How do I start, settle or disable readiness? | SESSION START: key, duration and the whole SESSION_START list |
| What appears, in which order, for how long? | TRIAL EVENTS: flat Show/CollectResponse list and named duration fields |
| Where does the stimulus appear? | TRIAL EVENTS placements and nearby prepare_stimuli using the selected condition |
| Which onset/accepted-response cue is requested? | TRIAL EVENTS: optional beep on the corresponding Show/CollectResponse |
| How is the next condition chosen? | SCIENTIFIC RULES: make_conditions/choose_condition and the named shared scheduler |
| What does the answer mean? | RESPONSES plus SCIENTIFIC RULES: interpret_response |
| What is the response-dependent next strength? | SCIENTIFIC RULES: explicit update_experiment or named shared teaching method |
| When does the staircase/study stop? | STOPPING AND RESULTS: is_finished, limits and method-specific completion |
| How is the result computed and saved? | STOPPING AND RESULTS: primary_rule/finish_experiment/trial_record; shared canonical recorder |

## Scientific equivalence evidence

Before production edits, `tests/fixtures/stage_c_baseline_20261027.json` captured
46 complete runs from exact merged Stage B `359bf663b233178b25a338ab09332357bb57bd78`:
all ten experiments, both methods, seeds 0 and 19, plus original modes of the
three teaching examples at both seeds. True adaptive protocols complete four
reversals and retain two with a 512-response safety ceiling; teaching runs use
ten accepted responses. Fixed schedules use zero and .01 at two repetitions.
The observer is TeachingObserver(accuracy=.65). Full selected values are frozen
per case, including varied frequencies, positions/aspect ratios and required
scientific choices.

The new test group passed **152 tests**:

- **92 frozen run comparisons:** all 46 cases with opening disabled and enabled.
  Hashes compare every canonical response row, complete trial plans and resolved
  stimuli, response interpretations, complete initial/final state, adaptive
  histories/session, reversals, stopping and primary results where applicable.
  The scientific projection removes only the added `ready_fixation` slot's
  session provenance. Source hashes and software session timing are expected to
  change. With opening disabled there is no session sidecar; with it enabled the
  sidecar has exactly readiness and settling, without a scientific response.
- **20 injected-display comparisons (40 software runs):** both methods for every official
  experiment compare opening off/on through the actual presentation phase player,
  preserving Trial 1, trial plans/parameters, rows, states and primary results.
- **10 Escape-at-readiness cases:** the ordinary presentation-test runner saves
  zero-response user aborts, and the read-only validator accepts their records.
- **10 default/response/safeguard checks**, **10 scientific source-body/six-section
  checks**, and **10 generic Review/authoritative-factory checks**. Scientific
  source-body hashes exclude the intentionally changed event/registration/
  procedure functions; only saved-plan spelling is normalized for four teaching
  initializers. All scientific function bodies otherwise match the frozen source.

The prior Stage A/B fixtures and regression tests remain. The extension group
passed **94 tests, 1 skipped**, including both updated starters, both strength
methods, source fingerprints, no-overwrite protection and an archived pre-Stage-C
starter that loads/runs unchanged with no opening. It retains its own custom
stimulus's separate Preview/Ready requirement. Historical readers/validators do
not import current experiment code to reinterpret saved science.

Complete Windows regression and GitHub CI outcomes for the exact final revision
are recorded in the Stage C PR. Windows is the requested acceptance platform;
the existing CI matrix is retained. A partial run is not final acceptance.

## Changed files and boundaries

- Eight remaining official Python files: chronological declarations, approved
  opening, existing scientific functions rearranged cohesively, final compatibility
  registration. Four teaching initializers record plans from `trial_events`
  directly. Stage B's two official source files are unchanged.
- Two bundled extension files: the same style, composable lists and optional-cue
  comments. Installed laboratory sources and provisioning logic are unchanged.
- Frozen baseline, archived legacy starter and regression tests: scientific,
  presentation, Review and compatibility evidence. Existing test instrumentation
  preserves a factory's authored return type; stimulus-cropping fixtures keep the
  separate ready slot's correct family rather than assigning a task scene to it.
- Current authoring, learning, experiment and extension guides: one preferred
  narrative, edit map and Test/Ready walkthrough. Stale descriptions of removed
  reference folders and pre-extension loading are replaced in the current guides;
  dated architecture/audit reports retain their historical evidence.

The renderer, presenter, input, adaptive algorithms, methods, runner, recorder,
simulation models, TUI, calibration and installed-laboratory files are unchanged.
Software tests cannot establish monitor photometry, frame-to-photon timing,
acoustic onset, response-device latency or protocol-specific physical validity.
The retained teaching metadata wording limitation is documented separately in
[scientific notes](STAGE_C_SCIENTIFIC_NOTES.md); it is not silently corrected.

All active official sources and bundled starters satisfy the requested structure.
Treat migration acceptance as complete only when the full Windows suite and the
Windows CI job for the reviewed final revision pass. Human readability review and
the maintainer's merge decision remain explicit; this change merges no PR,
creates no release and moves no tag.
