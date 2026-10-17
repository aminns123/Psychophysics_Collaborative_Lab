# Build a stimulus and an experiment in PsyCoLab

**Two places to edit. No generator. No per-stimulus Python files.**

1. **Drawings:** `src/psychophysics_lab/stimulus_library.py`
2. **Experiments:** `src/psychophysics_lab/experiments/<task>.py`

The framework handles monitor geometry, human responses, simulation, data, and calibration.

## 1. Create or edit a stimulus

Open **Build Stimuli → Open stimulus_library.py**, or open the file directly in
VS Code. Find `FixationCross`, `VerticalLineProbe`, `TeachingGabor`,
`ResearcherVerticalLine` and `ComposedScene`. Each keeps three familiar
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

If the drawing already exists, use `Scene` and its functions (`fixation`,
`line`, `ellipse`, `annulus`, `gabor`, `grating`, `square`, etc.)
instead of copying the drawing mathematics.

### Reference CSF

`CSFGrating` in the same library owns the exact reference GLSL shader.
It is a special hardware-rendered class, **not** an ordinary NumPy
`render()` preview. Do not substitute a teaching Gabor and assume
equivalent luminance, phase or timing. CSF's experiment settings remain
in `experiments/contrast_sensitivity.py`; its hardware driver is internal
and requires separate lab qualification.

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
Write the values in `configs/experiments/my_task.json`. See
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
after writing the files. The first terminal command **only registers the existing file as a Draft**. It does
not generate anything. Run the test again after source/JSON edits, then mark
the tested revision Ready. Restart the TUI to reload the experiment catalogue.
Physical human acquisition still requires the appropriate monitor calibration.

The existing `probe_above_below` JSON experiment is preserved for historic
compatibility, not offered as a competing authoring route. The reference CSF
uses a retained shader implementation pending scientific/hardware equivalence.

**Remember:** stimulus = appearance; experiment = conditions and time;
framework = hardware, responses, calibration, storage.
