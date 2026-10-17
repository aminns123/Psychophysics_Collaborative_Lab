# Build a reusable stimulus and a JSON-only spatial experiment

For the preferred shared Python drawing library, start with
`src/psychophysics_lab/stimulus_library.py` and `Scene`; see
[Learn PsyCoLab](LEARN_PSYCOLAB.md) and the
[legacy migration examples](LEGACY_STIMULUS_MIGRATION.md). The per-ID modules
below are retained registered adapters. The JSON builder's two-slot spatial
workflow remains supported, while multi-interval/adaptive Scene protocols use
separate Python procedures and the same trial runner.

**Goal:** Create one stimulus, reuse it in many experiments, and do not write a
new Python experiment file for a simple 2-alternative forced-choice task.

## Start with the working above/below demonstration

The repository supplies two **independent, reusable** stimulus modules:

| Stimulus | Science code | Defaults | Purpose |
|---|---|---|---|
| `fixation_cross` | `src/psychophysics_lab/stimuli/fixation_cross.py` | `configs/stimuli/fixation_cross.json` | Small central plus sign |
| `vertical_line_probe` | `src/psychophysics_lab/stimuli/vertical_line_probe.py` | `configs/stimuli/vertical_line_probe.json` | Vertical white line |

Each module defines `PARAMETERS` and a single `render(parameters, x_deg, y_deg)`
function. No response or data-saving code lives in a stimulus.

**Open the normal TUI → Build Experiments → No-Python experiment builder.**
The built-in **Probe Above or Below** experiment is registered and available
for software-only simulation and (with qualified calibration) human runs. Its
complete scientific definition is editable JSON:

`configs/experiment_designs/probe_above_below.json`

The JSON selects **existing** stimuli, defines conditions and response keys,
and arranges trial actions in chronological order:

```
Show fixation_cross (centre)                       500 ms
RecordState(before_probe)                            no display action
Show fixation_cross + vertical_line_probe           200 ms
   probe at (0, +2°) if above / (0, -2°) if below
Show blank                                           150 ms
CollectResponse(above=F, below=J)                     wait for key
RecordState(response_received)                        no display action
UpdateState(correct_count)                            no display action
```

A **single shared Python executor** in
`src/psychophysics_lab/experiments/library_builder.py` runs these validated
designs through the normal `TrialTimeline` / `RunContext` services. It
does not contain bespoke code for this example; other simple spatial
experiments use the same engine.

## Create your own line stimulus from scratch

In the TUI → **Build Stimuli**, enter an unused lowercase identifier such as
`my_white_line`, then choose **Start minimal vertical line**.

PsyCoLab creates:

- `src/psychophysics_lab/stimuli/my_white_line.py`
- `configs/stimuli/my_white_line.json`

Only edit **PARAMETERS** (scientific ranges/units) and **render()** (the
appearance). The JSON controls default values. Do not edit the framework's
drawing, coordinate conversion, keyboard or storage services.

Use **Preview / validate** then **Mark Ready**. This means the current Python
and JSON passed software checks; it is **not** a photometric/timing certificate.
The published stimulus then becomes selectable from the shared library.

## Build a NEW above/below experiment without Python

Open **Build Experiments** and use the **No-Python experiment builder**:

1. Select the Ready fixation stimulus and your newly Ready line.
2. Give the experiment a new name, e.g. `my_above_below_test`.
3. Choose an offset (e.g. 2 degrees) and select **Create JSON experiment**.
4. Click **Inspect / edit JSON** to modify the parameters and ordered actions.
5. Click **Simulate / validate** — software-only virtual observer and canonical
   saved-run validator, in separate development data.
6. Click **Mark Ready**. Restart the TUI if the normal experiment catalogue has
   an older in-memory selection.

Now the experiment is available through **Configure Experiment** and uses
the same calibration and run/storage services as other public experiments.

You can also use the plain USER_env terminal:

```cmd
python -m psychophysics_lab --preview-stimulus vertical_line_probe --preview-output vertical_line.png
python -m psychophysics_lab --library-list
python -m psychophysics_lab --library-create my_above_below_test --library-probe my_white_line --library-fixation fixation_cross --library-separation 2
python -m psychophysics_lab --library-test my_above_below_test
python -m psychophysics_lab --library-ready my_above_below_test
python -m psychophysics_lab --list-experiments
```

**Never edit** the library catalog by hand to grant Ready. A successful
simulation/validator records a digest of the exact design plus its registered
stimulus Python/JSON sources. Altering any of these files requires retesting.

## What the JSON-only builder supports (and does not)

This first authoring route supports **two-position, two-response static
stimulus tasks**. All visual phases use reusable registered stimuli; the
response and state actions use the universal core execution engine. No extra
Python experiment file is generated. Digital grayscale is **not** measured
optical luminance. Software/virtual timing is **not** photon or HID timing.

For custom trial-order algorithms, conditional branching, dynamic animation,
staircases, flicker, time-critical overlays or advanced analysis, use
**Build Experiments → Advanced Python experiment** with the same public
`TrialTimeline`. The legacy CSF acquisition renderer remains unchanged
pending scientific equivalence and hardware qualification.

**Safety:** developing/simulating and being ready for a human participant are
different states. Normal human preflight still requires the monitor's relevant
calibration evidence. Arbitrary USER_env scripts are not sandboxed.
