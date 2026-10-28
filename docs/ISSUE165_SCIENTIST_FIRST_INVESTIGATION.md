# Issue #165: executable scientist-first investigation

**Historical prototype report for PR head `9724d9f`.** The subsequent design-freeze
proposal is [EXPERIMENT_AUTHORING_STANDARD.md](EXPERIMENT_AUTHORING_STANDARD.md).
Its reference no longer imports official CSF or uses a source-hash guard; source
size and coupling descriptions below record the earlier investigation only.

Baseline: merged `main` **9776a25fd9dce39860ef620b3dd70652f9dfa113**.
Investigation is isolated from the retirement follow-up and the working lab.
No official experiment, stimulus, framework, TUI, method or recorder is changed.

## Delivered designs

The [external lab examples](../examples/scientist_first/README.md) contain two
executable Python files with matching filename, ID and declared source path:

- `demolab__csf_two_part`: Gaussian CSF, adaptive and constant-stimuli modes.
- `demolab__temporal_order`: peripheral line before/after an enlarged central
  visual cue, fixed signed-SOA schedule. This is a distinct teaching protocol.

Both retain the ordinary 20-column table. `trial_measurements` and explicit
`MEASUREMENT_UNITS` feed the existing per-trial journal; the optional derived
exporter reads those saved records and refuses to overwrite original data.
All scientific choices are in Part A. Part B uses ordinary RunContext and the
existing method loop/registration. There is no new condition framework or DSL.

## Before/after researcher-facing complexity

Counts include comments/docstrings; they measure source size, not human ability.

| Source | Lines | Functions | Science / integration split |
|---|---:|---:|---|
| Current official Gaussian CSF | 750 | 22 | Established six sections |
| Earlier supplied, unqualified CSF prototype | 412 | 18 | 227 / 185 lines |
| This Gaussian CSF prototype | 309 | 18 | 230 / 79 lines |
| This temporal prototype | 200 | 13 | 140 / 60 lines |

The previous filename `demolab__csf_readable.py` did not match its declared
`demolab__csf_two_part` ID. Its guide/exporter names also diverged. The new
directory uses one correct filename/ID per experiment, one README and the actual
`export_measurements.py` name. The supplied originals were not edited.

Previously, parameter declarations, target coordinates, measurements and
estimator details required several separate sections or reference callbacks.
Now, for example, CSF declares named left/right rows in `TARGETS`, multiplies
their coordinate signs in `target_position`, and immediately uses those positions
in its chronological event list. `change_contrast` visibly selects negative
log-down, positive log-up or zero, then calls the same bounded log10 method.
`primary_rule` explicitly declares the reversal median and across-track mean.
The temporal file reads as a different methods section: signed SOAs, balanced
repetition, seeded shuffle, before/after scoring and per-SOA response fractions.

Integration still has real costs. CSF uses the reference's named staircase
initialisation and record construction; these are not generic authoring magic.
Both examples retain small historical Review planning hooks. The CSF callback
dependency additionally needs a pinned, LF-normalised reference hash, since that
official experiment file is outside the generic extension fingerprint's shared
science dependency list. A changed reference fails validation rather than
retaining a misleading Ready state. These constraints must remain visible.

## Scientific software evidence

Exact-profile **Windows 11 / CPython 3.11.15** targeted selection:

```text
python -m pytest tests/test_scientist_first_examples.py tests/test_laboratory_extensions.py tests/test_public_run_reader.py tests/test_authoring_contract_learning.py -q
105 passed, 1 skipped in 139.87 seconds
python scripts/portability_check.py
PsyCoLab portability check passed.
```

The new investigation contributes 44 tests; the selection also retains existing
legacy-extension, public-reader and authoring-contract checks. The skip is the
existing platform-specific extension case. CI results for the final commit
belong to the associated review target, not an earlier source revision.

CSF checks cover both opening states, both strength methods and two observers
(teaching and psychometric), plus repeat runs with identical seed. They verify:

- Identical normalised defaults and constructed scientific conditions.
- Byte-identical complete canonical trial tables, including random condition/
  target choices, response keys, current/next strength, steps and reversals.
- Every saved adaptive update/session, reversal contrast history, completion,
  primary threshold result and resolved per-trial stimulus/parameter/placement.
- Fixed schedules and observed per-frequency/per-level accuracy.
- Identical incomplete termination/results at the accepted-response ceiling.
- Explicit source provenance: only the qualified `change_contrast` callback
  module name differs in action records. Its function AST and five other
  scientific function ASTs are identical before comparing that renamed label.
- Extra journal measurements, declared units, readers/validator and saved source
  identity; no extra canonical columns or changed source identity for old runs.

Temporal checks verify exact signed target-minus-cue scheduled onset, both event
orders, balanced seeded schedule, response scoring, counters, saved per-SOA
fractions, repeatable canonical trial bytes and complete measurement records.
Invalid/nonfinite/duplicate/unpaired/overlapping conditions and excessive plans
are rejected. There is no equivalent current official temporal reference, so
these tests establish agreement with the declared methods, not equivalence to
an already accepted temporal experiment or validity of a temporal threshold.

Both use the public extension loader and Test → Ready workflow. Source edits
invalidate readiness and block execution/publication; missing/nonfinite or
nonscalar measurements are rejected. Generic Review observes an edited
`trial_events` function without TUI changes. The actual software phase player
is exercised with the established injected-display harness, including CSF
adaptive/fixed modes, remapped response keys, opening on/off and zero-response
Escape aborts. The export tests preserve every original run byte and reject
overwrite/in-run destinations.

## Acceptance recommendation

**Ready for independent researcher evaluation as external examples. Not ready
to replace the accepted official authoring structure.** No real novice has yet
demonstrated independent understanding or editing. Fewer lines and green
software tests cannot prove that outcome. The six-section official experiments
remain the accepted baseline; the two-part layout is an investigation.

Ask a scientist with modest Python experience to identify and change factor
levels/order, target alternatives/placement/timing, response scoring, saved
measurements/units and stopping/results using Part A plus the stimulus class.
Then restart, Test → Ready, run synthetic data and explain the results. Record
where Part B or framework knowledge was necessary. Use that evidence to decide
adoption; do not introduce another abstraction merely to conceal the remaining
integration coupling.

Native console/novice acceptance and physical apparatus qualification are
outstanding. Injected clocks/windows/audio do not establish photon timing,
photometry, geometry, acoustic onset or input latency. These examples neither
certify hardware nor make universal hardware certification a software release
gate. Existing acquisition/calibration safeguards remain in force.
