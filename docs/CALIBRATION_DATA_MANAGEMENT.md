# Active calibration data, live constraints and presentation testing

The latest workflow separates **saved measurements**, **physical laboratory verification**, **experiment qualification**, **uncalibrated presentation testing**, and **simulation**. None of the software-only paths certifies a display. The existing human-acquisition preflight, command guard, shader convention and staircase mathematics remain authoritative.

## Luminance workflow

Open **Calibrate → Luminance → Open / edit active luminance measurements**, or the direct luminance action on **Experiment Review** or **Experiment Qualification**. You do not need to edit JSON or unrelated geometry fields.

The page explicitly identifies no measurements, saved measurements with missing provenance, synthetic test data, measurements awaiting independent verification, verified laboratory declarations, and invalidated physical configurations. The method `used photo meter, results are fake but are test pilot` is test data. The page shows **TEST DATA — NOT PHYSICALLY VERIFIED** and explains that these values can support simulation, UI development and designated uncalibrated presentation tests. They cannot qualify human acquisition. Existing pilot values stay intact until you explicitly change or replace them.

Use the following controls:

1. **Continue / add repetitions** adds individual readings at an existing command, retaining earlier raw observations. Select an existing intensity or enter a precise command in 0–1, then enter comma-separated readings in cd/m².
2. **Add a new intensity** retains the other measured commands. Existing commands require the repetitions mode instead.
3. **Load selected raw readings for correction** shows the existing values in the numerical editor. Correct the full selected reading list, choose **Replace selected intensity readings**, and acknowledge replacement. Applying changes only the draft.
4. **Replace whole dataset** requires explicit acknowledgement. The **Reset to empty draft** button also requires acknowledgement and keeps saved data intact until Save. Changing the physical configuration requires an explicitly replaced dataset, not reusing an earlier snapshot silently.
5. **Preview import into draft** supports earlier measurement/pilot JSON and original raw `session.json` files. Choose merge, append or confirmed replacement first. It checks monitor identity and physical configuration, retains stable observation IDs and rejects means inconsistent with supplied raw readings. Single-intensity files can be previewed and combined with existing measurements; physical verification still requires a usable mapping.
6. **Save active dataset** validates the draft and updates the same active file. **Discard draft / Back** leaves the saved file intact. **Export saved dataset copy** writes only to a new, explicitly chosen file path; it does not overwrite an existing export or change the active dataset.

Every genuine repetition remains a separate observation, even if its numerical value equals another reading. Reimporting the same IDs does not add duplicate observations. Old files without IDs get deterministic identifiers based on their source session, command, value and occurrence within that value. If independently collected files have identical content without distinguishable provenance, the software cannot infer whether they are new observations; retain/export IDs or explicitly enter the new repetitions. Import previews make the resulting counts visible.

The unique command-to-luminance mapping is the arithmetic mean at each intensity. Sample standard deviation uses `n−1` and is reported only for repeated raw observations. It is not a standard error or a confidence interval. A single observation has no estimated sample SD. Historical profiles often retain only means, without raw readings or repetition counts. These remain **summary-only**, with count/SD unknown; they are not invented individual observations. Import the original readings or explicitly replace the selected summary before adding repetitions. Earlier summaries remain recoverable.

Interactive fullscreen photometer sessions continue known active raw observations. Summary-only legacy values are retained in the saved dataset, but cannot be silently combined into new raw statistics. Session/pilot files remain recovery evidence; use the editor's preview and explicit Save to merge them into the active dataset. Running a session alone does not verify or qualify the display.

## Reopening Calibration, old reports and saved test measurements

Reopening a calibration page or switching among PsyCoLab hub tabs **does not
require a new physical calibration**. The TUI only carries editable diagnostic
inputs between pages; old saved diagnostic-report selections are reconstructed
after the report list loads, rather than restored as invalid dropdown values.
A report that has been removed or is incompatible with the current monitor
must not crash PsyCoLab.

**Saved data and verified measurements are different:** a profile may contain
many recorded intensity/cd/m² pairs, including synthetic pilot data, without
the computer having a physically verified luminance curve. The **Review
physical verification** page now summarises what is already saved and explains
whether the active observation snapshot matches the selected physical setup.
It identifies changed physical fields (such as width, resolution, viewing
distance, binding or refresh) rather than merely instructing the researcher
to recalibrate.

- **Unchanged physical setup, genuine readings:** keep the existing evidence;
  do not repeat readings merely because the app restarted or a note changed.
  Declare Verified only after an actual independent laboratory review.
- **Synthetic/fake photometry:** preserve the saved data and use them only for
  simulation or designated uncalibrated presentation tests. A label such as
  `photometer fake` is not evidence. Do not change that label to make the
  software accept it; actual instrument readings must replace synthetic
  data before physical verification/human acquisition.
