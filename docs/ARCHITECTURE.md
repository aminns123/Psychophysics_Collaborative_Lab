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

## Working reference CSF boundary

The CSF uses the same public registered experiment and calibration gateway.
Its shader is defined by `CSFGrating` in the shared stimulus library.
For actual human presentation it still enters an **internal** reference
driver at `src/psychophysics_lab/_reference_csf/` rather than the generic
NumPy Scene / `TrialTimeline` presenter. This is a *technical compatibility
boundary*, not a competing authoring design. It exists because physical
shader, temporal, response and adaptive equivalence remain incomplete.

All former root folders `Events/`, `Experiments/`, `Functions/`,
`Interface/` and `libC.py` have been removed from current source paths;
the same trusted CSF routines are now bundled within the package. Work to
remove the internal reference driver must satisfy the quantitative
comparison checklist in [CSF_ACTION_MIGRATION.md](CSF_ACTION_MIGRATION.md).

## Framework-only locations

| Location | Responsibility |
|---|---|
| `src/psychophysics_lab/core/` | Trial actions, real/synthetic presentation, run lifecycle, source hashes |
| `src/psychophysics_lab/config/` | Monitor profiles, photometry, timing and geometry safety |
| `src/psychophysics_lab/data/` | External experiment workspace and append-only trial records |
| `src/psychophysics_lab/adaptive/` | Reusable staircase/state algorithms |
| `src/psychophysics_lab/stimuli/` | Registry and geometry, NOT individual drawing modules |
| `src/psychophysics_lab/ui/` | Researcher interface/inspection |
| `src/psychophysics_lab/_reference_csf/` | Internal, still-active physical CSF reference implementation |
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

## International ownership boundary (planned)

The core and public experiment layers above are implemented. Machine-local
presets, monitor calibration and external acquisition records already live
outside the source checkout. A *third* layer for independently loadable
`PsyCoLab_Extensions/` Python studies is a reviewed future change: current
experiment discovery and registered source hashing assume repository-relative
code. See [the international roadmap](INTERNATIONAL_LAB_ROADMAP.md) before
changing discovery or experiment source-path semantics.
