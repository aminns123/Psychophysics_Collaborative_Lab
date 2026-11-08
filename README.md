<p align="center">
  <img src="docs/images/psycolab-logo.png" alt="PsyCoLab" width="900">
</p>

# PsyCoLab — Psychophysics Collaborative Laboratory

**PsyCoLab is a scientist-first psychophysics laboratory for designing,
understanding, configuring, testing and sharing reproducible experiments
through readable Python protocols and a consistent researcher interface.**

Read one Python file to understand a study's conditions, stimulus placement,
trial sequence, responses and scientific methods. Independent stimulus classes
define reusable appearances. Configure the existing study through Review and
save your choices in local JSON. When you want to develop a new protocol, you
can write it in your own laboratory folder and use the same interface and runner.

## Start on Windows 11

PsyCoLab's supported release target is **Windows 11 with 64-bit Python 3.11**.
Follow the [installation guide](docs/INSTALLATION.md) for the complete source
checkout and first-time setup.

1. Double-click **PsyCoLab.bat**. Choose **Check / Repair PsyCoLab** for initial
   setup or recovery, then **Launch PsyCoLab**.
2. Open **Experiment**, choose a study and display profile, set the common run
   controls in Configure, then open **Review**.
3. Select a scientific parameter and choose **Edit selected value**, or open
   **Edit inputs / stimuli** to see all declared inputs. Apply your changes to
   Review. Shared Python defaults stay available for future configurations.
4. Use **Save configuration** to keep your setup locally. Use **Export JSON…**
   to share it in portable schema 2, or **Import JSON…** to preview differences
   and approve a new local copy. Compatible experiment and stimulus source
   must already be installed. For a version 1 transfer, ask for a fresh export
   from the verified original settings. See the
   [sharing guide and ellipse example](docs/SHARING_CONFIGURATIONS.md).

Use **Python Workspace** from the launcher to run your own scripts in the
PsyCoLab environment. If you have an old shortcut, use the
[launcher migration guide](outdated_code/windows_launchers/README.md#migrate-existing-shortcuts-and-automation).

## Inspect, test and record

| Action in Review | What you can learn |
| --- | --- |
| **Try the experiment** | Inspect actual trials on the selected display with your keyboard. Test records are kept separately from participant data. |
| **Simulate responses** | Exercise the configured study and inspect saved software results with a virtual observer. |
| **Collect participant data** | Run the study in the selected external data workspace after the acquisition checks pass. |

Review shows the selected study's effective settings, their units and what
controls them. The same scientific definitions drive Review, Test, simulation
and Run. Saved records capture source identity, selected configuration, local
display provenance and accepted responses. Use the result page or the read-only
[Python data reader](docs/ANALYSING_RUN_DATA.md) to inspect saved runs.

Each laboratory must qualify its own apparatus and protocol before making
acquisition claims. A shared configuration carries scientific settings, while
display geometry, luminance, sampling and physical timing depend on local
measurements. See the [display setup and calibration guide](docs/TUI_AND_LOCAL_DISPLAYS.md).
Command-line simulation defaults now use the **current public**
`contrast_sensitivity` protocol. See [simulation testing](docs/SIMULATION_TESTING.md).

## Develop or contribute a study

Start with the [researcher walkthrough](docs/LEARN_PSYCOLAB.md) and the
[progressive laboratory examples](examples/laboratory_extensions/LESSONS.md).
The [scientist-first authoring guide](docs/SCIENTIST_FIRST_AUTHORING.md) explains
A1/A2/B, the shared [stimulus library](src/psychophysics_lab/stimulus_library.py)
and the [official experiment files](src/psychophysics_lab/experiments/README.md).

Use [independent laboratory extensions](docs/LABORATORY_EXTENSIONS.md) to keep
your own Python protocols and stimuli outside the official checkout. Explicitly
trust and test laboratory source before marking it software Ready. To propose a
fix or contribute an experiment to the official catalogue, see the
[contributor guide](CONTRIBUTING.md).

## Release status and citation

The current source includes work after the published
[`v0.3.0` research pre-release](https://github.com/aminns123/Psychophysics_Collaborative_Lab/releases/tag/v0.3.0).
For tested revisions, remaining Windows 11 acceptance and distribution decisions,
see the [release policy](docs/RELEASE_POLICY.md) and [changelog](CHANGELOG.md).
Keep participant records, calibration and lab-owned source separate from the
checkout when [updating or moving computers](docs/SAFE_UPDATES_AND_LOCAL_WORK.md).

Use [CITATION.cff](CITATION.cff) to cite PsyCoLab and report the exact source
revision used in your study. Project licensing and distribution approvals are
tracked in the [release checklist](docs/RELEASE_POLICY.md#before-a-stable-release).
