# PsyCoLab calibration — what to measure, what to enter, what remains unverified

This document is for the researcher operating **Calibrate** and the persistent
**Calibration guide** accessed from Review. It documents the fields accepted by
the current repository and what equipment is required. It is not a declaration
that any particular workstation meets scientific acceptance standards.

## Overview

| Calibration stage | Inputs/units | Where to enter | Equipment/evidence | What does NOT follow |
|---|---|---|---|---|
| Bind monitor | OS monitor, pixel width/height, nominal refresh (Hz); physical image width/height (metres), viewing distance (metres) | Calibrate -> Bind/edit profile -> Detect/select; enter dimensions, Save revision | OS framebuffer plus physical tape/ruler measurement | OS mode does not measure physical size, eye position or photon timings |
| Geometric size | requested bar extent (degrees or mm), measured bar length (mm) | Calibrate -> Size / ruler -> Record Measurement | physical ruler at monitor, measured distance | one correct bar doesn't verify all off-centre geometry |
| Spatial frequency | grating frequency (cycles/degree), orientation, angular size, position | Calibrate -> Spatial sine grating | frequency/sampling diagnostics; optical measurement if claiming true spatial response | successful software presentation isn't optical frequency certification |
| Luminance/photometry | digital commands [0,1], meter readings (cd/m²), meter/method/date/notes | Calibrate -> Luminance / grayscale patch; Bind/edit profile -> Create example JSON -> Load JSON from path -> Save | calibrated photometer/spectroradiometer, controlled conditions | grayscale command and OS brightness aren't cd/m²; import is unverified |
| Timing | nominal refresh (Hz), diagnostic temporal frequency (Hz), independently measured photon onset/durations | Calibrate -> binary flicker / frame-sampled sine; profile timing status/provenance | photodiode, oscilloscope/data acquisition as appropriate | frame callbacks do not measure light onset |
| Contrast/adaptive | background command [0,1), starting probe intensity [background,1], steps, staircase policy | Experiment -> Configure -> Display and contrast / Adaptive | reviewed scientific contrast definition and actual display command range | a safe starting value does not constrain later staircase steps |
| Experiment qualification | registered experiment ID(s), e.g. `contrast_sensitivity` | Bind/edit profile -> Explicitly qualified experiments | lab sign-off of relevant checks for exact profile revision and experiment | neither geometry nor importing a JSON file automatically qualifies a monitor |

**Status meanings:** `manual_unverified` means input or readings are saved as
a draft. `verified` means the operator explicitly asserts verification; the
software cannot observe the physical metrology or approve laboratory quality.
No required scientific check should be marked verified just to make the launch
warning disappear.

## 1. Monitor geometry worked example

Suppose the active image is physically **340 mm × 210 mm**, the eye-to-screen
distance is **500 mm**, and the current Windows mode is **1536 × 960 pixels** at
**59 or 60 Hz depending on the detected mode**. Enter:

- `physical_width_m: 0.340`
- `physical_height_m: 0.210`
- `viewing_distance_m: 0.500`
- `expected_resolution_px: [1536, 960]`
- `refresh_rate_hz`: copy the *actual* detected Hz value (do not invent 60).
- Select the connected screen and save a local revision.

For a centred bar specified as **5 degrees**, the ideal length at **0.5 m** is

```
L = 2 * distance * tan(angle / 2)
  = 2 * 0.500 * tan(2.5 degrees)
  ≈ 0.04366 m = 43.66 mm
```

Run the fullscreen bar check, measure with your physical ruler, and enter the
actual reading in the **Measured bar length (mm)** input, e.g. 44 mm **only if
you personally measured that length**. The app records signed error. Repeat in
other axes/positions for a more convincing geometric check.

## 2. Spatial frequency worked example

Select **Spatial sine grating**, then `spatial_cpd: 4`, a horizontal or
vertical orientation, and a 5-degree nominal patch. Four cycles/degree over
five degrees correspond to approximately **20 cycles**, with realized endpoints
and quantization documented in the diagnostic. Inspect for aliasing and ensure
the requested frequency is below both axes' Nyquist limits; inspect the real
production Gaussian-enveloped CSF stimulus separately.

## 3. Luminance: JSON file workflow

### A. Display a known digital gray command

In **Calibrate**, select **Luminance / grayscale measurement patch**. Set:

- `Grayscale digital command` to 0, 0.25, 0.5, 0.75 or 1 (examples, not
  prescribed calibration sampling points).
- `Size units` and `Requested value` determine the central rectangular
  patch dimensions. The surround is black.
- Set duration `0` to leave it visible until Esc/Enter.
- Measure the actual **central patch** with a photometer under controlled
  warm-up, OS brightness, environmental illumination and device settings.

The test records the command and monitor profile revision in its diagnostic
report. It **cannot** record physical cd/m² itself.

### B. Generate a file you can fill in

Go to **Bind / edit monitor profile** and click:

**Create / open example luminance JSON**

A JSON file is created under the machine-local configuration folder, in
`calibration_templates/`. On Windows, the app attempts to open it in your
system's JSON editor. It also fills in the absolute file path so you can
find it yourself.

Initially, the example looks approximately like this (shortened):

