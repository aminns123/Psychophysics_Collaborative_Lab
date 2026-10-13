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
- Each step is labelled green, amber or red. Green **TEST RECORDED** means a
  physically compatible software diagnostic/ruler measurement exists, *not* that
  the emitted visual stimulus was scientifically verified.
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
| 3. Spatial frequency | Green means a spatial diagnostic was presented for that physical setup, **not** that output frequency was measured | Calibrate → Spatial sine → independently verify orientation, cycles and geometry |
| 4. Luminance | Red if no trusted encoded luminance/command table; geometry cannot fix it | Measure with a photometer, enter instrument/date/points in profile editor, review before verifying |
| 5. Timing | Green only if explicitly declared verified; amber for software-only temporal test | Calibrate → temporal test; photodiode evidence required for photon-onset claims |
| 6. Contrast | Amber if starting RGB command passes the *initial* range guard; red if it could clip | Edit Experiment → background/starting intensity/adaptive steps; document scientifically chosen contrast policy |
| 7. Experiment qualification | Red until the selected experiment/profile pairing is explicitly qualified | Finish lab protocol checks first, then add the experiment ID to the profile's qualified-experiments field |

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

### Progress after a test or measurement

The active calibration page and Review now show software completion separately
from verification: awaiting measurement, awaiting review, stale or failed.
Escape/Enter completes a presented diagnostic; it does not certify hardware.
Ruler measurements attach to the latest completed ruler, even after running a
spatial/timing test. Notes or verification-only revisions retain compatible
evidence; changed physical geometry/binding/resolution/refresh rejects it.
See `CALIBRATION_RELIABILITY_AUDIT_2026-10-13.md` for the compatibility policy.
