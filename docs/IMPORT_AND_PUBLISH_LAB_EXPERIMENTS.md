# Import a scientist's experiment into PsyCoLab — without custom Python tests

The maintained framework source is **not** a dumping ground for laboratory
experiments. The correct architecture has two catalogues sharing one runner:

- **Official**: reviewed and versioned Python experiments and stimulus classes
  maintained in this Git repository.
- **Laboratory**: researchers' own Python files in one trusted extensions
  folder, with a distinct namespace. Once **Test → Ready** is satisfied they
  become selectable in the **same Experiment dropdown** as official studies,
  labelled as laboratory-owned. They are not automatically official or
  physically qualified.

Both catalogues use the same experiment/stimulus registration, event-first
timeline, adaptive/constant methods, canonical recording and source
provenance. There is **no separate local execution framework**.

## Starting with an existing experiment file

1. Start PsyCoLab and open **Build Experiments → Laboratory Extensions**.
2. Create/enable an external root with `psycolab_extensions.json`,
   `stimulus_library.py`, and `experiments/`. Explicitly inspect and trust
   the Python; this is **not** a security sandbox.
3. Enter the absolute path to your completed **namespaced** source, e.g.
   `C:\LabProjects\demolab__my_ellipse.py`, and click
   **Import existing experiment .py (Draft)**.
4. The source is AST-checked, copied **byte-for-byte** to
   `experiments/demolab__my_ellipse.py` with exclusive creation (no
   overwriting). The TUI offers to open it. There is no execution on import,
   no hidden scientific rewriting, no automatic Ready or official promotion.
5. The experiment must export a top-level `SPEC` whose `SPEC.id` matches
   `demolab__my_ellipse`, and its local `source_paths` must point to
   `experiments/demolab__my_ellipse.py`. The current importer deliberately
   reports naming errors rather than *silently renaming* scientific identity.
6. Add any required **new** stimuli as classes in the same trusted
   `stimulus_library.py` (use **Open lab stimulus library**). Only a declared
   built-in stimulus may otherwise be selected. An experiment `.py` file
   alone is not sufficient to infer or safely copy arbitrary imported code.
   If an existing laboratory folder already contains your experiments and
   stimulus library, **enable that folder directly**, instead of copying
   each file; that retains their existing dependencies.
7. Refresh the catalogue (F5). Select the Draft experiment under
   **Build Experiments**, click **Simulate / validate**, correct any named
   registration/configuration errors, then **Mark Ready**. Local stimuli
   require their own Preview → Ready. The exact-source fingerprints are
   checked again for normal catalogue appearance.

No pytest file needs to be authored by the scientist for this standard
workflow. The generic software checker (draft PR #203) adds universal
declaration checks; PsyCoLab's current virtual run and saved-data audit already
exercise the real selected experiment procedure and record schema.

**Ready means tested software**, not a scientifically correct experiment or
physical qualification. A human must review geometry, contrast, target
mapping, overlap, threshold/stopping rules, monitor calibration and timing.

## Preparing an official contribution

When a lab experiment has passed Test → Ready, choose it in
**Build Experiments → Prepare official contribution**.

PsyCoLab writes a new, immutable, source-hash-tagged directory in the trusted
laboratory folder:

```text
contribution_proposals/
  demolab__my_ellipse__<short hash>/
    contribution_manifest.json
    experiments/demolab__my_ellipse.py
    stimulus_library.py                 # if local stimuli are used
    presets/...                         # if explicitly declared
    experiments/helpers.py              # if explicitly declared
```

The manifest proposes an official experiment ID and lists the actual
source paths, sha256 hashes, local-stimulus IDs and required review decisions.
It **does not** rewrite source imports, existing IDs, presets, archived runs,
calibration or data. It **does not** call `git push`, create a PR, or install
anything under `src/psychophysics_lab`.

A maintainer then reviews the science, chooses collision-free official IDs,
checks the source dependencies, adds official tests where essential, creates
a PR to `develop`, runs Windows CI and visually verifies rendering.
Only accepted and merged official sources enter the maintained catalogue.
The lab's original ID and source remain available, with their historical
readiness/provenance intact.

## Testing should be a button, not a programming prerequisite

For everyday local authoring, **PsyCoLab runs generic checks automatically**:
syntax/registration, effective fields and stimulus domains, event references,
method selection, virtual trials, data schema and exact-source fingerprints.
The researcher shouldn't need to know pytest or internal code architecture.

When a scientist is happy with their study, the **next automation improvement**
should be a UI-controlled reference example: choose representative scientific
settings/seed, record the requested events, geometry, stimulus-frame samples,
method results and data schema as a *named baseline*. Later source changes
automatically compare against that baseline, presenting differences for the
scientist to **accept or reject**. This is how official scientifically frozen
tests can be created without researchers writing assertions by hand. A
baseline is evidence of **changed behaviour**, not proof of scientific
correctness; deliberate protocol changes need a new identity/version.

## Code cleanup strategy

Remove genuinely obsolete paths, never the last reader of historical data or
the only implementation of a validated scientific rule. For each old
experiment:

1. Inventory which legacy functions/classes are called, which are import
   compatibility, and which are truly unreachable; identify saved-run and
   source-provenance dependencies.
2. Migrate the **scientific** source to a readable A1/A2/B file with one
   `STIMULI` map and independent stimulus classes; do not modify old
   psychophysical behaviour unintentionally.
3. Compare old/new event sequences, monitor-independent rendered frames,
   response meanings, adaptive/fixed selection, threshold values and
   canonical records. When the behaviour genuinely changes, assign a **new**
   scientific protocol identity.
4. Remove now-unreferenced helpers, duplicated orchestration and dead source
   *only after* their dependents and compatibility commitments are checked,
   and re-run the Windows acceptance suite. Do not retain duplicate paths
   indefinitely just for appearances.
5. Keep any necessary historical data reader and approved source snapshots
   available; **do not resurrect legacy runtime by copying archived files**.

Related: #202 new modular ellipse, #203 universal user testing, #201
modularisation, #200 local-to-official authoring, #198 effective parameters,
#199 new contrast contract, #197 baseline.
