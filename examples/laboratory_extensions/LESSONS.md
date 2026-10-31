# Learn by extending one left/right experiment

Start here: **Beginner → Intermediate → Advanced**. Each lesson is executable
ordinary Python in one file with the same A1/A2/B narrative. The question stays
“which side contains the line?”; F means left and J means right throughout.
These are finite teaching studies, not validated threshold protocols.

| Lesson | Python source | What is added |
|---|---|---|
| Beginner | [lesson1_side](experiments/demolab__lesson1_side.py) | Alternating left/right line, SPACE opening, fixation/exposure/response, finite count, journal measurements |
| Intermediate | [lesson2_strength](experiments/demolab__lesson2_strength.py) | Distance conditions, one independent adaptive track per condition, existing fixed-level planner, explicit digital strength and finite stopping |
| Advanced | [lesson3_study](experiments/demolab__lesson3_study.py) | Distance × length cells, own soft-edged stimulus, retention gap, optional cues, additional measurements and constraints |

There is no new experiment language, generator or method engine. Intermediate
and Advanced each contain their own scientific declarations so the scientist
can read one file; neither imports another lesson or an official experiment.
They call the installed adaptive counters, bounded step calculation, fixed-level
planner, canonical runner and recorder. Keep framework integration in B.

## Prepare your own trusted source folder

1. Open **Laboratory extensions**. A new first-run starter contains these lessons
   alongside the older compatibility examples. Existing folders are never
   overwritten or silently upgraded. For an existing lab, copy the three lesson
   files deliberately from this bundle and add the `LearningLine` class from its
   `stimulus_library.py` to your own library; preserve your existing definitions.
   Use unique namespace-prefixed IDs and filenames if you already use `demolab`.
2. Select that folder and explicitly trust it only after reviewing its Python.
   These files are executable local code. In **Build Stimuli**, Preview the
   `demolab__learning_line` stimulus and mark that tested revision Ready for the
   advanced lesson. Beginner/Intermediate use the installed `oriented_line`.
3. In **Build Experiments**, select a lesson, open its source, Test it and mark
   the successfully tested revision Ready. Trust alone never marks code Ready.
4. Select it in the experiment catalogue. **Configure** contains universal setup
   controls only. **Review → Edit inputs / stimuli** is the generic editor for
   all declared scientific inputs and compatible stimulus choices.
5. Inspect Review's effective units, conditions, keys, timeline, measurements and
   source rows. Open a selected row's Python source to locate the actual local
   file/class. Invalid supplied values stay drafts until corrected and applied.
   Blank optional values use their declared defaults; they are not missing
   required study inputs. Presets save run choices, not rewritten source.
6. Simulate the lesson and open the saved run. After any Python edit, refresh/
   restart and retest the new source before marking it Ready again. Refresh
   retains run settings but cannot retain obsolete Ready evidence.

For the project-source route, place an experiment in
`src/psychophysics_lab/experiments/`, adjust its `source_paths` to that project
location, and place the advanced stimulus class in the project's existing
`stimulus_library.py` with its project-relative source path. No registry, TUI or
execution changes are needed. Local extensions are the recommended learning
route; do not overwrite an official experiment or existing stimulus ID.

## Read each file from A1 to B

**A1 — Experimental choices:** `FIELDS` contains editable units/defaults;
`RESPONSES` defines alternatives and keys; slots select appearance;
`SESSION_START` opens once; `trial_events` reads chronologically;
`trial_measurements` names saved requested values with `MEASUREMENT_UNITS`.
These declarations feed generic Review. No JSON serialisation knowledge is
needed to add a scalar measurement and its unit.

**A2 — Scientific methods:** `make_conditions` enumerates cells;
`choose_condition` chooses the current cell/target and current strength;
`prepare_stimuli` maps those quantities into renderer parameters;
`interpret_response` checks correctness; updates change state only after an
accepted response; stopping and validation are explicit. Edit A2 deliberately:
changing balancing, steps or bounds changes the scientific design.

