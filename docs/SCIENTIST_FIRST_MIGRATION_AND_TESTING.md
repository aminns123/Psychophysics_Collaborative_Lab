# PsyCoLab scientist-first migration — working contract

**Decision:** a researcher authors one or more independent `LibraryStimulus` classes,
then one readable experiment source: **A1** experimental choices, stimuli, positions
and chronological `trial_events`; **A2** conditions, methods, measurement and
stopping; **B** only the minimal existing framework connection.

**This is a staged migration on `develop`, not a replacement of original science.**
`main` remains the known baseline until the maintainer approves each step.

## Why a scientist should not have to write their own test code

Building a new experiment must not require understanding pytest, simulator
internals, Textual or the 20-column recorder. PsyCoLab already provides the
ordinary **Build Experiments → Simulate / validate → Mark Ready** workflow.

The generic Test now has these automated stages:

1. **Experiment contract** — effective settings, researcher-supplied validation,
   declared stimulus IDs/compatible families, session start and method selection.
2. **One actual synthetic experiment** — run the *researcher's real Python
   procedure* using PsyCoLab's existing runner and a simulated observer.
   A normal completed run is required to mark this exact source Ready.
3. **Saved data audit** — reuse the existing `scripts.validate_run.validate_run`,
   including canonical schema, provenance and run integrity; no replacement
   experimental data format.
4. **Software-only evidence** — save a machine-readable report under
   `~/PsyCoLab_USER_env_data/<repo-identity>/software_test_reports/<experiment-id>.json`.
   It is *outside* the code repository and contains no participant measurements.
5. **Source fingerprint + Ready** — only this exact tested version may be
   promoted to software Ready. Source/configuration changes require retesting.

**No custom Python test file is necessary for a new researcher experiment.**
Maintainers retain generic automated checks for shared algorithms, while
researchers can now create their own **one-click behavioural regression
reference** without ever writing test code.

### Save and compare a reference — entirely from the TUI

After a successful **Simulate / validate**, select **Save Test as reference**.
PsyCoLab stores the selected scientific settings, synthetic observer seed,
source dependencies and SHA-256 digests of canonical trials and trial-event
journals in `PsyCoLab_USER_env_data/scientific_references/<experiment-id>/`.
This does **not** copy participant data or write generated tests into the
Git repository. Earlier references are never overwritten.

After modifying a stimulus or experiment source, choose
**Compare with reference**. PsyCoLab reruns the current experiment using the
existing synthetic test procedure and compares the newest successful run
with the last saved reference. It shows which settings, trial events, data
files, responses or source dependencies changed. The scientist decides
whether a difference was intentional; a changed scientific protocol may
need a new experiment identity and new reference. The same-seed reference
does **not** prove geometry, optical luminance, display timing or actual
human stimulus suitability.

This is a first no-code regression facility, **not a replacement for the
maintainer's tests of shared low-level algorithms, historical source
compatibility and safety properties**. It can later be extended to compare
user-selected multiple test profiles and actual rendered image samples.

A passed Test / Ready result is not an ethical clearance, monitor qualification,
hardware timing measurement, scientific hypothesis test or certification that
the target appeared where the scientist intended. The researcher must visually
inspect the full combined frames, check target/response correctness, select
appropriate adaptive/fixed parameters and confirm photometry, geometry and
timing. This is the researcher's scientific responsibility.

## Contract for editable source files

```python
# A1 — WHAT, WHERE, WHEN
STIMULI = {
    "ellipse": "ellipse_ring",
    "probe": "probe_line",
    "fixation": "gaussian_fixation_spot",
}

def trial_events(settings, condition):
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        # Independently positioned objects, written from back to front:
        Show("interval_one", duration="stimulus_ms", stimuli=(
            Stimulus("ellipse"),
            Stimulus("probe", x_deg=condition["probe_x_deg"]),
        )),
        CollectResponse(actions=("first", "second")),
    ]
```

This is **illustrative**: target-dependent interval assignment and the
complete two-interval sequence belong in the actual experiment source.
The new `experiment(..., stimuli=STIMULI)` optional shorthand is introduced
in modular ellipse PR #202; it must be accepted and merged before older
experiments can use it. Do not manually add duplicate stimulus registry tables.

`Show` order means later visible stimulus coverage goes on top **only** when
the selected renderer declares transparent/alpha coverage. Existing opaque
patches retain the historical semantics until deliberately migrated and tested.

## Migration sequence and compatibility gates

| Step | Source group | Acceptance before moving forward |
| --- | --- | --- |
| 1 | New modular ellipse (`#202`) | Correct 6° semi-axis, probe/fixation, overlap, both methods, visual/Windows test; no old data change |
| 2 | Generic authoring Test (this change) | Independent existing/researcher studies pass reusable contract + synthetic data checks; explain software vs science |
| 3 | First simple teaching/line experiment | A1/A2 readable; single STIMULI mapping, no duplicate registration; same geometry/target/timing/trial bytes |
| 4 | Remaining simple orientation and probe experiments | One experiment at a time, compare saved trials and real trial events with frozen baseline |
| 5 | Existing ellipse centre/major-axis and line flankers | Decompose `DetectionScene` only after pixel-level ring/probe/flanker/fixation and contrast parity, else create a *new protocol ID* |
| 6 | CSF + circular-windowed grating | Preserve their different peak-to-peak modulation and aperture definitions, both contrast methods and saved readings |
| 7 | Independent PC/Windows release | First-time run.bat, install/update/rollback, calibration/review, reliable data output and actual physical qualification |

For each official migration, freeze before/after event order, numerical
stimulus rasters, selected contrast method/units, adaptive sequence/threshold
rules, responses and canonical TSV. **Do not silently rewrite** any old
`SPEC.id`, source hash, user preset, participant data or completed run.
Existing experiment modules may need explicit source compatibility,
but the goal is one readable scientific narrative per module.

## Naming and authoring UX decisions

- Stimulus names describe the visible object (`EllipseRing`, `ProbeLine`),
  not the experiment or a vague composite container.
- A legitimate Gabor/compound stimulus can remain an intrinsically composite
  class; generic scene assembly should be done by experiment-owned events.
- Local extension experiments keep namespace-prefixed IDs; the official
  contribution step proposes source path/ID mappings for explicit review.
- The researcher should not edit TUI/runner/registry to change stimulus
  positions, conditions, trial order, contrast, timing or responses.
- Review should always show authoritative effective scientific inputs and
  actionable validation errors (including stimulus-level bounds).
- Keep `develop` as the integration sandbox and `main` protected.

Related GitHub work: #198 scientific parameter authority, #199 draft contrast
contract, #200 authoring/promotion UX, #201 modular architecture, #202 new
ellipse prototype and #197/#82 release criteria.
