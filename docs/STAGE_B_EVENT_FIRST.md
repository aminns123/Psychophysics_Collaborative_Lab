# Stage B: Python-first CSF and two-interval ellipse

This stage migrates only `contrast_sensitivity.py` and `ellipse_major_axis.py`.
It follows [the code philosophy](CODE_PHILOSOPHY_AND_CONTRIBUTIONS.md), based on
latest merged main `b3d53d511721fbd201c4ee263783a2f10dcb1cdf` (PRs #153/#154).
The authoritative laboratory checkout was clean on main `9006baf` at intake;
origin/main was fetched and the explicitly named `event-first-stage-b-20261027`
worktree/branch was created from the newer merged main. The laboratory checkout,
calibration records, participant data and real external extensions were not edited.

## Final researcher-facing API

An experiment owns one ordinary `SESSION_START` list and one
`trial_events(settings, condition)` function returning a flat list. Its six
sections are parameters; once-only opening; repeated events and effective
stimulus preparation; scientific conditions/updates; stopping/results; minimal
registration. No event logic or new experiment-specific controls are in the TUI.

The two migrated defaults deliberately add SPACE readiness and 1,000 ms settling:

```python
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]
```

Write `SESSION_START = []` to disable it, or edit the key and duration directly.
Reload the Python definition through the existing refresh/restart workflow.
Existing ConfigFields still configure the trial and scientific method. A
researcher can optionally use fields in event declarations; they are not required.
Use a uniquely identified lab extension for experimental variants; changes to
curated official science still require explicit review.

`ready_fixation` selects the existing Gaussian fixation class. The ellipse's
ordinary detection-scene base includes a probe, so reusing its unprepared base
for readiness would be incorrect. The session-only slot avoids changing any
trial stimulus identity or parameter. Its background follows the selected
experiment background through existing stimulus-field binding. The public
`experiment()` helper now exposes that existing binding mechanism; unbound
parameters use the selected class defaults when creating a fresh snapshot.
Saved JSON still requires every original parameter and remains strictly validated.

## Before and after

Previously each file put condition construction and preparation before its
`make_trial()`/TrialTimeline. A reader encountered scientific selection machinery
before seeing the participant's experience. There was no official opening.
Now parameters are followed immediately by the opening and event list. Preparation
is adjacent and explicitly maps current condition/strength to renderer inputs.
The unchanged scientific functions then explain selection and subsequent updates.

| Experiment | Previous sequence declaration | Stage B authoritative declaration |
| --- | --- | --- |
| Gaussian CSF | `make_trial()` in section 4, returning TrialTimeline | `trial_events()` in section 3: fixation → selected-side grating → left/right answer |
| Ellipse Major Axis | `make_trial()` after conditions and scene preparation | `trial_events()` in section 3: fixation → first interval → ISI → second interval → first/second answer |

CSF's event list retains its selected eccentricity and silent trial default:

```python
def trial_events(settings, condition):
    offset = settings["grating_offset_deg"]
    x = -offset if condition["target"] == 0 else offset
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("grating", stimuli=(Stimulus("grating", x_deg=x),),
             duration="grating_ms", beep=None),
        CollectResponse(actions=("left", "right"), slot="fixation", beep=None),
    ]
```

Ellipse retains both existing onset cues when its auditory-cue setting is enabled:

```python
cue = Beep(settings["cue_hz"], settings["cue_ms"]) if settings["auditory_cues"] else None
return [
    Show("fixation", slot="fixation", duration="fixation_ms"),
    Show("interval_one", slot="first", duration="stimulus_ms", beep=cue),
    Show("inter_interval", slot="fixation", duration="isi_ms"),
    Show("interval_two", slot="second", duration="stimulus_ms", beep=cue),
    CollectResponse(actions=("first", "second"), slot="fixation", beep=None),
]
```

These are flat Python lists. A small function returning events can be joined
with `+`; unique names and the existing timeline validation still apply. The
method selects the current condition and strength before building each trial.
No future adaptive values are precomputed.

## Researcher edit map

| What to identify/change | Where in either experiment |
| --- | --- |
| Opening, start key or disable | Section 2 `SESSION_START`; key literal SPACE, empty list disables |
| Initial settling fixation | Section 2 `Show("settle", duration=1000)` |
| Per-trial fixation duration | Section 1 `fixation_ms`; used by section 3 Show |
| Stimulus-onset tone | CSF grating `beep=None` can become `Beep(550, 35)`; ellipse's two interval events retain `cue` |
| Accepted-answer tone | CollectResponse `beep=None` can become `Beep(750, 35)`; it triggers only on an accepted answer |
| Stimulus placement | CSF signed angular offset in `trial_events`; ellipse coordinates/geometry in `prepare_stimuli` and its declared fields |
| Condition selection | `make_conditions`, `make_fixed_schedule`/shared fixed scheduler and `choose_condition` in scientific rules |
| Response-dependent next strength | `change_contrast` uses the existing bounded log step; `update_experiment` applies the shared staircase update once after interpretation |
| Stopping and estimation | `is_finished`, `primary_rule`, `finish_experiment`; configured reversals and safety ceiling retain their distinct meanings |
| Chronological displays | The flat `trial_events` list near the top; both ellipse intervals and ISI are visible together |

The framework retains pre-rendering, input handling, algorithms, recording and
recovery. No arbitrary callback is added inside a timed phase. Python edits can
change a protocol intentionally; saved field selections still override edited
Python defaults where the existing configuration contract says so.

## One definition, compatible callers

Both migrated procedures pass `trial_events=trial_events` to the existing shared
contrast loop. Generic Review uses that same module function. Older modules
continue through `make_trial`; no change to `ui/setup.py` is required.

The centralized `legacy_trial_factory` supplies
`make_trial = legacy_trial_factory(trial_events)` for older callers expecting
`make_trial(...).resolve(...)`. It wraps the same list with the existing validated
TrialTimeline; it neither declares another sequence nor executes a runner.
The shared method accepts the old keyword, rejects simultaneous competing
factories before scientific state creation, and leaves method/RNG/update logic intact.

The circular CSF inherits Gaussian registration. A narrow compatibility edit
excludes the new session-only slot/binding and keeps its empty opening; its
scientific functions and events are not migrated. The other seven files have
no source change. Stage C has not begun, and no compatibility path was removed.

## Equivalence and evidence

The original Stage A frozen fixture is retained unchanged. Its forty runs still
compare all ten official studies and both methods with openings explicitly disabled.
Before Stage B edits, eight additional runs were captured from latest main:
two studies × two methods × seeds 0/19. Adaptive runs complete all requested
reversals, including initial one-down, and produce primary thresholds. The fixture
retains full scientific function identities and hashes of complete canonical rows,
trial actions, presentations, per-response adaptive histories, final adaptive
sessions, primary thresholds and resolved scientific results.

Stage B compares those captures twice: Case A rebuilds the registered Python
definition with `SESSION_START=[]`; Case B uses the approved opening. Scientific
outputs must match in both cases. Case A creates no session-event sidecar.
Case B adds only session behavior/provenance and corresponding software timing.
Source hashes and configuration provenance also identify the new session-only
slot; they are not expected to pretend this is an old source revision.

Additional tests exercise the real Presentation phase player with an injected
window/input clock, both contrast methods and both opening cases. They compare
first/last accepted responses and scientific state, excluding only host software
timestamps. Escape at readiness traverses the isolated presentation-test runner
and preserves a zero-trial aborted manifest. Generic Review is tested with the
legacy hook absent or conflicting, proving that the new Python event definition
controls both inspection and acquisition. Existing extension/trust/Ready,
saved-run reader, calibration and recovery regressions remain in the full suite.

Exact final Windows test counts, CI head and test-merge tree are recorded in
the Stage B PR evidence. This report does not claim physical photon timing,
photometry, speaker onset, native apparatus or participant-acquisition qualification.

Before the full Windows run, the final combined Stage B/session/shared-method/
extension/reading-pattern selection passed **164 tests, 1 platform skip**, in
155.12 s. An earlier broader group passed 246 tests and identified a generic
Configure partial-binding issue; that issue was repaired and the edit/return
workflow now has its own regression. No scientific assertion was removed.

The design is ready for maintainer assessment as the pattern for Stage C once
Windows acceptance is green. Broader migration requires acceptance of this
researcher-facing design; no other experiment is automatically converted.
