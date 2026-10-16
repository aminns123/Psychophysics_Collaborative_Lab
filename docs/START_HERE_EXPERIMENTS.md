# Build a stimulus and an experiment

Use the normal PsyCoLab TUI. Your Python defines the science; JSON supplies
validated settings. PsyCoLab handles geometry, input, recording and provenance.

## 1. Read the four beginner files

| File (Python files are under src/psychophysics_lab) | Edit here |
|---|---|
| stimuli/example_stimulus.py | PARAMETERS, then render(): a simple white line |
| configs/stimuli/example_stimulus.json | Line width, position and digital intensity |
| experiments/example_experiment.py | Conditions, TRIAL action list, response update |
| configs/experiments/example_experiment.json | Trial count, durations and response keys |

Open **Build Stimuli → Read example stimulus.py** and **Build Experiments →
Read example experiment.py**. Adjacent JSON controls open the corresponding
settings. Source inspection opens VS Code if available; otherwise it displays
the exact file read-only. Use your preferred editor when VS Code is unavailable.

## 2. Create a stimulus

In **Build Stimuli**, enter a new lowercase name, then **Build new stimulus**.
Existing files are never overwritten. Your component appears in the selector
below the Build button. **Edit Python** changes appearance and parameter
declarations; **Edit JSON** changes starting values. **Preview / validate**
exercises its renderer and reports the image location. **Mark Ready** publishes
that tested revision into the existing stimulus registry.

The example's grayscale values are digital commands. They are not measured
luminance. Select the required calibration in the stimulus/experiment declaration.

## 3. Create an experiment

In **Build Experiments**, enter a new name, then **Build new experiment**.
It initially selects the registered example_stimulus. Change the stimulus
argument in definition() to select your own compatible simple_line stimulus.
Build a matching pair from the terminal with
`python -m psychophysics_lab --scaffold my_task --blueprint pair`.

The beginner procedure is deliberately non-adaptive. Its chronological sequence
is written directly in Python:

```python
TRIAL = TrialTimeline((
    Show("fixation", duration="fixation_ms", instructions="+"),
    RecordState("before_line"),
    Show("line", slot="target", duration="stimulus_ms"),
    Show("blank", duration="interval_ms"),
    CollectResponse(actions=("left", "right"), timeout="response_timeout_ms"),
    RecordState("response_received"),
    UpdateState(update_from_response),
))
```

Change make_trial_order() for conditions, the action list for chronology,
update_from_response() for the next scientific state, and definition() for
stimulus selection, response meanings, settings and calibration requirements.

The JSON values are checked against the same ConfigField declarations as the
TUI. TUI/CLI selections override JSON defaults for that run. Unknown settings,
invalid values and missing files fail explicitly. No JSON expression is executed.
The run saves the effective configuration plus the experiment JSON and its hash.

## 4. Test and publish from the same page

Select your draft and choose **Simulate / validate**. Inspect the reported run
folder: trials.tsv contains accepted responses; trial_actions.json contains the
plan, actual/virtual events, resolved stimuli and state snapshots. The framework
also saves configuration, source fingerprints and completion/abort/error status.

Then **Mark Ready**. New Ready modules enter the normal catalogue without edits
to framework registration files. Return to **Experiment** to select the new
task. If an already imported module was edited, restart PsyCoLab to refresh Python
module references. Editing Python/JSON invalidates the tested fingerprint; test
and publish the changed revision again. Ready means software-tested.

## 5. Configure and run

Choose participant, experiment and display; configure settings and independent
stimulus slots; then Review. First run a simulation. For human collection,
resolve the experiment's calibration and qualification requirements. Geometry,
luminance and timing controls remain on their corresponding Calibrate pages.

For the existing luminance mapping: **Calibrate → Luminance → Step 1 — Review or add saved luminance readings →
Accept luminance values → Timing**. When opened from Review the button
returns to Review. If readings are still in entry boxes, choose **Add readings
to draft** first. To reject unwanted draft changes use **Discard draft; keep
saved values**, then Accept. Saving alone leaves the mapping pending approval.
Acceptance preserves raw provenance/history and does not certify fake values as
physical measurements. This behavior was already present on baseline main.

## 6. Add more science when needed

- Additional scalar measurements: pass named values in measurements to play_trial;
  declare their units in initialise's resolution.
- State snapshots: RecordState("label", fields=("contrast", "position")).
  Omit fields to capture the full current state.
- Updates: return a new finite JSON mapping from update(state, response). Inputs
  are immutable. Use run.trial_state for the next trial's parameters.
- Adaptation: see orientation_task.py and orientation_adaptive.py. A registered
  algorithm created by run.adaptive() is used by UpdateAdaptive; history is automatic.
- Multiple patches: Show("pair", duration=200,
  stimuli=(Stimulus("left", -2, 0), Stimulus("right", 2, 0))).
  Declare both slots and pass independently validated parameters_by_slot.

Patches are opaque, drawn in written order. Later patches cover earlier ones.
The static backend pre-renders before the trial; updates affect scientific state
and subsequent trials, not an already prepared image. No dynamic animation,
sub-frame timing, transparent compositing or measured photon timing is claimed.

## Plain Python terminal

run_user_env.bat remains a dependency-managed Python 3.11 command prompt. It does
not open another TUI. Equivalent commands:

```text
python -m psychophysics_lab --dev-preview my_stimulus
python -m psychophysics_lab --dev-ready stimulus my_stimulus
python -m psychophysics_lab --dev-test my_experiment
python -m psychophysics_lab --dev-ready experiment my_experiment
```

Generated files are modules. Running python path/to/module.py loads definitions;
use the framework commands above to preview/test them.

## CSF boundary

The human CSF remains the existing OpenGL/event implementation. It has NOT been
fully migrated. The explicit development-only comparison is:

```text
python -m simulations.csf_actions --output NEW_DIAGNOSTIC_DIRECTORY
```

This replays scientific state through the public actions without rendering any
substitute pixels. See [CSF parity and remaining gaps](CSF_ACTION_MIGRATION.md).
