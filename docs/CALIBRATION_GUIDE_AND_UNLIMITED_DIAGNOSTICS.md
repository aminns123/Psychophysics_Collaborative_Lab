# Actionable human-acquisition calibration guide

## Why a completed ruler test can still block acquisition

The current CSF Review evaluates separate properties of a monitor and
experiment. A 5-degree bar near 44 mm at 0.5 m supports the intended length
geometry; it **does not** validate cd/m², the monitor transfer function,
photon timing, a particular grating stimulus, or the selected experiment's
laboratory qualification. These are deliberately distinct checks.

If **Run human experiment** is blocked, the large Review warning states
the exact reasons. Choose the **blue Resolve blockers / Calibration guide**
button directly above it. A small persistent lower-right panel appears:

- Close with **× Close** or **Esc**; it does **not** disappear after a timer.
- Choose **← Previous / Next →** or press the **left/right arrow keys** to
  inspect independent calibration sections.
- Each step is labelled green, amber or red. **Software presentation** and
  **researcher assessment** are different records. A green Spatial page requires
  a saved visually consistent researcher observation with no reported abnormality;
  this is not independent physical verification of the optical stimulus.
- **Open section** routes to the exact selected local profile's editor,
  the Calibrate test controls, or the experiment's editable protocol settings.
  Editing calibration from Review preserves the experiment draft but requires
  another Review of the current profile revision before human acquisition.
- The guide cannot bypass a safety guard or set qualification automatically.

## Step-by-step workflow

| Guide step | What a status means | User action |
|---|---|---|
| 1. Bind monitor | Green means bound and expected resolution present | Edit monitor → Detect, select, verify physical size/viewing distance, Save |
| 2. Ruler geometry | Green means physical measurement is recorded on a **matching physical setup and profile identity** | Calibrate → Size test → measure physical bar → Record Measurement; inspect signed error |
| 3. Spatial frequency | Green means a *researcher-observed* visually consistent result was saved for the latest compatible spatial presentation; physical frequency is **not** instrument-certified | Calibrate → Spatial → launch grating → return to the same page → select report → describe observed cycles/abnormalities → Record observation; Next stage deliberately |
| 4. Luminance | Green once at least two valid REAL intensity/cd/m² pairs are SAVED; physical verification shown separately | Import and SAVE directly from Calibrate → Luminance, or use the advanced editor; optional method/date/notes warn but do not block |
| 5. Timing | Green when software timing evidence is SAVED, not when photon-onset was verified | Calibrate → temporal diagnostic → Review; separate photodiode evidence is required for physical timing claims |
| 6. Contrast | Amber if starting RGB command passes the *initial* range guard; red if it could clip | Edit Experiment → background/starting intensity/adaptive steps; document scientifically chosen contrast policy |
| 7. Experiment qualification | Red until the selected experiment/profile pairing is explicitly qualified | Finish required lab checks, then use **Calibrate → Review → Check / qualify experiment** or the Experiment Readiness action; choose the registered experiment by name and deliberately record qualification |

**Important:** qualification is never inferred from geometry, software test
completion or a saved profile. If the photometer/photodiode checks are not
available, keep their states unverified and treat the study as a restricted
pilot or synthetic test rather than production-grade psychophysics.

### Reading the reported example

A background digital command of 0.25 and a normalized display contrast of
1.0 would produce a conservative shader RGB range from -0.25 to 0.75 under
`RGB = background + envelope*C_disp*sin(phase)/2`. Digital RGB must be
within 0–1. The maximum allowable initial value for that *specific*
rendering command is `C_disp <= 2*min(0.25,0.75) = 0.5`, but an adaptive
upward step can later exceed it. **Do not merely change numeric values until
the error vanishes**: review contrast semantics, measured luminance and
planned adaptive termination with the experiment owner.

## Fullscreen diagnostic duration

The Calibrate duration now defaults to `0` seconds, meaning **no automatic
timeout**. The diagnostic stays visible until the researcher presses
**Esc** or **Enter**. The explicit timeout feature still accepts any positive
finite duration (including >60 seconds) for scripted acceptance; negative and
nonfinite durations are invalid. Fullscreen frame rates and timing reports are
software diagnostics, not photodiode measurements.

The diagnostic loop continues to service window events while waiting for user
input. If the physical display becomes unavailable or the user must abandon
a window, ordinary OS-level process termination remains available, but may
interrupt the diagnostic and record an error instead of a successful test.

## Validation and limits

Regression tests cover duration 0, large positive durations, rejection of
negative duration, readiness status wording and Textual button/key navigation,
including click-through to the original profile. Physical on-monitor visual
checks remain necessary on Windows with the actual hardware and video driver.

### Fullscreen return and Spatial observation

When a fullscreen calibration test finishes (or fails recoverably), the
application restarts the TUI and restores **Calibrate**, the selected monitor
and the subsection that launched it. It does **not** automatically jump to
Experiment or the next calibration page. When the user deliberately entered
Calibrate from Experiment Review, the explicit Return action remains available.

In Spatial, a completed fullscreen grating creates a **software report**,
not an automatic green stage. The researcher must select the presentation
report and record an assessment and rendering-abnormality response; only
*visually consistent* with *no obvious abnormality* completes the subjective
spatial stage. For a 5° extent at 1 cpd, nominally five complete periods
are expected; counting individual bright maxima is phase/edge-dependent.
Discrepant or uncertain responses stay saved and visible without automatic
acceptance. See `SPATIAL_FREQUENCY_CALIBRATION.md`.

**Current mapping selector:** On the CSF experiment configuration page,
**Background from this display's saved measurements** lists saved means in
cd/m² paired with digital commands for that selected display. Choosing a
row sets both fields. Selecting another display can require explicit
reconfirmation; old values are not silently replaced. Manual mode is
available but not automatically certified. Synthetic pairs can be used for
testing but not certified human acquisition.

### Progress after a test or measurement

The active calibration page and Review now show software completion separately
from verification: awaiting measurement, awaiting review, stale or failed.
Escape/Enter completes a presented diagnostic; it does not certify hardware.
Ruler measurements attach to the latest completed ruler, even after running a
spatial/timing test. Notes or verification-only revisions retain compatible
evidence; changed physical geometry/binding/resolution/refresh rejects it.
See `CALIBRATION_RELIABILITY_AUDIT_2026-10-13.md` for the compatibility policy.
