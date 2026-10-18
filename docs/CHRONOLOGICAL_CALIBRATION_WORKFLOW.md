# Calibration in order — researcher quick guide

**Aim:** make every page say *what to do*, *what PsyCoLab saves*, and *what to do next*. The seven pages are a **setup path**, not seven automatic claims of physical verification.

## Start by choosing your purpose

| Purpose | What is required? |
| --- | --- |
| **Test an experiment** | Use the connected display and valid geometry/digital intensity bounds. Existing **test/synthetic** luminance pairs may be used for uncalibrated presentations. A photometer and human-acquisition qualification are **not** required. |
| **Simulation** | Virtual observer. No display photometer required. |
| **Human acquisition** | Physically applicable monitor binding and geometry, genuine calibrated photometry, any applicable independent timing evidence, explicit experiment qualification, and final preflight. Test values can **never** be declared physically measured. |

Select the purpose under **Experiment**. You may enter Calibration and return without making new measurements.

## Seven pages — do them in this order

1. **Display:** Bind the physical screen, confirm resolution and refresh rate, enter measured active width/height and viewing distance, and save the profile. *Next: Geometry.*
2. **Geometry:** Present a ruler bar. Measure its length with a real ruler; enter the result in mm and **Record measurement**. Inspect the percentage error; saving is not certification. *Next: Spatial.*
3. **Spatial:** Present a grating, then record **Yes / No / Uncertain** for the visible spatial pattern. *Next: Luminance.*
4. **Luminance:** Open the saved command/luminance table. Keep and accept appropriate values or enter/import new readings with their real/test provenance. **Accept luminance values → Output precision** approves the mapping but does not physically verify it. *Next: Output precision.*
5. **Output precision:** Use **Inspect selected output format** to record the selected display's Windows-reported depth and actual framebuffer. Optionally conduct photometer measurements using **Halving** (near-black diagnostic) or **Fine** (adjacent command steps). Record repeated cd/m² readings and your assessment, which may be *inconclusive*. See [Output precision laboratory guide](OUTPUT_PRECISION_CALIBRATION.md). This stage never automatically certifies native panel bit depth or blocks ordinary software testing. *Next: Timing.*
6. **Timing:** Present flicker/sine diagnostics and review software frame timing. Physical photon timing needs an independent instrument. *Next: Review.*
7. **Review:** Examine saved evidence and choose **Finish calibration setup → Return to Experiment**. Human acquisition separately requires applicable measurements, laboratory verification, explicit experiment qualification, and successful preflight.


The top of each page shows a single **NEXT** instruction. Use **Next stage** when *you* are ready; merely saving a diagnostic should not unexpectedly leave the page.

## Accept existing luminance values

All reading, editing and acceptance controls are in **Calibrate → Luminance → Step 1 — Review or add saved luminance readings**. Geometry and timing remain on their respective pages; Review summarises the saved evidence.

- **Accept luminance values → Output precision** acknowledges the saved dataset for test use and opens Output precision. When opened from Experiment Review, the button returns to **Review** with Test selected instead.
- **Continue without acceptance → Experiment Test mode** returns directly to configuring a test presentation. Both actions are available whether or not display settings changed.
- If there are unsaved rows, metadata edits or typed readings, first save the changes or choose **Discard draft; keep saved values** on the Luminance page. Acceptance never silently discards them.
- **Saved values — no unsaved dataset changes** means no Save is needed. Acceptance does not rewrite the dataset, create a revision, change its provenance, physically verify it or qualify human acquisition.

Two or more saved intensity points already complete the green Luminance stage. **TEST DATA — NOT PHYSICALLY VERIFIED** remains correct after acceptance; green records setup completion, not physical certification.

On versions without the acceptance button, **Discard draft / Back → 5 · Output precision** (or **7 · Review**) keeps saved values and discards only unsaved edits. The older “Saved + unsaved draft” heading appears even when the draft is unchanged.

## Display settings changed? (especially resolution)

If Luminance shows **Saved data belong to an earlier display configuration**, there are **two clearly different choices**.

### A. Continue software testing with old test values

Choose **Continue without acceptance → Experiment Test mode**. PsyCoLab returns directly to Experiment with Test mode selected.

Old readings are preserved and marked as test-only for your present physical configuration. Choose **Test an experiment** when configuring a run. This does **not** re-verify the old measurements and does **not** qualify human data acquisition.

### B. Record a new measurement dataset for the current screen

In **Calibrate → Luminance → Step 1 — Review or add saved luminance readings**:

1. Read the highlighted old/current differences (e.g. old resolution → new resolution).
2. Tick **Yes — keep the previous readings in history and start a NEW dataset for this screen**.
3. Click **Start new measurements for THIS display**. This prepares an *unsaved, empty* draft using the current screen snapshot. No old data are deleted.
4. Choose **Test values** for fictional readings, or **Actual photometer readings** only if a real meter was used.
5. Enter each digital intensity and its measured/test cd/m² value(s). Click **Add readings to draft**; repeat for any additional intensities.
6. Review the draft table and press **Save active dataset**. The previous active dataset is preserved in recovery history. Merely opening this screen, starting a draft or changing a tab never overwrites it.

**Important:** a new dataset for the current resolution is not automatically physically calibrated. Human acquisition still requires genuine instrument evidence and independent verification. The software prevents saving an empty replacement.

If old and new physical settings already agree, you do **not** need replacement: keep or append your readings normally. Invalid/stale physical evidence is never silently upgraded to Verified.

## Wording and buttons

**Green stage** = saved stage evidence. **Verified** = a separate, independently reviewed physical laboratory declaration. **Human ready** = the experiment-specific qualification and all final preflight checks passed. These are **different outcomes**.

If something fails, the step should name the missing value or evidence and leave you on the same page. Technical JSON paths, recovery history and raw metadata belong under **Advanced**, not in the default sequence.