**B — Framework integration:** record projection, the existing runner and SPEC
connect the declarations to provenance and recording. This normally stays
unchanged when editing A1. Changing response alternatives requires checking the
binary target rules in A2 as well as changing keys.

## Beginner exercise

Run the default eight responses. Change `stimulus_ms` from 200 to 125 and
`eccentricity_deg` from 1 to 1.5 in Review. Inspect the new timing and both target
placements, simulate, and find `line_x_deg` and `requested_exposure_ms` in
`trial_presentations.json` / `trial_events.jsonl`. Change the SPACE key or
settling duration in A1, then Test → Ready again. `SESSION_START=[]` disables
the opening; readiness is never an accepted answer. Odd counts include one
extra left target. No staircase or threshold is claimed.

## Intermediate exercise

Distance is a **scientific condition**; left/right is the **target alternative**.
Each distance has its own **adaptive track** and response history. A **fixed
repeat** is a presentation in a distance/strength cell, not a track.

Strength is `I_line - 0.5`, a digital increment in [0, 0.5]; the actual renderer
command is `0.5 + strength`. Zero is an intentional invisible catch. Neither
the increment nor the command is measured luminance or optical contrast.

Select Adaptive: the finite cell/side order is shuffled using the run seed;
current track strength is selected after the preceding accepted response.
Existing n-down/n-up counters choose a step; the shared bounded numerical method
applies the selected multiplier. The finite goal must cover both sides of all
cells and fit `max_trials`. With complete cycles, sides are exactly balanced;
partial final cycles differ by at most one per cell. No future strengths are
precomputed and reaching this count does not establish threshold convergence.

Select Constant stimuli: two distances × three increments × five presentations
gives 30 responses. Repetitions count **all responses in each cell**, not each
target separately. The installed planner balances binary targets to within one
for odd counts and shuffles with a fixed seed. Fixed trials have blank
staircase-only columns and save per-cell accuracy, not an invented threshold.

Exercise: change distances to `0.5,1,1.5`, use 18 adaptive responses, then switch
to fixed levels `0,0.05,0.15` with two repetitions. Check the 18-response fixed
plan and compare independent adaptive histories with fixed-level accuracy.

## Advanced exercise

Distance × length defines four cells by default, each with its own finite track
in Adaptive. `LearningLine` in the local stimulus library declares dimensions,
finite edge coverage and digital intensity. A2 enforces the edge/width
constraint; Review shows prepared values and which parameters the trial controls.
Placement is still left/right; the response paradigm has not changed.

Enable `audio_cues=1`. A1 visibly requests a 550 Hz / 35 ms onset cue, a retention
fixation, and a 750 Hz / 35 ms accepted-answer cue. These are software requests,
not measured acoustic timing. Exercise: change lengths to `0.4,0.9`, increase
retention to 250 ms, then inspect all four cells and simulate both methods.
Add `requested_retention_ms` to `trial_measurements` and declare `ms` in its
units map. Retest, open a saved journal and verify the new observation. Try an
edge wider than half the line: validation must reject it without losing drafts.

## Saved results and limits

All lessons retain the shared 20-column `trials.tsv` with its data dictionary;
custom observations use the existing journal, not new canonical columns.
`experiment_config.json`, `resolved_experiment.json` and `manifest.json` preserve
selected settings, resolved plan, source fingerprints and software provenance.
Inspect accepted responses, correctness and conditions with the existing saved
run reader. Intermediate/Advanced adaptive runs include the existing
`adaptive_session.json` / per-track histories; fixed results report observed
counts and accuracy. Finite teaching tracks supply **no scientific threshold
estimate**. A future estimator requires scientific justification and validation.

ESC before Trial 1 preserves a zero-response abort. Interruption during a run
preserves accepted trials and journals; do not retry acquisition automatically.
Geometry, calibration, qualification and researcher override behaviour remain
the platform's normal safeguards. This guide is software teaching; neither
synthetic tests nor previews qualify physical apparatus or a measurement protocol.
Independent student/human acceptance remains a separate exercise.

Older `demolab__left_right` and `demolab__line_strength` sources/presets remain
compatible; their additional details are in [METHODS.md](METHODS.md).
