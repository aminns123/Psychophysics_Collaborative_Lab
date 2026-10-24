# PsyCoLab TUI hub

The TUI is the interface for selecting an experiment, participant/session,
calibrated monitor profile, preview, simulation, review and acquisition.
The [fixed monochrome console](FIXED_CONSOLE.md) uses one shared header,
sidebar, bordered workspace and scrollbar rail on every page. Press **F6**
to focus sidebar navigation. `>` marks focus/hover, `->` the active path,
and `-` an inactive choice. Configure and Review appear as indented routes.
Scientific controls remain inside the main workspace.

**Build Stimuli** opens the official
`src/psychophysics_lab/stimulus_library.py`. Add a `LibraryStimulus`
class there, with `PARAMETERS`, `render()` and `SPEC`. No wizard,
stimulus generator or separate per-stimulus file.

**Build Experiments** opens manually written files under
`src/psychophysics_lab/experiments/` and their validated settings.
No automatic experiment copy/generator.

On first normal launch, PsyCoLab non-destructively prepares the default sibling `PsyCoLab_Extensions` folder and shows its location in **Build Experiments → Laboratory Extensions**. Researchers can create the starter at a different absolute location there. The files are not trusted, loaded or marked Ready merely because they were created.

For independent laboratory science, enable one explicitly trusted external folder in **Build Experiments → Laboratory Extensions**. Its local classes and experiments use the same previews, authoring Test/Ready controls and normal workflow. See [the Windows extensions guide](LABORATORY_EXTENSIONS.md).

**Calibrate**, **Scenarios** and **Data** are distinct operations, not
alternative places to implement stimulus science.

CSF shader source is in `CSFGrating` in the shared library;
`_reference_csf/` is an internal hardware reference driver, not
another researcher authoring mechanism. See [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md).

Settings changed in the TUI may be saved as local presets in machine-local
configuration, avoiding unnecessary edits to official Python defaults.
Trusted, software-Ready external experiments use the **normal** configuration,
Review, simulation and acquisition paths; the same physical preflight and
researcher-override rules apply. Draft/untested extensions cannot silently
enter human acquisition. See [external extensions](LABORATORY_EXTENSIONS.md),
[safe updates](SAFE_UPDATES_AND_LOCAL_WORK.md) and the
[international roadmap](INTERNATIONAL_LAB_ROADMAP.md).
