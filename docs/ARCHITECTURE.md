# PsyCoLab architecture — one mental model

```text
Researcher
  ├─ stimulus_library.py        appearance, units, reusable Scene building blocks
  └─ experiments/<task>.py      conditions, visual placement, chronological trials
          │
          ▼
    ExperimentSpec + TrialTimeline
          │
          ▼
    PsyCoLab core runner
      ├─ monitor calibration and input validation
      ├─ shared simulation / human RunContext + trial actions
      ├─ scientific/adaptive algorithms
      └─ canonical data / provenance in an EXTERNAL data folder
```

The normal workflow requires **one shared stimulus file** and **one Python
experiment per task**. It does not generate new stimulus modules. All
framework internals are for engine maintenance, not researcher editing.

## Current public CSF path and historical reference boundary

The current `contrast_sensitivity.py` experiment owns its chronological Python
`TrialTimeline`, response interpretation and staircase update. It uses
`CSFGrating` from the shared stimulus library and the **normal shared
RunContext/runner** for synthetic and physical presentation. The retired
`_reference_csf` shader/driver and `libC.py`/`packages.zip` are **not tracked
runtime components** on this revision of `main`; do not install them or assume
they are a second active scientific implementation.

Historical comparisons and migration notes are retained as dated evidence
in [CSF action migration](CSF_ACTION_MIGRATION.md), not as present-day installation
requirements. Physical display output, photometry and photon timing remain
subject to independent apparatus qualification.

## Framework-only locations

| Location | Responsibility |
|---|---|
| `src/psychophysics_lab/core/` | Trial actions, real/synthetic presentation, run lifecycle, source hashes |
| `src/psychophysics_lab/config/` | Monitor profiles, photometry, timing and geometry safety |
| `src/psychophysics_lab/data/` | External experiment workspace and append-only trial records |
| `src/psychophysics_lab/adaptive/` | Reusable staircase/state algorithms |
| `src/psychophysics_lab/stimuli/` | Registry and geometry, NOT individual drawing modules |
| `src/psychophysics_lab/ui/` | Researcher interface/inspection |
| `simulations/` | Synthetic observers/scenarios and test visualisations |
| `tests/`, `scripts/`, `docs/audit_evidence/` | Verification and preserved evidence |

This design is intended to minimise the files a scientist needs to read,
not to hide scientific assumptions: unit conversions, saved state and
physical display calibration remain explicitly documented and testable.


Each Python experiment owns its full scientific policy and exports `SPEC` for
automatic discovery. Managed Drafts continue through the existing fingerprint
gate. No companion JSON or authoring-list edit is required for a new definition.
See [the authoring contract](AUTHORING_CONTRACT.md#scientific-decisions-retained-internally)
for every shared-mechanism justification and the documented reference-CSF exception.

## Independent laboratory ownership — implemented, opt-in

The public science remains in one official `stimulus_library.py` and one Python
file per experiment. Laboratories may separately maintain an explicitly trusted
`PsyCoLab_Extensions/` source folder outside the checkout, calibration and
data directories. The loader checks namespace identities, trusted-root
containment, source fingerprints, Draft/Test/Ready state and portable run
provenance; it does not introduce a second renderer or experiment language.

See [laboratory extensions](LABORATORY_EXTENSIONS.md) and
[Windows acceptance](ISSUE80_VALIDATION.md). The ability to load independently
owned code is implemented and tested; software Ready and extension trust are
**not** physical display/protocol qualification.
