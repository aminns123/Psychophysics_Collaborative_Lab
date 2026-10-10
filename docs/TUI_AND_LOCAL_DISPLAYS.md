# TUI and machine-local display configuration

Launch your existing checkout with `run_psycolab.bat`, or run
`.venv\Scripts\python.exe -m psychophysics_lab` from its root.

## Navigation and code inspection

The header and six page buttons occupy a single fixed container at the top.
The forms scroll below it. Setup, configuration and review actions also stay at
the top, so changing page length, scrolling and resizing do not move them.
Headless acceptance tests cover 80-column and larger terminals, long content,
real clicks, resizing and configuration drafts surviving a visit to Help.

Experiment/stimulus **Inspect** actions launch VS Code with both the repository
folder and the real source location. Opening another source supplies the same
folder identity so VS Code can route it to the existing project window. The
launcher passes arguments without a command shell. A missing editor produces
an actionable TUI notification; it never pretends a static preview is editable.
If necessary, set `editor_executable` to the full Code executable path in the
local `preferences.json`. On Windows, `Code.exe` is used directly where possible.
Actual VS Code routing depends on installation/window settings and requires a
manual check, especially with an unrelated project open.

Read-only previews remain available for run records and help documents.

## Separate local configuration

The default directory is a sibling of the source checkout:

```text
GitHub/
  Psychophysics_Collaborative_Lab/   shared source/specifications
  local_psychophysics_config/       this machine's profiles/preferences/tests
    preferences.json
    profiles/<local_id>/revision_000001.json
    presets/<experiment_id>/<preset_name>.json
    diagnostics/display_geometry/<profile_id>/<date>/check_NNN/geometry_check.json
  local_psychophysics_data/         existing participant/run workspace (example)
```

The acquisition folder is still selected using the existing data workspace
controls. It may have another name/location. Local configuration must be
separate from both source and data; neither folder may contain the other.
Set `PSYCOLAB_CONFIG_DIR`, or a `config_root` entry in the existing ignored
`.psycolab_local.json`, to choose another configuration directory. Environment
configuration takes precedence. Reading configuration never migrates old data.
Existing diagnostics under an older data workspace remain there unchanged;
new diagnostics appear under local configuration. No automatic move is performed.

## Create or edit a display profile

1. Open **Display**, choose a profile and select **Edit / copy display profile**.
2. For a shared reference, use a new local ID. Enter physical width/height and
   viewing distance in metres, plus the intended refresh rate in Hz.
3. Select **Detect connected displays**, then choose the physical display that
   will present stimuli. Detection is explicit; startup/pure tests do not open
   a graphics window. Save captures the detected resolution and binding.
4. Enter measured luminance mappings as JSON objects with `screen_intensity`
   and `luminance_cdm2`, and record method/date/notes. Commands must be within
   [0,1]; measured luminances must increase with command and remain finite.
5. Keep geometry, luminance and timing statuses separate. A saved profile or
   copied reference does not itself establish physical validation.
6. Save a local revision. Revisions are numbered, preserve a stable UUID and
   reject concurrent/stale edits. Old revisions remain readable. The loader
   rejects local IDs that shadow shared reference IDs.

For a local display to run the reference CSF procedure, laboratory qualification
of that combination must precede adding `contrast_sensitivity` to its
`qualified_experiments`. This is an explicit operator declaration, not an
automated certification. Without qualification, setup excludes it for CSF;
it remains available for diagnostics. Confirm photometry, geometry, response
mapping, stimuli and timing before scientific collection.

Launch resolves the bound display. Windows Pyglet device names identify the
display even if enumeration order changes. Where an identity is unavailable,
the recorded index, desktop position and resolution must match exactly. This
fallback is conservative but cannot prove physical identity after replacement.
A missing/ambiguous display, resolution change or incompatible refresh mode
fails rather than silently selecting another monitor. Pyglet 1.5 Windows mode
rates can be integer-rounded; a 0.5 Hz tolerance accommodates 59.94 versus 60.
The configured fractional rate is retained and OS mode observations are saved.

The existing unbound `legacy_reference_display` deliberately retains its
primary-display behavior and is labelled unverified. No shared profile is
rewritten or auto-qualified. This compatibility exception is explicit in runtime
metadata and the review page.

## Editable experiment settings and presets

Fields declared by an experiment can be adjusted within validation constraints.
CSF accepts measured luminance/command values, rather than limiting entry to the
historical menu suggestions. Verified profiles enforce the measured background
pair and the full-command maximum endpoint when encoded. Numeric settings reject
NaN/infinity, booleans and fractional integers. Digital background intensity must
remain below one; starting probe intensity must be at least the background.
Unverified profiles remain visibly marked as such.