- **Changed physical setup:** preserve earlier records (for reproducibility)
  but do not silently reuse old photometry as if it were verified for a
  different screen arrangement. The review screen lists which settings are
  different. Retake only the relevant measurements under laboratory criteria.
- **Unreadable or stale active dataset:** use **Inspect existing luminance
  measurements** in physical verification or **Calibrate → Luminance** to
  inspect the active dataset and recovery files. No current data are deleted
  by these inspection actions. Correct/rewrite only via explicitly
  acknowledged draft replacement and Save.

**Finish calibration setup → Return to Experiment** remains available even
if physical qualification is outstanding. The actual human-acquisition
preflight remains strict; unverified, synthetic or incompatible data cannot
qualify it.

## Physical verification and qualification

Record actual observations, their instrument/method and any known optional date/notes. Inspect counts, raw readings, means and SD. Save first, then select **Review physical photometry**. The focused verification page describes the saved evidence and requires explicit laboratory acknowledgement before changed Verified declarations. Return through the measurement page to Experiment Review; its profile and readiness reload immediately.

Synthetic classification is retained on individual observations and in the saved profile. Changing the method text alone cannot relabel those readings as genuine. Replacing them with actual observations remains unverified until independently reviewed. Optional notes alone retain applicable verification. Changed readings, their provenance or instrument/method require renewed review; even an unchanged mean with new raw readings is different evidence. Physical dimensions, viewing distance, binding, pixel mode or refresh changes invalidate dependent claims conservatively. Earlier raw data stay associated with their original physical snapshot.

Qualification is a separate, explicit registered-experiment/display declaration. Its failed checks have direct actions for binding, geometry, luminance, photon timing and current contrast. The current experiment values, physical requirements and contrast command must validate before qualification. The final human launch still reloads the profile and checks current parameters and the actual connected framebuffer. A green saved calibration stage is never a substitute for those checks. The established historical reference-profile compatibility policy remains for backwards compatibility; it is not a new physical-verification claim. Saved local laboratory displays use the experiment-specific verification requirements.

## One active record, separate reproducibility history

The external participant workspace is unchanged. Within the existing machine-local configuration root:

```text
profiles/<selected-local-display-id>/
  revision_000001.json          # established immutable profile history
  revision_000002.json
  current/
    profile.json               # current committed profile projection
    geometry.json              # current geometry / latest diagnostic observations
    luminance.json             # active raw observations, statistics and provenance
    timing.json                # current rate / software timing observations
    spatial.json               # latest spatial diagnostic when available
    snapshot.json              # profile revision/hash for completed projections
    .history/luminance_*.json   # content-addressed recovery datasets
```

The saved local profile identity identifies the selected physical display and arrangement; binding, physical snapshot and profile UUID prevent mixing observations from another display. Deliberately distinct local profile copies are separate arrangements, not automatically merged merely because an OS device label matches.

Opening, navigating and discarding are read-only. Explicit Save creates missing active projections or updates their existing paths. Unchanged data report **No changes to save**, preserve the active file's modification time, and do not advance profile/dataset revisions. Immutable history is retained internally only for changed saves/recovery; researchers operate on the active record. Old `revision_*.json`, measurement sessions and diagnostic records are never deleted or moved. No migration edits actual participant records.

Legacy means are migrated in memory first, then persisted only on an explicit Save/import. Identical mean-only imports retain existing applicable verification. Mean edits through an older supported profile editor synchronize the active record as summary-only data and retain the former raw dataset in recovery history; they do not invent replacement raw readings. Optional metadata edits synchronize the active record without unnecessarily invalidating evidence.

Writes use the established atomic JSON replacement and file locks. Expected profile and dataset versions reject stale concurrent edits. A matching recovery dataset is durable before committing its corresponding profile revision. If the final active-file write fails, the committed unverified profile and matching recovery observations remain available; reopening finds that matching recovery snapshot and an explicit Save repairs the active file without creating another profile revision. Current projections are conveniences; immutable profile revisions remain the acquisition/replay authority.

## Choosing background luminance while configuring an experiment

Open **Experiment → Configure → Experiment** (Contrast Sensitivity).
Immediately above the **Background luminance** field, use **Select background
luminance and digital intensity from this monitor**. Options pair an intensity
command (0–1) with the **mean cd/m²** of all saved observations at that
intensity; repetitions are **not** separate choices. The full-command
endpoint at intensity 1.0 can determine the measured maximum, but is **not**
offered as a background selection because the CSF background must be below 1.

