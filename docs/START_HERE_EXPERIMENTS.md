# START HERE: Build a stimulus and experiment in PsyCoLab

If a newly generated file looks like a complicated Gabor/tilt experiment, it
was created using an *older* scaffold. Existing authored files are never
rewritten. Create a **new** draft name with the updated Build buttons, or
edit the old files yourself. Do not delete previously acquired data.

## The four files you actually edit

| File | Job | Function / field to change first |
|---|---|---|
| `stimuli/example_stimulus.py` | What appears on screen | `render()` |
| `configs/stimuli/example_stimulus.json` | Default line width, position, brightness | `parameters` |
| `experiments/example_experiment.py` | Which trials, target conditions and response-dependent state changes | `make_trial_order()`, then `procedure()` |
| `configs/experiments/example_experiment.json` | Chronological sequence and timings | `phases` |

Open these directly using the normal PsyCoLab TUI **Stimuli → Read example
stimulus.py** and **Experiments → Read example experiment.py**. The matching
JSON buttons are adjacent. The source inspector opens your editor if available,
or presents a read-only view.

Do not begin by editing the internal runner, registry, calibration implementation
or logger. A researcher may add helper functions in their own stimulus/experiment
file, but does not need to implement event handling, calibration or saving.

## A small complete scientific experiment

The reference example presents a single white vertical line, either left or
right of the screen centre, and asks a two-choice question:

```text
experiment configuration
       |
       v
fixation (500 ms)     from experiment timeline JSON
       |
       v
line (200 ms)         use one stimulus + condition (left or right)
       |
       v
blank (150 ms)
       |
       v
response (F/J)       PsyCoLab collects and timestamps
       |
       v
record condition, response, correctness, custom measurements
       |
       v
update state / choose next trial
       |
       +---- repeat until trial_count responses, then complete
```

**Where to edit:** `render()` changes the *appearance* of the line.
`PARAMETERS` declares validated editable parameter names and ranges.
`make_trial_order()` changes the condition sequence.
`procedure()` builds per-trial parameter values, calls `run.play_trial()`
and optionally processes the returned `correct` value. The framework saves
responses and stimulus state automatically; the `measurements` dictionary
is for additional simple scientific observations.

The timeline JSON can use literal millisecond durations, or reference
`ConfigField` values such as `{"field": "stimulus_ms"}`. Such fields
are available in Configure Experiment in the normal TUI.

**This first example has no staircase.** Once the basic loop is clear,
see `experiments/orientation_adaptive.py` for an already-registered adaptive
method; it uses the same presentation cycle. A student should not reproduce
a staircase merely to learn how to draw a stimulus.

## Create your own files (the normal TUI or a terminal)

Use Build Stimuli / Build Experiments inside the normal PsyCoLab TUI, or:

```cmd
python -m psychophysics_lab --scaffold probe_white_line --blueprint stimulus
python -m psychophysics_lab --scaffold my_line_task --blueprint experiment
```

For a separate stimulus and experiment, the newly generated experiment
initially uses the registered `example_stimulus`. Change its
`definition(..., stimulus="probe_white_line")` to select your stimulus,
provided the stimulus uses the same `simple_line` family.
For a matching pair with both IDs prewired to each other:

```cmd
python -m psychophysics_lab --scaffold my_task --blueprint pair
```

Edit the generated files. To preview and simulate in the activated USER_env
plain terminal:

```cmd
python -m psychophysics_lab --dev-preview probe_white_line
python -m psychophysics_lab --dev-ready stimulus probe_white_line
python -m psychophysics_lab --dev-test my_line_task
python -m psychophysics_lab --dev-ready experiment my_line_task
python -m psychophysics_lab --dev-list
```

A test marks the exact current source/JSON revision. Editing afterward
invalidates Ready until retested. Restart the normal PsyCoLab TUI to see
newly Ready experiments.

**Important:** The scripts you create are Python *modules*. Running
`python path_to_my_stimulus.py` merely loads their definitions, unless
you add an explicit `if __name__ == "__main__":` entry point. Use the
normal PsyCoLab preview/test commands to run these modules through its
framework services.

## How does the CSF fit this same design?

CSF is **the more advanced instance of the same scientific model**, not a
recommended starting template:

| Same responsibility | Beginner experiment | CSF reference |
|---|---|---|
| Stimulus | `example_stimulus.render()` | Legacy OpenGL grating source (`Events/stimuliC.py`) |
| Conditions | `make_trial_order()` | `contrast_sensitivity.py` condition fields |
| Ordered states | `example_experiment.json` | `contrast_sensitivity.json` |
| Responses | `run.play_trial()` | Existing CSF response handler |
| Adaptive changes | Optional (none in example) | Retained independent staircases |
| Saving | Standard PsyCoLab recordings | Standard PsyCoLab recordings with CSF semantics |

**Current boundary:** CSF's *declared* fixation → new condition → grating →
interval → response timeline uses the same `TrialTimeline` model. Its actual
presentation and adaptive-response loop still use the retained
`Trial_ADMs`/OpenGL implementation. A full migration requires regression
tests against the existing scientific output, then physical timing and
photometric equivalence. This change does not silently replace that runtime.

The simple line example uses software timings and digital grayscale values,
**not** physically measured photon onset or calibrated luminance. Simulation
readiness does not qualify a real participant session.
