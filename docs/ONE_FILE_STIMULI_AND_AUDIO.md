# One-file stimulus authoring and simple trial beeps

**Open only this file to add ordinary stimulus drawing science:**
`src/psychophysics_lab/stimulus_library.py`.

There are two things inside it:

- **Primitive drawing functions** such as `fixation()`, `line()`,
  `grating()`, `gabor()`, `ellipse()` and `annulus()`.
- **Complete registered classes**, such as `FixationCross`, with all three
  of the familiar sections together: `PARAMETERS`, `render()` and `SPEC`.

To make a new stimulus, copy the smallest similar class **inside that one
library file**, subclass `LibraryStimulus`, and give it unique `PARAMETERS`,
`render()` and `SPEC`. The loader discovers these subclasses automatically:
**no new Python file, no new registry entry, and no separate defaults JSON
are required**. For a new class set `SPEC.source_path` to
`"src/psychophysics_lab/stimulus_library.py"` and `default_config=""`.
The ConfigField defaults will be used until a researcher explicitly supplies
other validated values.

Existing historical IDs with Ready fingerprints keep their adapters/JSON
and are **not** automatically registered around the publication gate. To make a combination of shapes, compose
existing drawing functions in a `Scene` instead; do not copy their maths.
The old `src/psychophysics_lab/stimuli/*.py` modules are mostly import adapters
for existing IDs, not separate researcher edit locations.

For example, an experiment creates a stimulus Scene from the library, then
describes its sequence using the public trial vocabulary:

```python
from psychophysics_lab.researcher import TrialTimeline, Show, CollectResponse, Beep

TRIAL = TrialTimeline((
    Show("fixation", slot="fixation", duration=500),
    Show("probe", slot="probe", duration=200, beep=Beep(450, 35)),
    Show("blank", duration=150),
    CollectResponse(actions=("above", "below"), beep=Beep(550, 35)),
))
```

- Omit `beep=` for **silence**. For older timeline JSON files, add
  `"beep": {"frequency_hz": 450, "duration_ms": 35}` to a `show` or
  `response` phase instead. The exact two-number JSON cue is validated.
- `Show` supports a beep at the start of *any* timed phase, including
  `Show("blank", duration=...)` when there is intentionally no image.
- `CollectResponse` beeps **only after an accepted valid response**, not
  on ignored keys or timeouts.
- The two beep numbers mirror your original `winsound.Beep(frequency,
  duration)` code; the framework uses the same Windows implementation via
  a short background thread so tone duration does not block the timed trial.
- Synthetic runs record a virtual beep event but **never play audio**.
- The logged software request is **not a measurement of speaker onset or
  sound-to-screen synchronisation**. Hardware validation remains necessary
  for experiments in which audiovisual asynchrony affects the inference.

See [REPO_SURFACE_AUDIT.md](REPO_SURFACE_AUDIT.md) for what is ordinary user
science, what stays for compatibility and why old CSF code is retained.

### Creating a new stimulus

New researchers **never run a generator** and do not add separate stimulus
modules. Open `stimulus_library.py`, add a `LibraryStimulus` subclass with
`PARAMETERS`, `render()` and `SPEC`, and reuse it in experiment files.
The framework automatically discovers the class. For physical CSF, consult
the `CSFGrating` class and the separate hardware-equivalence checklist.