Presets are separate local JSON files, loaded/saved on the configuration page.
Saving validates them first. Presets and drafts do not mutate registered
specifications. Fixed CSF constants, conditions, staircase behavior, response
codes and legacy renderer mathematics remain intact. Loading reused settings
starts a new run. It does not resume an old staircase.

Review and acquisition use the same preflight validation. Review captures the
profile content hash; changing its revision before launch requires another
review. The legacy 30-response default remains in place. The review warns when
the ceiling is below an optimistic minimum for the requested reversal count.

## Size, position and frequency tests

Select a diagnostic from the Display dropdown. Size can be specified in mm or
degrees, thickness in mm and x/y offsets in mm or degrees from the screen centre.
Angular position uses `d * tan(theta)`; centred extent uses
`2 * d * tan(theta/2)`. Reports include the pixel-rounded size/position and the
actual angular extent from the two off-axis endpoints. A patch outside the
display is rejected. Degree size denotes a centred-equivalent physical extent;
its angular extent changes off axis and is reported explicitly.

The spatial sine diagnostic uses angular pixel positions from `atan`, reports
cycles across the patch and minimum pixels per cycle, and rejects frequencies
above the conservative pixel sampling limit. This is a diagnostic implementation;
it does not replace or relabel the reference CSF renderer's legacy 31.5 scaling
or its condition values as validated cycles/degree. Grating digital commands
are not a calibrated sinusoid in physical luminance.

Two temporal modes intentionally have different semantics:

| Mode | Definition | Example at 60 Hz |
|---|---|---|
| Binary constant cycle | 50% duty cycle with equal whole-frame on/off durations; `f = R / (on + off)` | 10 Hz = 3 on/3 off; 8 Hz rounds to 7.5 Hz = 4 on/4 off |
| Frame-sampled sine | Digital command `0.5 + 0.5*cos(2*pi*f*frame/R)` | 8 Hz has a sampled sine phase sequence; it is not a fixed 8 Hz binary cycle |

The preview and report distinguish requested/planned frequency, refresh rate,
frame counts, representation error and mode. Frequencies above `R/2` are
rejected; sine modulation also excludes the phase-dependent Nyquist boundary.
At 59.94 Hz, an eight-frame binary cycle is 7.4925 Hz. No rounding to integer
refresh rate occurs in profile/configuration handling.

The renderer requests vsync, advances by actual flip count and saves timestamps
observed immediately after `window.flip`, interval statistics and suspected
missed refreshes. These are software measurements. OS mode rate, callback rate
and software flip timestamps do not certify photon timing. A photodiode and
laboratory measurements remain required; reports do not automatically promote
timing/geometry/calibration status. A high software draw rate or missed refresh
can invalidate the intended temporal presentation. Check the saved trace.

Tests finish after the selected duration (up to 60 seconds), or Esc/Enter. New
reports stay in local configuration. Ruler measurements preserve a history of
earlier entries and never modify participant trials. Legacy diagnostic reports
remain readable but are not silently migrated into the new location.

## Reproducibility and failure handling

Each new run preserves its profile snapshot and SHA256, profile UUID/revision,
resolved settings, actual display metadata, source hashes and initial Python
random-generator state. `trial_context.json` links every row of `trials.tsv` to
that run/profile. Canonical trial columns and run folder layout are unchanged.
Derived threshold summaries record input hashes and incomplete/calibration/timing
flags separately from acquisition records.

Zero-response aborts retain a valid TSV header/readable export and an empty
compatibility response file. Recording errors propagate; setup/finalisation
errors preserve the original failure, surviving trial data and final manifest
where disk writing remains possible. The launcher returns failure for error
status. An unwritable disk cannot guarantee a final record; existing files are
not replaced with invented success metadata.

JSON replacement uses a unique temporary file and fsync. Index/profile writers
use advisory process locks on local filesystems. They cannot coordinate edits
made on disconnected machines through cloud-sync folders. Shared-workspace
last-setup convenience state remains last-writer state for compatibility;
local monitor preferences take precedence. Run records remain authoritative.

## Checks before collecting data

The automated suite uses isolated synthetic data and local configuration, pure
calculations, headless Textual clicks and mocked displays/editor processes:

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe -B scripts\portability_check.py
.venv\Scripts\python.exe -B scripts\validate_run.py <new_run_folder>
```

Manually verify monitor selection with two monitors and changed/disconnected
bindings; measure ruler size/position and viewing distance; check spatial output;
use a photodiode for frequency/dropped-frame timing; validate measured luminance
commands; and inspect two source files while an unrelated VS Code project is
open. Automated tests do not stand in for those physical/editor checks.

Collaborators can start with `docs/EXTENDING_PSYCOLAB.md` and
`examples/minimal_experiment.py`. Changes to scientific procedures still need
their own review and equivalence/laboratory evidence.
