# USER_env: develop scientific components before publishing them

**Researcher objective:** choose or create a stimulus, edit its Python/parameter
JSON, assemble trial phases and timing in experiment Python/timeline JSON,
simulate the response/adaptive loop, inspect reproducible saved data, then
explicitly mark the tested revision **Ready**. You should not need to edit the
runner, calibration engine, data storage or TUI for a new static experiment.

## Architecture and scope

| You author | PsyCoLab manages |
|---|---|
| `stimuli/my_stimulus.py` and `configs/stimuli/my_stimulus.json` | parameter schema checks, degree-coordinate grid, preview |
| `experiments/my_experiment.py` and `configs/experiments/my_experiment.json` | ordered trial phases, response events, standard saving |
| Optional adaptive algorithm and selected response mappings | simulator, virtual observer, adaptive recording, trial metadata |

Both the CSF and new experiments use a common *chronological phase model*;
the validated legacy CSF OpenGL presentation remains retained. USER_env's
teaching presenter currently supports **sequential static grayscale phases**.
It does **not** implement verified subframe/flicker/SOA timing, arbitrary
compositing or dynamic animations. Those belong to subsequent development
stages and require frame/photodiode verification on laboratory hardware.

## 1. Start the development workbench

On Windows, double-click **`run_user_env.bat`**. On first use this creates a
separate project `USER_env/` Python **3.11** virtual environment, installs the
package in editable mode, checks requirements, and launches the development
workbench. Network or a local dependency cache may be needed for the first
installation. Subsequent launches reuse it. Alternatively, from an existing
working PsyCoLab Python 3.11 environment:

```text
python -m psychophysics_lab --user-env
```

From the normal PsyCoLab TUI, **Build Stimuli → Open USER_env test workbench** or
**Build Experiments → Open USER_env test workbench** opens the same workbench.
If the separate `USER_env` interpreter exists, the normal TUI launches it;
otherwise it uses the current Python environment and tells you which interpreter
was selected. Dependency isolation therefore requires the `.bat` bootstrap.

**Security:** a Python virtual environment is **not** an operating-system
sandbox. Authored Python has the permissions of the logged-in user. Only run
code you trust. Development outputs go under the user directory
`~/PsyCoLab_USER_env_data/<checkout-hash>/`, isolated from human runs and saved
monitor measurements. The virtual observer never certifies physical calibration.

## 2. Build or edit scientific source

**Build a stimulus:** enter a new lowercase identifier; choose Create stimulus
draft. PsyCoLab generates a Python renderer and parameter JSON. Open either
file from the workbench. Keep the parameters and units consistent, and return
an array of valid [0,1] digital grayscale values. Preview the generated stimulus
using the real renderer; the preview PNG is saved under USER_env_data/previews.

**Build an experiment:** choose Create experiment draft. PsyCoLab generates a
working procedure and a timeline JSON describing sequential phases, such as
fixation → target → blank → response. Python determines experimental conditions,
responses and optional adaptive updates. JSON declares phase order and durations;
`{"field":"fixation_ms"}` refers to an experiment configuration field.

Use the **Experiment configuration JSON** editor inside USER_env to change the
same public configuration values and response mappings used by normal Configure
Experiment. After changing Python declarations, close and reopen USER_env to
refresh imported metadata. Each test itself starts in a fresh Python subprocess
and always imports the current source. Invalid or unfinished drafts report their
own errors; they do not register as ordinary human experiments.

## 3. Test and inspect

1. Select the draft experiment and check the fields in its JSON configuration.
2. Choose **Test experiment (virtual)**. PsyCoLab executes the real public
   scientific procedure with a virtual observer, never a participant.
3. The test must finish with `status=completed`, and the full saved-run validator
   must pass. Otherwise the draft remains untested.
4. Inspect the recorded run folder, `trials.tsv`, source/config snapshots,
   `trial_presentations.json`, `phase_events.json` where present, and the
   independent static storyboard `previews/<experiment>_timeline.png` when
   available. A storyboard depicts the *intended default phase order*, not
   measured display onset or condition-dependent overrides.
5. Edit the scientific files and retest as often as needed. File changes
   invalidate the old tested source fingerprint for publication.

**Stimulus test:** choose **Preview stimulus**; it validates the current JSON and
renders through the same grayscale function used for presentation. No actual
luminance or timing is measured. The old and new human acquisition paths remain
outside USER_env. A simulation PASS is not a human-readiness pass.

## 4. Mark a component Ready

When a stimulus preview or experiment simulation passes, USER_env records a SHA-256
fingerprint of the Python source and corresponding parameter/timeline JSON in
`authoring/components.json` (automatically maintained). Choose **Mark stimulus
Ready** or **Mark experiment Ready**. Publication fails when source or JSON has
changed since its last successful test. Authored stimulus/adaptive dependencies
must also be Ready before an authored experiment can be published.

Only components marked **Ready** join the **normal experiment catalogue** after
returning from USER_env or restarting the normal TUI. Drafts stay separate. Users
never edit `contributions.py` manually for these generated components. These
statuses are *software-development statuses*, not calibration certificates:
normal human-experiment preflight still applies its full scientific hardware
and participant/session requirements.

Existing built-in CSF and Orientation examples remain available regardless of
student drafts. A broken or incomplete draft cannot block the built-in run list.

## 5. Limits and stages beyond this pull request

- **Stage 2:** dynamic animation, multiple simultaneous stimuli, high precision
  frame-indexed timing, SOA/flicker and hardware-onset validation.
- **Stage 3:** rebuild one real ellipse/flanker experiment through the public
  architecture to test comprehensibility and scientific correctness.
- **Stage 4:** migrate CSF's presentation runtime only after scientific regression
  and hardware parity; the existing CSF remains the reference meanwhile.

Do not treat a virtual test or a digitally rendered storyboard as verification
of physical luminance, temporal accuracy or participant response latency.