- Choose a saved row to populate **both** `Background_Luminance` and
  `Background_Screen_intensity` together. Those two fields become
  read-only while the linked choice is active. **Starting probe digital
  intensity** is separate and must satisfy the live shader-safe range.
- Choose **Manual entry** to unlock both background fields and type a
  deliberately unpaired configuration. Previously saved values/presets are
  retained rather than silently changed when a different monitor is selected.
- Use **Review / repair saved luminance measurements** directly next to the
  selector to examine/add/correct the active dataset. On return, select the
  appropriate saved row and review the new contrast limits.
- If the active raw dataset is missing or stale **but the saved profile is
  unverified**, the selector may display historical profile-stored summary
  pairs prefixed **TEST ONLY**. These preserve a useful software/simulation
  workflow, not calibrated photometry. The recorded run provenance says
  `profile_summary_unverified`; none of these values can certify human
  acquisition. Repair/re-measure the actual display before laboratory use.
- If a physically verified profile has inconsistent active measurements,
  **no fallback calibration row is offered**. Review and reconcile the
  dataset; do not silently trust one of two conflicting physical records.
- Changing the selected monitor or active calibration data requires a
  deliberate new selection or explicit Manual confirmation. No interpolation
  and no transfer of calibration from another display occurs.
- Synthetic pilot observations may be selected for simulation and explicitly
  uncalibrated test presentation, but never qualify human acquisition.

The digital-bound warning is independent of the measured cd/m² mapping:
the current CSF shader draws digital pixels
`I_rgb = I_b + (C_disp/2) sin(phi)`, with
`C_disp = (I_start - I_b)/(1-I_b)`. To avoid negative values or commands
greater than 1, the live allowed range for `I_start` depends on `I_b`.
For example, at `I_b = 0.3`, `I_start` cannot exceed `0.72` under
this specific shader. This is a **digital rendering bound**, not a
universal physical contrast or luminance ceiling. No value is silently
clamped, and later staircase steps are checked at human presentation.

## Dynamic input domains

Experiment fields show their domain beside the input, retain invalid entries for correction and highlight them. Dropdowns contain registered choices. Fixed field bounds come from `ConfigField`; cross-field and monitor checks reuse specification/preflight and existing geometry/contrast validators. They run during edits and again on submission. Live feedback is separate from Save/Review success messages. An enabled Review button does not bypass validation: configuration submission revalidates the current values, including immediately after the last keystroke.

| Controls | Domain / dependency | Authoritative source |
|---|---|---|
| Background digital command | `0 ≤ I_b < 1` | CSF specification |
| Starting probe intensity | `I_b` through the inverse of `2 min(I_b,1−I_b)`; current shader | Existing display-contrast helpers and command guard |
| Background / maximum cd/m² | Background nonnegative and below positive maximum; verified measured pair and measured full-command endpoint | Field/specification and monitor validators |
| Background mapping dropdown | Only the selected monitor's actual measured rows; manual mode retained | Saved monitor mapping |
| n-up/n-down, reversal limit, response ceiling | Positive integers | Specification/adaptive contract |
| Up/down step sizes | Positive finite legacy log10 units; no automatic scientific ratio change | Specification and registered step calculator |
| Condition count / staircase count | Conditions match the entered list, 1–24; staircases 1–24 | Specification |
| Spatial frequency / period | Positive; reciprocal period convention; monitor sampling limit and experiment ceiling | Condition resolver and spatial validator |
| Fixation/interval/stimulus duration | Positive whole milliseconds; zero stalls keyless phases | Existing CSF validator |
| Response timeout | Whole milliseconds ≥ 0; 0 is self-paced | Existing CSF validator |
| Physical width/height/distance, refresh/callback rate | Positive finite values; pixel dimensions positive integers or both absent | Profile validator |
| Ruler size, thickness, angular size / position | Positive finite size; monitor fit and position-unit bounds; viewing distance changes derived geometry | Existing geometry/diagnostic resolver |
| Spatial / temporal diagnostics | Spatial Nyquist from geometry; temporal Nyquist from refresh (sine boundary is excluded by its validator) | Spatial and temporal planning helpers |
| Patch command / sweep floor / step | Command 0–1, floor below 1, positive step at most 1; fixed 6° square must fit | Luminance session validator |
| Photometer readings / repetitions | Individual finite nonnegative cd/m²; counts/statistics derived | Raw observation validator/statistics |
| Virtual observer / seeds | Model-owned parameters and seed parser, validated during edits; registered experiment domains also shown | Observer factory and existing simulation parsers |
| Analysis retention | Fraction `(0,1]` or positive whole final reversal count | Analysis validator |

Diagnostic/profile domains are shown with current computed geometry and feedback; selectors offer finite valid choices. Fixed stimulus settings that the experiment does not expose remain fixed; no extra scientific parameter controls were invented. Unknown framebuffer dimensions are described as a launch-time check, not fabricated as detected values. Hardware accuracy still requires measurement.

