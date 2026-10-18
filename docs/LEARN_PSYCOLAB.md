# From stimulus idea to a tested experiment

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

Open one file in `src/psychophysics_lab/experiments/`:

- `orientation_task.py`: fixed-trial orientation judgement.
- `contrast_sensitivity.py`: adaptive left/right grating detection.
- `ellipse_major_axis.py`: first/second interval line detection.

Read settings → conditions/order → stimulus preparation → one trial → responses
and adaptation → run/finish → framework connection. `TrialTimeline` states the
display order. Keep the participant's alternatives, units, adaptive change,
stopping rule and primary estimator explicit. The TUI supplies the chosen values.
Do not copy an example's scientific choices unless they fit your study.

For a new file, export `SPEC` with its matching experiment ID. Discovery needs no
registry edit. Fixed-trial and adaptive loops may differ. Repeated recording
machinery is shared; each experiment still declares strength, steps, gamut and
extra measurements at its recording call.

For a quick scientific review, start with `make_trial()` and `prepare_stimuli()`,
then read response/adaptation and `finish_experiment()`. Expand the settings when
changing the study. Keep fixed-trial loops simple; they need no dummy adaptive
stage. Dictionary declarations beside the framework connection explain what the
saved columns mean; a digital increment and a peak-to-peak grating modulation are
different quantities even if they use the same compatibility column name.

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
