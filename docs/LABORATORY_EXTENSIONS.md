# Independent laboratory extensions (Issue #80)

PsyCoLab can load one explicitly trusted laboratory folder outside its checkout. It uses the same `LibraryStimulus`, `ExperimentSpec`, `RunContext`, adaptive algorithms, simulation runner and canonical recorder as official science. There is no second experiment language or runner. This feature is disabled by default.

External Python executes with your normal machine permissions. Path checks prevent accidental source confusion; **they are not a Python security sandbox**. Review code and install its dependencies in the laboratory environment before trusting it. Do not enable downloaded code that you have not reviewed.

## Verified architecture

The implementation was based on reviewed main `c88d43b` (after Issue #81 preset compatibility work). Before this change, `experiments/_internal/contributions.py` discovered packaged Python `SPEC` declarations, then loaded fingerprint-gated authored components. `stimulus_library.library_stimulus_specs()` discovered shared classes. Both entered the ordinary registries. `development.execute_user_action()` already exercised the production simulation and validator. `core.runner.run_request()` applied preflight, allocated canonical data, invoked the selected procedure, and recorded source hashes; source resolution assumed the framework root.

The extension boundary adds:

1. `extensions.configure()` stores opt-in trust and the root location in machine-local preferences. The root must be separate from source, local configuration and acquisition data. No filesystem-wide search occurs.
2. `extensions.load()` runs after official registration. It loads the single local library and `experiments/*.py` exporting `SPEC`, validates namespace/containment/collisions, and registers through the existing stimulus and experiment registries. A failed import rolls back that file's registry mutations. Built-in components remain available. Helpers use scoped, current-byte imports rather than timestamp-based bytecode caches.
3. Specs carry an optional `origin_namespace`; their paths remain relative to their own source root. `extensions.source_path()` is shared by presets, Review, source inspection and the runner. The public scientific authoring API is unchanged.
4. Local stimuli can be previewed as drafts. Only exact-source Ready experiments enter the normal experiment catalogue. Explicit development commands can load drafts for software-only testing. Every selected local stimulus and experiment must be Ready for normal execution, including when an official experiment selects a local stimulus. Human preflight and the runner reject stale/disabled sources; researcher override cannot waive software readiness. Existing hardware, protocol and override policies are otherwise unchanged.
5. The ordinary manifest gains optional `laboratory_extensions` metadata. Trial schema 1 remains exactly 20 columns; no reader imports external science to read archived data. Existing manifests are never rewritten.

One end-to-end PR contains these dependent stages. Partial source-loading infrastructure is not presented as a runnable feature on its own. No themes, outer geometry, navigation or scientific mathematics are changed.

## Folder contract

```text
Laboratory/
  Psychophysics_Collaborative_Lab/   # official framework checkout
  PsyCoLab_Extensions/              # optional independent Git repository
    psycolab_extensions.json
    stimulus_library.py
    experiments/
      demolab__left_right.py
    presets/
      left_right.json
    tests/                         # optional laboratory tests
  local_psychophysics_config/       # trust, software readiness, calibration
  local_psychophysics_data/         # acquired data and analysis
```

The external root can have any name and location. Its manifest is:

```json
{"schema_version": 1, "namespace": "demolab"}
```

Choose a stable, institution-specific namespace (3–64 lowercase letters/digits/single underscores). Every local component ID starts with `namespace__`; the experiment filename must equal `SPEC.id`. A custom experiment data-directory name must use the same prefix. This prevents accidental replacement of official science. The namespace, component ID and source hashes distinguish laboratory studies; an absolute private home path is not the portable identity.

Define stimulus classes in the one local `stimulus_library.py`, subclassing `psychophysics_lab.stimulus_library.LibraryStimulus` and declaring `PARAMETERS`, `render` and `SPEC`. Use the existing `StimulusSpec` and `ConfigField`, with `source_path="stimulus_library.py"`. No registration call or generated adapters are needed.

Each experiment defines its own normal `procedure` and exports `SPEC` from `experiment(...)`. Keep the existing seven-section scientific narrative and units. Set `source_paths=("experiments/your_namespace__task.py",)`. Optional default JSON lives under `presets/`; paths are relative to the extension root. Local helper Python may live under `experiments/` and use relative imports (`from .helper import ...`, `from ..stimulus_library import ...`). Ordinary installed dependencies use normal Python imports. Do not mutate registries during import.

The supported scientific dependency set is the library, the root manifest, and Python/JSON under `experiments/` and `presets/`. Symlinks and Windows junctions are rejected before traversal. Source dependencies outside that set are rejected. Arbitrary scientific resource files, additional external roots and external adaptive-plugin discovery are not supported in this initial boundary; reuse the existing adaptive API. Trusted code can of course call Python APIs, but unrecorded external inputs must not be treated as covered by this readiness/provenance contract.

## Windows first-run setup

**Cloning alone cannot create a sibling folder**: Git only manages its repository.
When the researcher **first launches the PsyCoLab TUI normally**, PsyCoLab
prepares a usable starter source directory beside the checkout, independently
of the default data and machine-local calibration directories:

```text
GitHub/
  Psychophysics_Collaborative_Lab/    # framework updated with Git
  PsyCoLab_Extensions/                # independent editable laboratory science
    psycolab_extensions.json
    stimulus_library.py
    experiments/demolab__left_right.py
    presets/left_right.json
  local_psychophysics_config/
  local_psychophysics_data/
```

No manual file copying or terminal setup is required to **prepare** this
starter. The example is useful for learning and can be customised by the lab,
but is **not automatically trusted or software Ready**. To enable execution,
open **Build Experiments → Laboratory Extensions**, inspect the supplied
source, tick the explicit trust checkbox and click **Enable trusted folder**.
Refresh (F5) or restart to rebuild the catalogue.

The user may choose any separate **absolute folder path** by editing the
path field and clicking **Create starter at this location**. This creates the
starter only in an absent or *empty* folder. Existing valid extension roots
are reused without rewriting any files. A populated folder lacking the
manifest is never silently modified or nested. The chosen path is retained
in local preferences even after disabling extensions, and data/calibration
remain separate.

From a newly cloned Windows checkout, a normal startup is sufficient:

```powershell
.\.venv\Scripts\python.exe -m psychophysics_lab
```

After explicit trust/enable, inspect discovered components:

```powershell
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-list
```

Existing CLI trust is also supported for researchers who have already
prepared a complete external folder:

```powershell
.\.venv\Scripts\python.exe -m psychophysics_lab --extensions-enable "C:\your-lab\my-experiments" --trust-extension-code
```

**Existing installations are preserved.** If you previously copied the
example under `PsyCoLab_Extensions/laboratory_extensions/`, keep using
that inner manifest-containing folder until you deliberately reorganise
your own source. PsyCoLab does not flatten/move it.

The starter contains a complete left/right line study, one self-contained
line class and one settings JSON. Before moving beyond the demonstration,
select a stable institution-specific namespace and update the experiment
and stimulus IDs consistently; no scientific code is silently renamed.

Test and mark this exact source revision Ready:

```powershell
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-preview demolab__line
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-ready stimulus demolab__line
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-test demolab__left_right
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-ready experiment demolab__left_right
.\.venv\Scripts\python.exe -m psychophysics_lab
```

Development preview/simulation outputs use the existing isolated `PsyCoLab_USER_env_data` workspace, never human acquisition storage. The commands print their output locations. `--dev-values path.json` accepts a plain object of experiment values when a draft needs particular required values; inspect the saved manifest to see exactly what was tested.

In the TUI:

- **Build Experiments → Laboratory Extensions** configures the folder with an explicit trust checkbox, or disables it. Use F5/restart after changing the setting.
- **Build Stimuli** lists local stimuli with a laboratory label and supplies the existing Preview/validate and Mark Ready controls for them. **Build Experiments** uses the existing authoring controls for local experiment drafts. Status and import errors are shown in the extension panel.
- After successful testing/Ready and F5/restart, select the laboratory experiment in **Experiment**, configure it, Preview/Test, Review all parameters/source files, then Simulate or Collect participant data through the ordinary workflow.
- Review opens actual local Python or presets in the configured editor. If no source editor is available, ordinary source inspection has a read-only TUI fallback.

**Software Ready does not qualify a monitor or experiment for physical acquisition.** The example still requires the existing display binding, geometry and applicable laboratory checks. No hardware qualification was simulated by these software tests. The established explicit researcher override remains available only under its existing rules and records its ordinary provenance.

Disable without deleting any laboratory source:

```powershell
.\.venv\Scripts\python.exe -m psychophysics_lab --extensions-disable
```

## Exact-source readiness

`extension_readiness.json` in machine-local configuration stores Tested/Ready records. Import success alone records neither. A successful development preview validates the selected stimulus; a successful canonical simulation and `validate_run` validate the selected experiment. Mark Ready is an explicit second action.

The fingerprint conservatively includes **all** local library/experiment/helper Python and preset JSON, plus the shared framework stimulus library, stimulus modules, adaptive modules and public `researcher.py` machinery. Changes invalidate local readiness; they do not modify scientific values or promote source. This intentionally over-invalidates unrelated components in the same laboratory folder, rather than risk missing an indirect dependency. A failed/incomplete simulation cannot mark a source Tested. Changes during import/testing are rejected. Retest and mark the exact current revision Ready, then refresh/restart.

Changing TUI values or saving a normal run preset under machine-local configuration does not edit extension source. Editing the extension's own default presets changes scientific dependencies and requires a retest. Only a single active root is supported, and changing namespaces requires explicit trust again. Missing source or dependencies are actionable errors, not silent substitution with an official component.

## Recording, portability and analysis

The normal manifest records software/package versions, exact experiment values, selected stimulus snapshots, response/adaptive metadata, and canonical file identities. Optional `laboratory_extensions` adds:

- `namespace` and `{namespace, id}` experiment identity;
- the local components used and their software readiness at launch;
- SHA-256 for each root-relative scientific source/preset file;
- the exact readiness fingerprint.

For a local experiment, `registered_source_sha256` is relative to the named laboratory root; the origin is identified in `laboratory_extensions.experiment_identity`. For an official experiment selecting a local stimulus, registered experiment sources remain official, and the optional metadata identifies the local stimulus. Neither field changes the meaning of presented/next contrast, digital luminance commands, timing, reversals, responses or thresholds.

Keep source revisions in your own backups or optional independent Git repository. A hash identifies bytes; it does not reconstruct deleted code. Archived observations and declared run metadata remain readable without that code:

```python
from psychophysics_lab.data.reader import load_run
run = load_run(r'C:\Laboratory\local_psychophysics_data\...\run_001')
```

This reader does not enable extensions or rerun experiments. Use the recorded data dictionary and resolved experiment/threshold files to interpret historical results, rather than today's source defaults. Copying a run does not establish physical calibration or scientific equivalence.

## Updates and deliberate promotion

Keep the extension folder, configuration and acquired data outside the framework checkout. Normal Git checkout/pull changes tracked framework files only. PsyCoLab never copies, deletes or promotes extension source during enable, import, testing or Ready. Tests exercise framework commits and checkout relocation and compare external source, preset, calibration and data bytes before/after. A framework scientific-code change may require retesting software readiness; it does not alter the laboratory files.

To propose official inclusion, deliberately open a framework feature branch, review/copy the chosen experiment and stimulus class into the official authoring locations, select reviewed official IDs and paths, add tests/docs and submit a PR with the original laboratory namespace and source hashes. Review scientific assumptions and compatibility before migration. Do not publish participant identifiers or private data. Nothing in this feature automatically promotes source, merges a PR, publishes a release or closes Issue #80.

## Validation and remaining acceptance

See [Issue #80 implementation evidence and Windows verification checklist](ISSUE80_VALIDATION.md) for the reported tests, changed components, pre-existing failures and required Windows acceptance. Linux/macOS work and GitHub Actions are deferred. Native fullscreen presentation on real laboratory hardware still needs researcher acceptance with the chosen display, photometer and timing equipment. The local headless TUI tests cover selection, Review, source navigation and geometry; they do not certify photons or replace that hardware check.