```json
{
  "format": "psycolab.luminance.measurements",
  "schema_version": 1,
  "monitor_profile_id": "legacy_reference_display_local",
  "based_on_revision": 2,
  "photometer_model_and_method": "REPLACE_WITH_REAL_METER_AND_MEASUREMENT_METHOD",
  "measurement_date": "YYYY-MM-DD",
  "notes": "REPLACE: controlled monitor/ambient settings, instrument and uncertainty",
  "measurements": [
    {"screen_intensity": 0.0, "luminance_cdm2": null},
    {"screen_intensity": 0.25, "luminance_cdm2": null},
    {"screen_intensity": 0.5, "luminance_cdm2": null},
    {"screen_intensity": 0.75, "luminance_cdm2": null},
    {"screen_intensity": 1.0, "luminance_cdm2": null}
  ]
}
```

**Do not fill the file using estimated or illustrative luminances.** The
`null` placeholders deliberately prevent unmeasured data being imported.
Use your own measured values, in **cd/m²**, for the exact digital commands
actually displayed. Add or remove measurement rows if your instrument/protocol
requires other commands. At least two distinct command/luminance pairs are
required, and luminance must increase with command; this is a minimal
validation rule, not a sufficient scientific calibration protocol.

The file is tied to a **specific monitor ID and source revision**. If you
update geometry/binding in the meantime, create a fresh template and carefully
transfer readings only after verifying their physical validity.

### C. Import, inspect and save the profile

**Recommended direct method:** Calibrate → **4 · Luminance** → paste the
absolute JSON path → **Import + SAVE real readings → Continue to Timing**.
The stage turns green after a successful save, regardless of optional metadata;
it does **not** assert laboratory verification. The advanced profile editor
below remains available if you need to modify the entire display profile.

1. Save the edited JSON file in your preferred editor.
2. Paste or retain its **absolute file path** in **Path to completed luminance
   measurement JSON file**. You do NOT paste the entire outer JSON object
   into the old single-line raw-calibration field.
3. Click **Load measurements into draft (not yet saved)**.
4. PsyCoLab validates file format, ID/revision, numeric real readings, command
   range, unique points and monotonic luminance. Method/date/notes may be omitted:
   their absence creates warnings, not import errors. Unused `null` rows are skipped.
5. Successful loading populates the current draft table and its method/date/
   notes fields. It explicitly selects **manual_unverified** and clears any
   experiment qualification from the draft.
6. Inspect the values, then click **Save local revision**. This stores a new
   profile revision, not a new human-data run.
7. Review the actual photometric evidence independently; only then declare
   verified using the calibrated monitor profile and required laboratory
   protocol. If you revise the measurement table, verification is revoked.

An existing user who already has the **simple list** format can still enter
that list directly into the raw `Current draft measurements` field:

```json
[
  {"screen_intensity": 0.0, "luminance_cdm2": 2.0},
  {"screen_intensity": 0.5, "luminance_cdm2": 101.0}
]
```

**These numbers are invented for a structural example only.** Never treat
them as measurements, or mark a profile verified based on this demonstration.
The file import path is safer because it also carries provenance.

## 4. Timing: example and limitations

If your nominal refresh rate is 60 Hz, `7.5` Hz binary flicker can be
scheduled using a repeating **4 frames ON + 4 frames OFF** command sequence.
This is a software timing example, not proof the display actually emits light
at the requested times. To certify physical onsets/durations, use a photodiode
and record its measurement method, data and uncertainties. `timing_status`
is a manual declaration; the repository does not yet have a dedicated
photodiode JSON import workflow.

## 5. Contrast: what fields mean

The reference production shader's conservative envelope formula is
`RGB = background + envelope*C_disp*sin(phase)/2`. For background command
0.25, a normalized display contrast of 1.0 could request an invalid
`RGB=-0.25`. The starting bound is `C_disp <= 2*min(0.25,0.75)=0.5`.
This does **not** establish a scientifically appropriate starting intensity,
because adaptive upward steps can exceed the bound later, and the physical
luminance response has not yet been measured. Use the **Experiment**
configuration controls; do not silently change the algorithm or clamp
the emitted contrast.

## 6. Qualification: explicit manual lab judgement

The profile's **Explicitly qualified experiments** text field takes
comma-separated experiment IDs, such as `contrast_sensitivity`. Enter them
only after you have reviewed the required experimental and physical
acceptance checks for the specific monitor and profile revision. Neither
successfully creating a template nor recording a software diagnostic
automatically qualifies the monitor.

## Known limitations / requested future improvements

- The new grayscale test generates known *digital commands*; it cannot
  measure luminance itself, nor does it automatically capture a photometer.
- Physical mapping validity depends on video pipeline, software gamma,
  monitor processing, spatial uniformity and ambient conditions. Digital
  command values are not physical luminances.
- A reliable future workflow could provide a photometer acquisition plugin,
  point-by-point guided measurement capture, uncertainty input, full audit
  trail and approved laboratory qualification sign-off.
- Timing currently records software diagnostic timing only; it does not
  automatically import photodiode traces.
- Existing green badges for a *recorded* ruler or spatial diagnostic mean a
  relevant record exists, not that the hardware met an experimental tolerance.

For instrument and Windows pilot acceptance criteria see
`docs/WINDOWS_HARDWARE_ACCEPTANCE.md`.
