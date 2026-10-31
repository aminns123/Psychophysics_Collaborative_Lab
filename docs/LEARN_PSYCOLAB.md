# Your first PsyCoLab experiment

Start in **Learn / Help → Read the short walkthrough**, or **Build Experiments**.
Read the basic discrimination example first, then the adaptive/fixed example.
Both are executable ordinary Python, using the approved
[A1/A2/B narrative](EXPERIMENT_AUTHORING_STANDARD.md). New science normally belongs
in your own trusted laboratory folder, not an edited official reference.

Configure supplies universal run controls. **Review → Edit inputs / stimuli**
edits the declared scientific inputs and stimulus values for this run. Review's
table explains effective values, units, authority, selected method, events and
outputs; selecting a row gives full details and its actual source location.
Unsaved drafts are not a successful validation. Correct errors and apply to
Review before running. Saved presets never overwrite Python defaults.


## 1. Draw the stimulus

Open `src/psychophysics_lab/stimulus_library.py`. Each `LibraryStimulus` class has
`PARAMETERS`, a `render()` function, and `SPEC`. Read a similar class before adding
your own. Keep the drawing rule and scientific units in that class. Restart
PsyCoLab after Python source edits; parameter edits within the interface do not
require a restart.

Open PsyCoLab → **Build Stimuli**, choose a stimulus, and press **Preview stimulus**.
Its default appearance opens in your image viewer. In Experiment setup, **Edit
parameters** previews different values and saves a named preset; shared defaults
are preserved. Advanced JSON editing remains available when needed.

An image preview is an 8-bit appearance aid, not a physical contrast measurement.
Low requested contrasts can look identical in the preview. Actual scientific
presentation retains floating commands and requires separate display qualification.

### Write geometry as equations and masks

`render(parameters, x_deg, y_deg)` already receives two NumPy arrays: the x and y
coordinate in degrees at each pixel. You can write equations directly; the
framework supplies the mesh and converts degrees for the selected display.
For example, inside a class with the corresponding declared parameters:

```python
x = x_deg - parameters["centre_x_deg"]
y = y_deg - parameters["centre_y_deg"]
inside_line = (np.abs(x) < parameters["width_deg"] / 2) & (y > 0)
return np.where(inside_line, parameters["intensity"], parameters["background"])
```

Use `&` and `|` for array masks, with parentheses around each comparison.
For a curve, compute its y-coordinate from x and mask pixels near that curve.
Return one intensity array, rather than a pair of coordinate arrays. Creating
your own pixel grid with `linspace` inside `render` would bypass the supplied
calibrated grid. Cropped, blank and control stimuli are valid design choices:
inspect all relevant conditions with previews and **Try the experiment**.

## 2. Describe the experiment

### First: basic discrimination

Open [demolab__left_right.py](../examples/laboratory_extensions/experiments/demolab__left_right.py)
or **Build Experiments → A1/A2/B: basic discrimination** (the official teaching
counterpart). Read these three sections, in order:

1. **A1 — Experimental choices:** the question, `FIELDS` with ms/degree units,
   `RESPONSES` (left/right, F/J), selected stimulus, once-only `SESSION_START`,
   `trial_events` and `trial_measurements`. The target rows alternate left/right;
   there is no independent factor or staircase in this local basic example.
2. **A2 — Scientific methods:** `make_conditions`, `choose_condition` (signed
   line offset), `interpret_response`, the correct-answer counter and stopping
   at the accepted-response goal. There is no threshold estimator.
3. **B — Framework integration:** existing RunContext execution, projection into
   canonical records and SPEC. Normally leave these connections unchanged.

The timeline is fixation → marker → line → blank → response → marker.
Markers observe state; they are not additional displayed intervals or answers.
Change exposure in `FIELDS`, or edit a flat `trial_events` list. A1's
`trial_measurements(settings, condition)` saves requested `line_offset_deg` in
the existing journal, with units declared beside it. Accepted responses, keys,
correctness and resolved presentation are already recorded automatically.

### Next: one experiment, adaptive or constant stimuli

Open [demolab__line_strength.py](../examples/laboratory_extensions/experiments/demolab__line_strength.py)
or **Build Experiments → A1/A2/B: adaptive / fixed**. It uses the installed line
stimulus and existing shared methods, not a copied staircase engine.

| Scientific concept | Meaning in this example | Where to inspect/change |
|---|---|---|
| Conditions | Positive eccentricities 1° and 2° | A1 `eccentricities_deg`; A2 parsing/selection |
| Alternatives | Left/right, codes 0/1, F/J | A1 `RESPONSES` and signed placement in `trial_events` |
| Strength | Digital increment: `I_line = 0.5 + increment`, range 0–0.5 | A2 `prepare_stimuli`; not calibrated optical contrast |
| Adaptive track | One shared finite teaching track across the scheduled target rows | A2 imported `TeachingAdaptiveMethod` and selected n-down/n-up factors |
| Fixed repetition | One presentation in an eccentricity × strength cell | A2 `make_fixed_schedule`; not a separate staircase or a repeat per side |
| Stopping/results | Adaptive: accepted-response goal; fixed: exhausted schedule; accuracy, no threshold | A2 stopping comments and method factories |
| Measurements | Fixed repeat and presented increment; both modes also save canonical responses/strength and resolved geometry | A1 units/declaration; B forwards the existing record |