For a saved mapping, the background dropdown labels each choice as `cd/m² — Screen intensity`. Selecting a row explicitly fills both original background parameters. A measured command-1 endpoint can fill maximum monitor luminance; absent endpoints are never inferred or interpolated. Starting probe intensity remains independent. Changing displays keeps entries for review, rebuilds choices from that display only, and revalidates the pair. Run metadata retains the original explicit numerical parameters.

At background 0.25, the starting domain is **0.250–0.625** under the retained `C_disp=(I_start−I_b)/(1−I_b)` and `RGB=I_b±C_disp/2` convention. No value is clamped. Initially safe contrast can exceed the range after upward updates. Current human/test presentation rejects each unsafe draw before OpenGL and retains accepted data with an error outcome. Numerical simulations do not certify physical command safety.

## Three distinct execution paths

| Action | What executes | Evidence / output |
|---|---|---|
| Run simulation | Registered virtual observer, no physical display | Existing synthetic-labelled pipeline |
| Test experiment presentation (UNCALIBRATED) | Actual registered procedure/renderer, response keys, trials and adaptive updates | Reserved `presentation_test_*` identity in an isolated marked test root |
| Run human experiment | Actual acquisition with unchanged strict certification/preflight | Established real participant workspace |

Use **Data → Latest uncalibrated test manifest / trials** to inspect the latest test records without changing the human workspace. These viewers are read-only.

Presentation testing requires acknowledgement. It validates configuration, initial shader command, physical sampling and connected framebuffer before creating a run. Its isolated root is `psycolab_presentation_tests` beside the local configuration root; existing unmarked folders and redirected roots are refused. Certified human acquisition cannot select that folder or its descendants, and cannot use reserved presentation-test identities. It does not update the human workspace's saved setup or local monitor preferences. Runtime failures return to the TUI; diagnostic reports stay in the marked test root. Failures before root allocation do not create an unmarked folder or write test reports into human data.

The CSF fullscreen caption and introductory/final messages identify uncalibrated testing. Manifest, experiment config, trial context, runtime display and an `UNCALIBRATED_TEST_DATA.json` marker retain the classification and exact profile/settings. Registered contributor procedures also receive `context.data_kind`. Normal post-acquisition scientific analysis is not automatically run for presentation tests; explicitly requested threshold figures carry an uncalibrated-test warning. These records cannot certify a monitor or qualify an experiment.

## Scientific choices and remaining hardware acceptance

No defaults, contrast convention, shader modulation, staircase updates, reversal rules or stopping criteria were changed. The current failure-before-unsafe-draw policy is retained. Possible future choices are (a) retain that policy, (b) an explicitly recorded ceiling termination with censored results, or (c) a separately registered bounded adaptive procedure. Capping commands or changing transitions alters the tested procedure; choosing an alternative requires explicit protocol approval and independent validation, not a universal “optimal” ceiling inferred by the UI.

Actual photometer provenance/response, independent photon timing, ruler measurements, selected GPU/display fullscreen behavior and protocol tolerances still need laboratory acceptance. Headless tests exercise workflow, persistence, calculations, rejection and mocked acquisition; they do not certify hardware or validate biological thresholds.

## Reproduce validation and review

Baseline on merged main: **625 Windows tests passed**. Added regression coverage includes raw means/SD, unknown legacy counts, file migration, partial/raw-session imports, repeated-import deduplication, confirmed replacement history, note-only preservation, stale edits, interrupted-write recovery, active/profile coherence, linked backgrounds, live invalid input and isolated mocked presentation acquisition. Final local/Windows/Linux results are recorded in the pull request.

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/portability_check.py
.venv\Scripts\python.exe -m pip check
git diff --check main...feature/calibration-datasets-validation-test-presentation
git diff --stat main...feature/calibration-datasets-validation-test-presentation
```

Changes center on `config/calibration_dataset.py`, `config/input_constraints.py`, `ui/luminance_data.py`, `ui/domain_feedback.py`, the existing profile/calibration/qualification/setup screens, local profile persistence and model/import compatibility, measurement sessions/diagnostics, and the dedicated presentation-testing boundary. The legacy adapter/renderer receive only the test-mode label; adaptive/stimulus mathematics remain unchanged. See the PR Files changed view for the complete inventory.

Review the dedicated branch and passing CI manually. Nothing merges automatically. After approval, merge the PR through GitHub; or, with a clean tree and main unchanged, use `git switch main` then `git merge --ff-only feature/calibration-datasets-validation-test-presentation`. If main has advanced, review and reconcile changes first.
