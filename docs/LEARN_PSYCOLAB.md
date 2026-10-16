# Learn PsyCoLab — from a white line to a real experiment

**One tutorial. Works without the TUI.** You can read this file in VS Code,
GitHub, or a browser, or print it in the USER_env terminal:

\`\`\`cmd
python -m psychophysics_lab --learn
\`\`\`

You do **not** need to know Git, OpenGL or Pyglet to do this exercise.
For the exact file/ID rules, see [AUTHORING_CONTRACT.md](AUTHORING_CONTRACT.md).

## The idea in 30 seconds

\`\`\`text
   STIMULUS LIBRARY                 EXPERIMENT DESIGN
   What does it look like?  ----->  Where? When? Which response?
   white_line_probe.py              my_above_below.json
   white_line_probe.json            fixation -> probe -> blank -> answer
                                             |
                                             v
                                SIMULATE / VALIDATE / READY
                                             |
                                             v
                              NORMAL TUI -> Configure -> Review
                                         -> Run (human)
\`\`\`

A **stimulus** is a reusable drawing: a line, fixation cross, Gabor or ellipse.
Its \`render()\` receives arrays of \`x_deg, y_deg\` coordinates and returns a
2D grayscale array between 0 and 1. The **experiment** chooses *where* to
place the stimulus in degrees, its display duration, condition order and
response. The framework handles display calibration, input and trial saving.

Do not confuse:
- \`new_probe_vertical_line\` = an example *stimulus ID*.
- \`new_probe_vertical_line_stimulus\` = an existing *experiment ID* (despite
  its confusing historical name).
- \`probe_above_below\` = the built-in JSON experiment. You may see both the
  last two in Configure Experiment: they are separate approaches to the same
  task, **not an accidental double registration**.

## Exercise 1 — create a white vertical line from scratch

**Start:** double-click \`run_user_env.bat\` in the repository root.
Look for \`(USER_env)\` at the terminal prompt.

Create a unique ID. For example:

\`\`\`cmd
python -m psychophysics_lab --scaffold my_first_line --blueprint stimulus
\`\`\`

This creates two files, *not* an experiment:

\`\`\`text
src/psychophysics_lab/stimuli/my_first_line.py
configs/stimuli/my_first_line.json
\`\`\`

Open the Python file. **Edit 1:** \`PARAMETERS\` declares names, units and
permitted ranges. **Edit 2:** \`render(parameters, x_deg, y_deg)\` draws
the line. The provided line sample uses a narrow horizontal coordinate
window and a longer vertical one:

\`\`\`python
inside = (
    (abs(x_deg - parameters["offset_deg"]) < parameters["line_width_deg"] / 2)
    & (abs(y_deg) < parameters["line_length_deg"] / 2)
)
return np.where(inside, parameters["intensity"], 0.5)
\`\`\`

Here \`offset_deg\` shifts the line **inside its own patch**. For
*experiment-level* positioning, normally set it to \`0\` so the patch's
internal drawing stays centred. Also ensure \`size_deg\` encloses the
whole line but does not produce an unnecessarily enormous opaque grey area.
If you change allowed ranges in Python, keep the JSON defaults inside them.

**Preview/test this exact revision:**

\`\`\`cmd
python -m psychophysics_lab --dev-preview my_first_line
\`\`\`

The terminal prints **Preview saved: ...png**. No fullscreen stimulus should
appear yet; this command saves an *image*, not a physical visual display.
Open the path shown, for example in Windows Command Prompt:

\`\`\`cmd
start "" "C:\path\printed\by\preview\my_first_line.png"
\`\`\`

**Publish that exact tested stimulus:**

\`\`\`cmd
python -m psychophysics_lab --dev-ready stimulus my_first_line
\`\`\`

\`Ready\` means its current Python and JSON passed software validation.
After editing either one, **preview again**, then **Mark Ready again**.
Restart the normal PsyCoLab TUI to reload a newly published component.

## Exercise 2 — build ABOVE/BELOW with no experiment Python

There is already a registered \`fixation_cross\` stimulus. We will reuse it
and your \`my_first_line\`. The same line can be used by other experiments
without copying its \`render()\` function.

In the plain USER_env terminal:

\`\`\`cmd
python -m psychophysics_lab --library-create my_above_below --library-probe my_first_line --library-fixation fixation_cross --library-separation 2
\`\`\`

This creates **one editable experiment JSON**:

\`\`\`text
configs/experiment_designs/my_above_below.json
\`\`\`

Open it. You should see:
- \`stimuli\`: fixation cross and your probe.
- \`conditions\`: \`above = (0,+2°)\`, \`below = (0,-2°)\`.
- \`response\`: \`F = above\`, \`J = below\`.
- \`values\`: trial count and durations.
- \`actions\`: the chronological presentation and recording procedure.

The action story is:

\`\`\`text
fixation cross (500 ms)
 -> RecordState(before_probe)
 -> cross + white line (200 ms; ±2° y-position)
 -> blank (150 ms)
 -> CollectResponse(F = above, J = below)
 -> RecordState(response_received)
 -> UpdateState(correct_count)
\`\`\`

Your JSON uses existing registered stimuli; it doesn't generate another
experiment Python file. \`x_deg\` increases right, \`y_deg\` increases up.
Each condition's alternative must match the declared response meanings.

**Test with a virtual observer (no physical fullscreen display):**

\`\`\`cmd
python -m psychophysics_lab --library-test my_above_below
\`\`\`

A successful test prints \`PASS\` and a directory containing saved synthetic
trials. It checks the actual shared trial-action engine and canonical data.

**Publish the tested design:**

\`\`\`cmd
python -m psychophysics_lab --library-ready my_above_below
\`\`\`

Restart the normal TUI using \`run_psycolab.bat\`. Your new Ready task should
appear under **Experiment → select experiment → Configure → Review**. Select a
real, correctly configured monitor. Try **Run simulation** first. Running on
the *physical display with a human* requires the appropriate calibrated
profile and human-readiness checks; virtual data are not human data.

If you prefer a GUI authoring route, **Build Stimuli** and **Build Experiments**
provide the same workflows. You do not have to use these command lines once
you know the corresponding TUI controls.

## Exercise 3 — when you DO need an experiment Python file

A JSON-only experiment currently supports static spatial **two-choice**
conditions. If you need custom condition-generation rules, stimulus dynamics,
trial-specific computations or a new adaptive method, create an **advanced
Python experiment**:

\`\`\`cmd
python -m psychophysics_lab --scaffold my_advanced_task --blueprint experiment
\`\`\`

Now there are *two* files:

\`\`\`text
src/psychophysics_lab/experiments/my_advanced_task.py
configs/experiments/my_advanced_task.json
\`\`\`

The Python template has sections for (1) condition order, (2) trial actions
and placement, (3) scientific state, (4) the trial loop, and (5) its public
declaration. Its unanswered scientific sections deliberately raise
\`NotImplementedError\` rather than quietly copying the old left/right
experiment. You must finish the scientific task before a virtual test can
pass. To understand a **finished** Python example, inspect
\`src/psychophysics_lab/experiments/example_experiment.py\`: that is a
*left/right worked example*, not a neutral template. Compare it with the
existing researcher-created above/below example
\`new_probe_vertical_line_stimulus.py\`.

**Test and publish a custom Python experiment** (only after its TODOs are
implemented):

\`\`\`cmd
python -m psychophysics_lab --dev-test my_advanced_task
python -m psychophysics_lab --dev-ready experiment my_advanced_task
\`\`\`

This is the *same* scientific runtime as the JSON-only method:
\`TrialTimeline\` → \`run.play_trial\` → trial records and provenance.

## Exercise 4 — understand your saved results

The \`--dev-preview\` command saves a PNG in a development-only folder
printed to the terminal. The \`--dev-test\`/\`--library-test\` commands save a
synthetic run. Useful files include:

| File | What it tells you |
|---|---|
| \`trials.tsv\` | Condition, selected response, key, correctness |
| \`trial_actions.json\` | What actions were planned/executed, positions and state |
| \`trial_presentations.json\` | Stimulus/parameters associated with each response |
| \`resolved_experiment.json\` | Condition order and scientific description |
| \`stimulus_parameters.json\` | The resolved stimulus IDs and validated values |
| \`manifest.json\` | Version, source hashes, completion/abort provenance |

Never copy simulated results into a human participant dataset. PsyCoLab
separates development data from human acquisition.

## Troubleshooting by message

| Message or surprise | Meaning and next step |
|---|---|
| \`Unknown stimulus '...linee'\` | Check spelling, then \`--dev-list\` for the actual ID |
| \`exports mismatched SPEC.id\` | The generated Python filename, \`definition(identity=...)\` and JSON experiment ID must match |
| \`Source or JSON changed since last successful test\` | Repeat \`--dev-preview\` or \`--dev-test\`, then \`--dev-ready\` |
| Preview saved, but nothing appeared fullscreen | Correct: preview creates a PNG; open the printed path |
| Two similar above/below experiments in the selector | \`probe_above_below\` is the built-in JSON example; \`new_probe_vertical_line_stimulus\` is your Ready Python experiment |
| New experiment not listed in normal TUI | It may still be Draft, may have changed since testing, or needs a TUI restart |
| \`NotImplementedError\` in a new advanced template | Deliberate: finish its scientific conditions and actions first; use JSON builder for the simple task |
| Human experiment blocked by calibration | Software Ready is not calibration. Follow the explicit Review/Calibrate checklist; do not bypass it |

## Remember the simple rule

**Stimulus = appearance. Experiment = position, time, conditions and
response. Framework = calibrated display, input and saving.**

Start next time with \`python -m psychophysics_lab --learn\`. Read
[AUTHORING_CONTRACT.md](AUTHORING_CONTRACT.md) for the agreed structure.
