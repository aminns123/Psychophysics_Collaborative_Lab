# PsyCoLab — Psychophysics Collaborative Lab

**Download a version:** [GitHub Releases](https://github.com/aminns123/Psychophysics_Collaborative_Lab/releases) — select a tagged snapshot to see release notes and obtain the automatic **Source code (zip)** / **Source code (tar.gz)** archives. A source ZIP is not an installer or a validated laboratory configuration; do not extract it over an existing Git checkout. See the [changelog](CHANGELOG.md) and [safe update guide](docs/SAFE_UPDATES_AND_LOCAL_WORK.md).


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

If calibration or protocol qualification is outstanding, select **Collect
participant data → Researcher override…** on Review. Confirm the displayed
requirements to start the full human experiment in the ordinary participant
workspace. The decision is recorded with the run; calibration records stay
unchanged. Display and parameter safeguards still apply. See
[Researcher override](docs/RESEARCHER_OVERRIDE.md).

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
results. The [psychophysical terminology guide](docs/PSYCHOPHYSICS_METHODS_AND_TERMINOLOGY.md)
distinguishes spatial 2AFC, temporal 2IFC and single-interval binary judgments.
The [living Windows acceptance and future stress-test plan](docs/WINDOWS_RELEASE_ACCEPTANCE_AND_STRESS_TEST_PLAN.md)
records what has been verified and what still needs laboratory evidence.
Historical reconstructions and framework helpers are internal.

## Data and laboratory setup

Participant data live outside this repository. Each run preserves its selected
settings, accepted responses and scientific provenance. Test records live in the
separate `psycolab_presentation_tests` folder beside local configuration;
simulations use reserved `synthetic_` identities in the chosen external data folder.
The end-of-run message gives the exact location.

**Calibrate** manages monitor binding, geometry, spatial consistency,
luminance, output precision and timing evidence. Output precision records
Windows-reported signal depth, obtained graphics-buffer format and optional
photometer measurements as separate evidence (see the
[output precision laboratory guide](docs/OUTPUT_PRECISION_CALIBRATION.md)).
Physical tests still require a usable monitor configuration and supported renderer.
They do not establish calibration. Current scientific protocols retain their blocks
on participant acquisition until qualified.

## Safe local research and updates

Keep run values in named local TUI presets whenever possible. On the **first
normal PsyCoLab launch**, a standalone `PsyCoLab_Extensions` teaching folder is
created beside the checkout if that folder is not already occupied. The source
is **not executed or marked Ready automatically**: explicitly trust and enable
it through Build Experiments. Its location may be changed from the TUI and
existing laboratory files are never overwritten.
For independent laboratory-owned scientific Python, use the **opt-in external extensions** facility:
[Windows setup and source-validation guide](docs/LABORATORY_EXTENSIONS.md).
Keep the trusted extension folder outside the framework checkout, calibration
configuration and participant data. Scientific source changes require retesting;
Ready status does not qualify a physical display. Official contributions still
use reviewed Git branches and pull requests.
Never overlay a new ZIP on an existing checkout or place participant data in Git.
See [safe updates](docs/SAFE_UPDATES_AND_LOCAL_WORK.md),
[contributor workflow](docs/CONTRIBUTING_EXPERIMENTS.md),
[international development roadmap](docs/INTERNATIONAL_LAB_ROADMAP.md) and
[release compatibility policy](docs/RELEASE_POLICY.md).

## Analyse saved runs in Python

The read-only [`load_run(path)` analysis helper](docs/ANALYSING_RUN_DATA.md) loads
`trials.tsv` into a dictionary of NumPy arrays, alongside the saved run
manifest and column definitions. It preserves additional named columns without
altering previously acquired records. Learn / Help also opens the code example.

## Further reading

- [Installation and moving computers](docs/INSTALLATION.md)
- [Display setup and calibration](docs/TUI_AND_LOCAL_DISPLAYS.md)
- [Experiment file guide](src/psychophysics_lab/experiments/README.md)
- [Scientific specifications and validation limits](docs/SCIENTIFIC_REDESIGN.md)
- [Researcher workflow implementation](docs/RESEARCHER_TEST_WORKFLOW.md)

Older command-line simulation defaults retain historical CSF behaviour for existing
scripts. Use the normal interface or an explicit modern experiment ID for new work.
