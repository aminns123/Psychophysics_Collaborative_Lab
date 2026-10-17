# Build a stimulus and an experiment in PsyCoLab

**Two places to edit. No generator. No per-stimulus Python files.**

1. **Drawings:** `src/psychophysics_lab/stimulus_library.py`
2. **Experiments:** `src/psychophysics_lab/experiments/<task>.py`

The framework handles monitor geometry, human responses, simulation, data, and calibration.

## 1. Create or edit a stimulus

Open **Build Stimuli → Open stimulus_library.py**, or open the file directly in
VS Code. Find `FixationCross`, `VerticalLineProbe`, `LinePatch`, `SquarePatch`,
`RectanglePatch`, `EllipsePatch`, `AnnulusPatch`, `GaussianDot`,
`SinusoidalGrating`, `GaborPatch`, `TeachingGabor`, `CSFGrating`
and `ComposedScene`. Each keeps three familiar
sections together:

- **PARAMETERS:** units, allowable ranges, defaults
- **render(parameters, x_deg, y_deg):** numerical grayscale image in 0–1
- **SPEC:** ID, description, renderer and calibration requirements

To add something new, copy the closest **class in that same file**, rename it,
give it a unique `SPEC.id`, and set
`source_path="src/psychophysics_lab/stimulus_library.py"`.
Inherit from `LibraryStimulus`; PsyCoLab discovers these classes automatically.
**Do not create a new .py file, edit a registry list or make a JSON file.**
`ConfigField` defaults work without a separate JSON file when
`default_config=""`.

When combining shapes, you may use existing `Scene` utilities (e.g.
`fixation`, `line`, `ellipse`, `annulus`, `gabor`) **within the new
class's render()**. You never edit a shared dispatch table or another class
to register new stimulus mathematics; put entirely new mathematics directly
in your new class's render() method.

### Reference CSF

`CSFGrating` in the same library owns the exact reference GLSL shader.
It is a special hardware-rendered class, **not** an ordinary NumPy
`render()` preview. Do not substitute a teaching Gabor and assume
equivalent luminance, phase or timing. Its historical experiment definition
and hardware driver are internal to `_reference_csf/`.

The new `experiments/contrast_sensitivity.py` is a separate protocol using
`ContrastSensitivityGrating` and `GaussianFixation`, ordinary NumPy renderers in the
same library. Its thesis defaults can be overridden through the TUI. It requires
separate physical qualification before human acquisition; it does not establish
rendering equivalence with the historical shader.

## 2. Preview the stimulus

Restart the main TUI after editing the shared file. In USER_env:

```cmd
python -m psychophysics_lab --dev-preview fixation_cross
```

Replace `fixation_cross` with your class's `SPEC.id`. The terminal prints
the saved PNG path, which you can open in Windows. **No physical stimulus is
displayed or calibrated by this command.** No separate stimulus Ready/Publish
step is needed; software validation does not qualify your lab hardware.

## 3. Write the experiment

Create **one** experiment Python module, such as
`src/psychophysics_lab/experiments/my_task.py`, describing the condition
order, `TrialTimeline`, response meanings, adaptive science and `procedure(run)`.
Declare defaults with `ConfigField` in that Python file; a companion JSON is
optional for saved settings. Export `SPEC` with `SPEC.id == "my_task"`; discovery
needs no registry edits. See
`experiments/example_experiment.py` for a *left/right worked example*, or
`experiments/ellipse_2d.py` for a development-only advanced procedure.
Neither example should be blindly copied as a scientific design.

The experiment uses **registered stimulus IDs** from the one library; it
controls when and where each drawing appears. Beep is optional:

```python
from psychophysics_lab.researcher import TrialTimeline, Show, CollectResponse, Beep

TRIAL = TrialTimeline((
    Show("fixation", slot="fixation", duration=500),
    Show("probe", slot="target", duration=200, beep=Beep(450, 35)),
    Show("blank", duration=150),
    CollectResponse(actions=("above", "below"), beep=Beep(550, 35)),
))
```

Omit `beep=` for silence; the beep at response happens after an accepted
key. Software audio requests are not hardware-synchronisation evidence.

## 4. Test and register your experiment

For a manually authored file called `my_task.py`:

```cmd
python -m psychophysics_lab --dev-stage experiment my_task
python -m psychophysics_lab --dev-test my_task
python -m psychophysics_lab --dev-ready experiment my_task
```

You can also use **Build Experiments → Register existing experiment as Draft**
after writing the Python file. The first terminal command **only registers the existing file as a Draft**. It does
not generate anything. Run the test again after source/JSON edits, then mark
the tested revision Ready. Restart the TUI to reload the experiment catalogue.
Physical human acquisition still requires the appropriate monitor calibration.

`experiments/probe_above_below.py` now owns the built-in above/below procedure.
Its old JSON design/loader are retained internally for saved-data interpretation
and parity tests, not offered as a competing authoring route. The reference CSF
uses a retained shader implementation pending scientific/hardware equivalence.

**Remember:** stimulus = appearance; experiment = conditions and time;
framework = hardware, responses, calibration, storage.


## 5. Run and find the data

In the TUI select your experiment and a display profile, configure values, then
Review → Run simulation. For human acquisition, satisfy the profile's calibration
checks and use Run human experiment. Draft/Test/Ready describes software testing;
it cannot certify physical display, input or acoustic timing.

The TUI prints the run folder under your selected external data repository.
Read `trials.tsv` for accepted responses, `trial_actions.json` for interpreted
responses and scientific state, `stimulus_parameters.json` for actual stimulus
parameters, and `manifest.json` for source/version provenance. Adaptive runs also
save complete staircase histories. Check a run with
`python scripts/validate_run.py <run_directory>`.


## Read the experiment as a participant's sequence

Open `experiments/contrast_sensitivity.py` for the current thesis example. Read the constants,
then `make_trial()`: fixation -> grating alone -> fixation and left/right response.
`change_contrast()` gives the response-to-next-trial rule; `procedure()` chooses
conditions and repeats trials until the declared staircase stopping rule. `SPEC`
at the bottom connects those scientific choices to the TUI. Recording and source
metadata are handled by PsyCoLab. The old CSF compatibility definition is internal
and is not a template for a new experiment.


## The same reading pattern in every experiment

Follow the [experiment folder guide](../src/psychophysics_lab/experiments/README.md).
All nine files put settings, conditions, stimulus preparation, one trial,
response/adaptation, the run loop and the framework connection in the same order.
Use `probe_above_below.py` as the small fixed-trial example. Internal discovery,
validation and historical loaders are in `_internal/`; researchers do not edit
those files when changing scientific behaviour.


## Explicit response and update calls

All experiment files now share the same executable main loop and helper input/
output contracts. `make_trial(settings, condition)` describes only what is shown,
when input is accepted and optional observation markers. The procedure enters
`run.trial()`, then explicitly calls `interpret_response()` and `update_experiment()`.
The shared recorder saves once when that trial context ends. See the
[folder guide](../src/psychophysics_lab/experiments/README.md) for the complete flow.
The public CSF source is `contrast_sensitivity.py`, with menu name Contrast
Sensitivity; source attribution remains documented, and old saved-run IDs retain
their original meanings.
