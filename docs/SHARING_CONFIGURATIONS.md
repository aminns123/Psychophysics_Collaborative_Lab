# Share an experimental configuration

Configure → Review → **Save configuration** → **Export JSON…** → share the file →
**Import JSON…** → Preview → Approve → Review → Test → Run.

Experiment and stimulus Python files define scientific behaviour. JSON stores
the researcher's selected settings. Sharing a configuration does not install
source code, transfer participant data or qualify another laboratory's apparatus.

## Researcher workflow

1. Configure your experiment in Review and its existing parameter editors.
   For example, select `ellipse_centre`, edit probe length/width, choose the
   adaptive settings and timings, then **Apply to Review**.
2. **Save configuration** creates a complete new local save. Existing saves
   remain intact. The saved location appears in Review. No source file changes.
3. **Export JSON…** lets you choose a folder and filename. Share that JSON file
   with your colleague. Export never replaces an existing file; choose a new
   filename when making another version.
4. The recipient opens Review for a local configuration, then **Import JSON…**.
   Browse to the downloaded file or paste its path. **Saved configurations…**
   browses earlier local saves. The file identifies the experiment; the recipient
   does not need to select the same experiment beforehand.
5. **Preview import** shows every selected scientific setting, its current and
   imported values, and which values differ. The current configuration stays
   active. Resolve any compatibility or validation errors, start a recovery
   draft if offered, or Cancel.
6. **Approve import** validates again and saves a new local copy before opening
   Review. Review shows the imported values and their scientific meanings, using
   the existing editors for subsequent changes. Back returns to the preceding
   Review. The downloaded file is no longer required after successful import.
7. Check the settings, Test locally and complete the normal acquisition checks
   before Run. Save/export again if you change the configuration.

## What the JSON contains

The portable container uses `format: "psycolab.experiment.configuration"`
and `schema_version: 2`.
It embeds the existing experiment JSON (`schema_version`, `experiment_id`,
`values`) and the existing complete stimulus documents (`schema_version`,
`stimulus_id`, `parameters`), indexed by experiment slot. It also includes the
response-guidance preference and software fingerprints. There is no new parameter
registry or parallel interpretation of scientific values.

All declared values are explicit, including inactive method settings, response
keys, durations, geometry, intensity, conditions and adaptive settings. The same
installed experiment generates its trial conditions and trial-controlled
overrides from these values. A representative Review row is not substituted for
the full configuration. Random trial sequences are not exported as measured
results; repeatability comparisons must also use the same seed and execution
conditions.

The file excludes the participant ID, data location, display/profile identity,
calibration observations, qualification/override approvals, machine paths,
original configuration filenames and measured results. Scientists developing
custom text parameters should check their chosen scientific text before sharing.

## Compatibility and safety

Import requires every declared parameter and stimulus slot, with valid values.
Missing fields are reported rather than filled from current defaults. The installed
experiment and stimulus validators, bindings, geometry checks and actual planning
path remain authoritative. Existing local JSON/presets and historical results
retain their existing formats and compatibility handling.

The registered experiment, selected stimuli, shared scientific source including
the primary estimator, and NumPy/Pyglet versions must match the export's
fingerprints. A retained JSON-library study includes its verified design digest.
A laboratory extension includes the existing verified laboratory source and
preset inventory, including imported helpers. The check is conservative, so
changes within those inventories can require a new export. Use the same
separately verified environment for any additional lab-specific packages or
resources outside those inventories. Paths do not travel with the file.
Framework and laboratory source hashes normalize LF/CRLF differences. The
retained JSON-library route uses its existing exact-byte Ready digest.
A different PsyCoLab version label alone produces a warning if the checked
fingerprints and dependency versions match.

**Older portable exports.** Verified import rejects version 1 because its fingerprints
omitted scientific dependencies. Ask the sender to open the verified original
settings in Review on an installation that supports schema 2, then choose
**Export JSON…** and save a new file. A recovery draft can instead help you
carry forward individual values whose scientific meaning you can verify. Open
ordinary local experiment and stimulus files through their existing editors.
Those files and historical run records retain their existing formats.

The preset safety correction changes a configuration file included in the
engine fingerprint. Schema 2 exports and complete local saves from the
earlier candidate (`53b8cacf`) need a fresh export or save for verified import.
Keep the originals. The recovery preview can assist with rebuilding a current save.
Review the verified settings in a matching installation, or load the saved
`experiment.json` and per-slot stimulus JSON through the current parameter
editors and compare the effective values before exporting again. Preserve
the archived `configuration.json` and its original provenance.

Missing custom/third-party experiments or stimuli must be installed, trusted and
verified separately through the existing authoring workflow. JSON contains no
Python import path, installation command or executable instruction. Import uses
the installed catalogue, rejects unsupported sections and duplicate keys, and
bounds file size at 1 MiB. Malformed/invalid files and cancelled previews do not
change the working configuration. A failed staged save does not publish partial
parameter files or overwrite earlier saves.

## Recover settings as draft

1. In Review, choose **Import JSON…** and **Preview import**. PsyCoLab tries
   verified import first. When a known portable schema cannot pass it, a
   read-only recovery preview can show the historical values and reasons.
