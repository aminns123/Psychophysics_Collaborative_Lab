# Calibration in order — researcher quick guide

**Aim:** make every page say *what to do*, *what PsyCoLab saves*, and *what to do next*. The six pages are a **setup path**, not six automatic claims of physical verification.

## Start by choosing your purpose

| Purpose | What is required? |
| --- | --- |
| **Test an experiment** | Use the connected display and valid geometry/digital intensity bounds. Existing **test/synthetic** luminance pairs may be used for uncalibrated presentations. A photometer and human-acquisition qualification are **not** required. |
| **Simulation** | Virtual observer. No display photometer required. |
| **Human acquisition** | Physically applicable monitor binding and geometry, genuine calibrated photometry, any applicable independent timing evidence, explicit experiment qualification, and final preflight. Test values can **never** be declared physically measured. |

Select the purpose under **Experiment**. You may enter Calibration and return without making new measurements.

## Six pages — do them in this order

1. **Display:** Bind your physical screen; use the OS resolution and refresh; measure the illuminated active width/height and eye-to-screen distance. Save the monitor profile. *Next: Geometry.*
2. **Geometry:** Present a ruler bar. Measure the displayed length with a physical ruler; enter it in mm and **Record measurement**. Inspect the percent error. A saved measurement is **not** by itself physical verification. *Next: Spatial.*
3. **Spatial:** Enter grating cycles/degree and launch. Return to the same page, select its presentation report, and record **Yes / No / Uncertain** and any abnormality. A complete light–dark period is one cycle; bright maxima depend on phase and edges. *Next: Luminance.*
4. **Luminance:** For **Test** or **Simulation**, keep the saved values labelled Test, or record new synthetic values without pretending to own a meter. For actual laboratory photometry, record digital command (0–1), actual photometer cd/m² readings, and source. Multiple readings at the same command produce a mean/SD. Click **Add readings to draft**, then **Save active dataset**. *Next: Timing.*
5. **Timing:** Choose frame flicker/sine, select a frequency, and launch the test. Review software frame timing. It cannot alone verify emitted photon onset (use a separate sensor for physical verification). *Next: Review.*
6. **Review:** Examine saved setup. Choose **Finish calibration setup → Return to Experiment** for test/simulation. For real human acquisition, review the physically measured Geometry, Photometry and Timing categories separately and then **Check / qualify experiment**. The final human-run preflight still decides whether acquisition is allowed.

The top of each page shows a single **NEXT** instruction. Use **Next stage** when *you* are ready; merely saving a diagnostic should not unexpectedly leave the page.

## Display settings changed? (especially resolution)

If Luminance shows **Saved data belong to an earlier display configuration**, there are **two clearly different choices**.

### A. Continue software testing with old test values

Choose **Keep saved TEST values → Experiment Test mode**. PsyCoLab returns directly to Experiment with Test mode selected.

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

