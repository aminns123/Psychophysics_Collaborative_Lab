# CSF action migration: development validation, incomplete acquisition migration

**Status: PARTIAL. The retained CSF is still the default human implementation.**
No claim of full migration follows from its Phase/JSON adapter.

The shared `stimulus_library.py` and Scene adapter do not replace CSF.
`experiments/flanker_response.py` exposes the existing `CSF_SPEC` unchanged.
The development indirect/base/ellipse procedures use a separately translated
legacy flanker rule, not the current CSF staircase. See
[LEGACY_STIMULUS_MIGRATION.md](LEGACY_STIMULUS_MIGRATION.md) for source conflicts
and the distinct numeric fixture evidence.

## Captured baseline

Main ad7c132, PR42 merged. Tests capture the actual LegacyStaircaseSession event
adapter using fixed choices/responses. Immutable fixtures in tests/fixtures/csf_actions
contain canonical legacy rows and every adaptive snapshot:
- reversal_completion: 17 responses, all staircases complete.
- response_ceiling: 5 responses, global ceiling with unfinished staircases.
- initial_one_down: 20 responses, independent initial phases and configured
  3-down/2-up rules, terminated by response ceiling.

The comparison independently selects active identities and computes the numeric
contrast step through public RunContext, TrialTimeline, CollectResponse,
RecordState and UpdateAdaptive. It uses the registered consecutive_up_down
factory. It does not call the legacy event/file adapter to produce the new trace.

Tests compare trial/condition/target order, correctness, before/after digital
intensities and normalized display contrast, step direction, per-staircase counts,
reversals, active/completed identities and stop status. Adaptive snapshots match
the fixtures; numeric rows use relative/absolute tolerance 1e-12. The existing
threshold analyser returns the same staircase thresholds for projected action
state rows and captured legacy canonical rows.

## Run it explicitly

```text
python -m simulations.csf_actions --output NEW_DIAGNOSTIC_DIRECTORY
python -m pytest tests/test_csf_action_parity.py
```

Output is labelled DEVELOPMENT STATE REPLAY ONLY and must use a new directory.
This route is not registered in the human catalogue. It deliberately renders
nothing; it does not substitute a teaching Gabor/line for the CSF shader.
Its procedure lifecycle means the scheduled replay completed, while adaptive
stop status is separately retained (completed or max_trials_reached).

## Exact remaining gaps before replacement

| Boundary | Evidence now | Required next |
|---|---|---|
| Adaptive numeric/state behavior | Fixed-response fixtures and threshold comparison pass | Expand scientific parameter coverage, independently review against study protocol |
| Condition selection | Same fixed seeded chooser and response schedule in comparison | Human queue pre-generates target positions; establish equivalence of RNG consumption and real trial ordering |
| Visual phase roles | Five within-trial roles match saved plan | Match startup/instruction screens, extra leading fixation and all termination displays |
| Actual stimulus pixels | NOT TESTED by state replay | Shared dynamic renderer matching Grating_ADM, Gaussian envelope, eccentric angular coordinates, phase/speed, box/RGB output and legacy units |
| Timing and keyboard | Generic action timeout/Escape tests pass | CSF-specific timeout/held-key aliases/feedback audio parity; real frame scheduling and photon/HID measurements |
| Canonical/history artifacts | Existing human/legacy files unchanged; state projection agrees | Shared CSF procedure must fill all canonical presented/next columns, six-column legacy output and final condition files without adapter |
| Source provenance | Normal public runs retain source/config hashes | Integrate the final CSF procedure through run_request; the direct state-replay diagnostic is not a qualified acquisition run |
| Human preflight | Existing CSF checks remain untouched; normal public procedure requirements tested | Bind final new CSF renderer to identical luminance/geometry/timing checks, then on-site validation |
| Abort/failure | Generic action tests retain events before/after response; legacy tests retained | Compare complete CSF partial historical artifacts and window cleanup across both presenters |

These are substantive missing features, not merely cosmetic documentation.
The raster backend's opaque 8-bit patches cannot presently establish equivalence
to the legacy floating-point/dynamic shader and optional RGB output.
No historical CSF implementation, calibration record or human data was deleted.

## Hardware

Physical display geometry, photometer measurements, gamma/luminance mapping,
optical contrast, photon timing, audio and keyboard latency: NOT TESTED.
Software parity is not physical verification.
