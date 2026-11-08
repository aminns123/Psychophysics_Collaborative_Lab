# PsyCoLab architecture

The experiment file describes the science. The shared framework executes it.
Review helps researchers inspect and choose the settings that the run will use.

```text
Python experiment + independent stimulus classes
              ↓
Experiment specification + validated local JSON selections
              ↓
Configure / Review → Test, simulation or participant Run
              ↓
Shared presentation, methods and recording
              ↓
External run records and provenance
```

## Scientific source

The ten official experiments use one readable Python file per study and the
[A1/A2/B authoring model](SCIENTIST_FIRST_AUTHORING.md). A1 declares the
researcher's choices and chronological `trial_events()`. A2 describes
placement, scientific methods, response interpretation, stopping and results.
B connects those declarations to the shared runner and recorder through
`SPEC`. Each study has one `STIMULI` mapping. The selected stimulus classes in
[`stimulus_library.py`](../src/psychophysics_lab/stimulus_library.py) own
parameters, validation and rendering. The experiment owns how those classes
are placed and combined in each trial.

The four official ellipse and line protocols use separate stimulus layers.
The old compound `DetectionScene` remains in frozen
[historical source and pixel comparisons](../outdated_code/pre_atomic_207/README.md).
`ComposedScene` remains a supported composition class. The portable engine
fingerprint covers its `core/scene_primitives.py` helper. The limited
JSON-library route remains available for existing designs. In the official
Python files, `legacy_trial_factory` exposes the same event list to older callers.
Use the [Python authoring standard](EXPERIMENT_AUTHORING_STANDARD.md) for
new scientific protocols.

The current Gaussian and circular-windowed CSF studies have distinct envelopes
and share named scientific methods. For current installations, do not install
the retired `_reference_csf` driver, `libC.py` or `packages.zip`. The
[CSF migration record](CSF_ACTION_MIGRATION.md) documents the historical boundary.

## Configuration, execution and provenance

Configure collects common run settings where declared. Review uses the
selected experiment's fields, stimulus slots and planning functions to show
effective settings, scientific meaning and editable sources. The optional
bright-probe explanation requires the corresponding contrast convention,
log-step controls and planning hooks. Independent studies use their own
declarations without inheriting the ellipse and line explanation.
See [Configure and Review](CONFIGURE_REVIEW_BOUNDARY.md) and
[parameter authority](REVIEW_PARAMETER_AUTHORITY.md).

Ordinary local experiment and stimulus JSON store selected values. The
[portable schema 2 container](SHARING_CONFIGURATIONS.md) uses those same
documents and adds verified scientific identity. Its fingerprints cover
shared scientific source including the primary estimator, applicable
JSON-library designs and verified laboratory source. A version 1 transfer
requires a fresh export from verified original settings. Ordinary local JSON
and historical run records retain their existing formats. Imported origin
records the source of a selection, while the effective values and hashes in
the run record describe what was executed.

Review inspects the trial plan and stimulus preparation used by presentation
Test, simulation and participant Run. The shared recorder saves accepted
responses, resolved stimulus parameters, methods, status and provenance in an
external workspace. Display profiles and qualification evidence belong to the
local installation. Software validation and shared settings support
reproducibility. Physical claims require measurements on the receiving apparatus.

## Framework locations

| Location | Responsibility |
| --- | --- |
| [`core/`](../src/psychophysics_lab/core/) | Shared trial execution, presentation, lifecycle and source inventory |
| [`config/`](../src/psychophysics_lab/config/) | Local settings, sharing, monitor profiles and scientific preflight |
| [`stimuli/`](../src/psychophysics_lab/stimuli/) | Stimulus registry and shared geometry |
| [`methods/`](../src/psychophysics_lab/methods/) and [`adaptive/`](../src/psychophysics_lab/adaptive/) | Shared methods and adaptive updates |
| [`data/`](../src/psychophysics_lab/data/) and [`analysis/`](../src/psychophysics_lab/analysis/) | External records, readers and derived scientific reports |
| [`ui/`](../src/psychophysics_lab/ui/) and [`simulations/`](../simulations/) | Researcher workflows and virtual observers |

## Independent laboratory ownership — implemented

A laboratory can maintain its own Python experiments and stimulus library in
an explicitly trusted external folder, separate from the checkout, local
configuration and participant data. Namespaced components enter the same
registry and execution path. Test and Ready records check the exact source
inventory, including local Python helpers. A source change can require
retesting before the component is available for ordinary use. See the
[laboratory extension guide](LABORATORY_EXTENSIONS.md) and
[contribution workflow](CONTRIBUTING_EXPERIMENTS.md).