2. Choose **Recover settings as draft**. The draft has its own Review table.
   Select a row and press Enter to inspect the current field, units, range,
   original value and any suggestion. Accept, replace or reject the value.
   Missing fields remain incomplete until resolved. **Use declared default**
   is an explicit choice where a valid default is available.
3. **Compatible** rows have matching complete scientific fingerprints and
   unchanged values. They can be accepted together. **Check meaning** rows
   have matching keys and locally valid values, but their original meaning
   still needs review. Check them against the original protocol, individually
   or using **Review same-key values**. Pay particular attention to intensity
   and contrast conventions, geometry, response alternatives, and adaptive
   method and estimator definitions. **Declared migration** rows show a
   specific author-provided rule and require individual approval. Ambiguous,
   invalid and out-of-range values require a decision. **Unmapped & source**
   shows the original and current fingerprints and the unmapped entries.
4. Resolve every row and confirm your review of the original meanings and
   installed protocol. **Validate and save new configuration** uses the
   installed experiment, stimulus, geometry and planning validators. It
   opens normal Review only on success. The saved configuration describes
   the current implementation. It does not establish scientific equivalence
   with the original protocol or qualify the display.

An unresolved draft exists only while its screen is open. It has no Test, Run
or Export action. Cancel discards the draft and leaves the active configuration
and imported file untouched. Unknown portable schemas require software that
understands them. Missing or unready experiment and stimulus implementations
must be installed and verified through the ordinary authoring workflow first.

A completed recovery includes private `recovery/original.json` and
`recovery/decisions.json` files in the new local save directory. They contain
the exact original bytes, source identities, unmapped values, and the decisions
for each row. Share the new schema 2 export if appropriate. Keep the original
and report as local scientific provenance.

### Declare a migration in an installed laboratory component

The module defining the experiment procedure or stimulus renderer can publish
a `CONFIGURATION_RECOVERY_RULES` mapping. Its keys are
`("experiment", experiment_id)` or `("stimulus", stimulus_id)`, and its values
are tuples of `RecoveryRule` declarations. The experiment or stimulus must
already be enabled and Ready through the normal laboratory workflow.

```python
from psychophysics_lab.configuration_recovery import RecoveryRule

# Set these to the actual reviewed hashes from the historical export.
CONFIGURATION_RECOVERY_RULES = {
    ("stimulus", "mylab__line"): (
        RecoveryRule(
            schema_version=1,
            source_sha256=HISTORICAL_SOURCE_SHA256,
            engine_sha256=HISTORICAL_ENGINE_SHA256,
            old_key="line_length_arcmin",
            new_key="line_length_deg",
            old_kind="float",
            old_units="arcmin",
            new_units="degrees",
            meaning="Full visible line length.",
            reason="The renderer now takes degrees. There are 60 arcminutes per degree.",
            scale=1 / 60,
        ),
    ),
}
```

Use the historical outer schema and both exact lowercase SHA-256 fingerprints.
A rename without `scale` requires the same declared type and units. A positive
numeric `scale` is an explicit conversion and must pass the current bounds and
validation. The destination key and unit must be present in the current
declarations. Competing mappings remain ambiguous. Scientific changes that
cannot be expressed safely as a rename or numeric scale require manual review.
The downloaded file supplies values and historical metadata only. The
application does not import modules or execute migration instructions from it.

## Local files and run provenance

Each Save/approved Import creates a unique directory under local configuration:

```text
parameter_files/<experiment>/configuration_<unique-id>/
    configuration.json        # complete portable save
    experiment.json           # existing experiment JSON
    <slot>_<unique-id>.json    # existing stimulus JSON, for each slot
```

Review tracks the exact local JSON bytes before Test/Run, independently of the
downloaded file. Import keeps the local participant, data workspace and display
profile. Selected stimulus snapshots can retain the original portable document's
canonical content hash, schema version and software identity in
`configuration_origin`, including in the saved run's `experiment_config.json`.
Reloading the same selected component files or saving derived edits keeps this
history. The current file and effective-value hashes describe the edited
selection. Selecting an independent file or a different stimulus drops the
prior origin for that slot. Effective experiment values, stimulus snapshots,
trial records and local calibration and environment provenance describe what
actually ran. Workflows without a portable save or import have no additional
origin metadata.

## Cross-laboratory reproducibility

Equal angular dimensions and digital intensity commands do not guarantee equal
physical stimuli. The recipient retains responsibility for local screen geometry,
viewing distance, photometric mapping, refresh/timing verification, physical
sampling and apparatus/software qualification. Imported JSON neither supplies
these measurements nor marks them Verified or Ready. It never transfers a
researcher override. Existing Test and human Run boundaries still apply.

The [ellipse example](examples/ellipse_centre_configuration.json) demonstrates
probe length **1.4 degrees**, width **0.035 degrees**, explicit scientific inputs
and complete stimulus documents. Its conservative source fingerprints target
the implementation accompanying this example; regenerate an export from Review
after changing scientific software. It contains no participant or experimental
results and is not a physical calibration or approved thesis protocol.
