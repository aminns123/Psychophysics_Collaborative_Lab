# PsyCoLab — Psychophysics Collaborative Lab

Build a visual stimulus, describe an experiment, and try it before collecting data.

## Start

Install Python **3.11**, then double-click **run_psycolab.bat**. PsyCoLab creates
its local environment and opens the setup interface.

1. Choose **Experiment**, an experiment, and a display profile.
2. Configure its conditions, timings, response keys and adaptive settings.
3. In a stimulus panel, choose **Edit parameters** or **Preview**. Preview opens
   an image immediately; close the image viewer to continue editing.
4. Review, then choose the action you need:

| Action | What happens |
| --- | --- |
| **Try the experiment** | Real display and keyboard; eight responses by default. Escape stops. Test records are saved separately. |
| **Simulate responses** | The same configured experiment runs with a virtual observer. Observer settings are optional. |
| **Collect participant data** | Uses the selected participant and external data folder, after acquisition checks pass. |

A preview shows the selected stimulus parameters. An experiment can change those
values for each condition: **Try the experiment** shows the actual trial sequence.
Preview images are not calibrated contrast or physical timing measurements.

Test length does not change the study's stopping rules. An unfinished test does
not produce a successful threshold estimate or qualify a display.

## Edit the science

- **Stimulus:** a class in [stimulus_library.py](src/psychophysics_lab/stimulus_library.py)
  contains its parameters, drawing rule and declaration.
- **Experiment:** one Python file in [experiments/](src/psychophysics_lab/experiments/)
  contains conditions, stimulus preparation, the visible trial sequence, response
  interpretation, adaptation, stopping and primary estimation.

Start with `orientation_task.py` for fixed trials, `contrast_sensitivity.py` for
adaptive spatial trials, or `ellipse_major_axis.py` for two temporal intervals.
Different designs can use different loops; shared section order helps navigation.
TUI values control the adaptive procedure, step sizes and reversal settings.
After editing Python source, restart PsyCoLab to load it. Parameter edits preview
immediately; Python code is not hot-reloaded.

Use [the short walkthrough](docs/LEARN_PSYCOLAB.md) for editing, testing and finding
results. Historical reconstructions and framework helpers are internal.

## Data and laboratory setup

Participant data live outside this repository. Each run preserves its selected
settings, accepted responses and scientific provenance. Test records live in the
separate `psycolab_presentation_tests` folder beside local configuration;
simulations use reserved `synthetic_` identities in the chosen external data folder.
The end-of-run message gives the exact location.

**Calibrate** manages monitor binding, geometry, luminance and timing evidence.
Physical tests still require a usable monitor configuration and supported renderer.
They do not establish calibration. Current scientific protocols retain their blocks
on participant acquisition until qualified.

## Further reading

- [Installation and moving computers](docs/INSTALLATION.md)
- [Display setup and calibration](docs/TUI_AND_LOCAL_DISPLAYS.md)
- [Experiment file guide](src/psychophysics_lab/experiments/README.md)
- [Scientific specifications and validation limits](docs/SCIENTIFIC_REDESIGN.md)
- [Researcher workflow implementation](docs/RESEARCHER_TEST_WORKFLOW.md)

Older command-line simulation defaults retain historical CSF behaviour for existing
scripts. Use the normal interface or an explicit modern experiment ID for new work.