Choose the method with the shared Configure control; edit its levels/rules in
Review's generic editor. The default fixed plan is 2 eccentricities × 3 levels ×
5 repetitions = 30 presentations. Targets are balanced within each cell to
within one for odd repetitions. Zero increment is an intentional catch.
The finite adaptive demonstration stops at `trial_count`, not reversal convergence;
increasing its trial goal does not turn it into a validated threshold procedure.

### Make your own local study

In **Build Experiments → Laboratory extensions**, choose a separate location
such as `PsyCoLab_Extensions`. **Create starter at this location** preserves any
existing files. Read its Python, then deliberately enable the trusted folder.
Trust grants code execution; it is not scientific or hardware qualification.

Use your own namespace/IDs for a new study. Read the local
[starter instructions](../examples/laboratory_extensions/METHODS.md), including
the matching manifest, filenames, SPEC IDs and custom stimulus. Preview the local
stimulus and mark its tested source Ready; Test the experiment and mark that
tested revision Ready. Use Refresh (F5) after saved Python edits. Changed source
or scientific dependencies invalidate stale Ready evidence; retest deliberately.
Refresh retains selected values/drafts rather than adopting changed defaults.

For source inspection, select the actual external file in Build Experiments or
Review. An identically named repository file is not a substitute. A project
experiment file exporting SPEC is also discovered without a registry/TUI edit;
official source changes still need review. Older make_trial/TrialTimeline files
remain compatible. The remaining six-section official files are scientific
references pending family migration, not the recommended new-author template.

Every official experiment has once-only SPACE readiness and 1,000 ms settling.
Local examples show how to edit the list or use `SESSION_START=[]`. Readiness
is not an answer and never updates a staircase. Optional `Beep(550, 35)` on Show
or `Beep(750, 35)` on CollectResponse requests sound; it does not establish
measured audiovisual synchronisation. Validate every scientific modification,
including keys, positions, durations, strengths, stopping and measurements.

## 3. Try the actual trials

Open **Experiment**, choose your experiment and display, configure, and review.
Choose **Try the experiment**. Enter the number of responses to try (default eight;
blank runs the full experiment), acknowledge test data and start.

Use the experiment's response keys. Escape stops. A short test ends with
`test_finished`; this means the test response limit was reached, not that the
study or staircase completed. Settings and accepted responses remain saved.

Test records go to `psycolab_presentation_tests`, beside local configuration,
separate from participant data. The completion message gives the exact run folder.
Open `trials_readable.txt` for responses, `resolved_experiment.json` for scientific
settings and `manifest.json` for run status and provenance.

Responses and detailed trial records are saved independently at each trial
boundary. A saving failure marks the run as an error, rather than successful
collection. The experiment file guide explains interruption records when needed.

If a test cannot start, follow its specific monitor, geometry or rendering message.
A photometer is not required merely to inspect trials. Participant acquisition
still requires the experiment's physical qualification checks.

Review also reports condition frequencies that this monitor cannot physically
sample. You can continue editing, previewing or simulating those settings;
physical presentation retains its display limits. A protocol-level acquisition
block requires laboratory/developer qualification, not another monitor checkbox.
A short randomised test may not include every condition. Inspect each relevant
condition deliberately, using a full test or a selected subset of study settings.

## 4. Check the procedure with simulated responses

Use the **same Experiment setup**, then choose **Simulate responses**. Start with
the default observer, or expand **Virtual observer settings** to change the model
or seed. Simulations do not show or qualify the physical display.

Simulation records use `synthetic_` identities in the selected external data folder.
Inspect the reported status, responses and analysis. A run that executes correctly
does not by itself demonstrate unbiased threshold recovery; read the protocol's
recovery evidence and boundary failures.

## 5. Prepare for participant data

Use **Calibrate** to bind the actual monitor and collect geometry, luminance and
timing evidence. Choose **Collect participant data** only after the required checks
pass. A successful preview, physical test or simulation does not qualify a display.
See [display setup](TUI_AND_LOCAL_DISPLAYS.md) for the measurement workflow.

## Optional: tracked researcher contributions and terminal tools

For Draft/Test/Ready protection, register an existing file with
`python -m psychophysics_lab --dev-stage experiment ID`, test it with
`--dev-test ID`, then use `--dev-ready experiment ID`. Changed tracked files must
be retested. Ready describes software testing, not physical calibration.

`--dev-preview STIMULUS_ID` remains a headless PNG export for scripts. The normal
interface opens previews automatically. `--learn` prints this guide without
opening the interface. Historical simulation commands remain compatibility tools;
use explicit experiment IDs and read their model-specific interpretation.
