# Two CSF envelope protocols: Gaussian reference and circular window

## Scientific rationale

These are two **distinct protocols**, not one CSF experiment silently changing
a historical stimulus.

- `contrast_sensitivity` uses the original compact-support
  **Gaussian-windowed** sinusoidal grating. `grating_sigma_deg` controls
  central-to-edge decay, and `grating_cutoff_sigmas` controls the radius
  with a final smooth fade to exact background. This remains unchanged.
- `contrast_sensitivity_windowed` uses
  `circular_windowed_sinusoidal_grating`, a radial **flat interior** of
  exact diameter in visual degrees. An optional raised-cosine taper affects
  **only** its outer annulus; no Gaussian centre-to-edge reduction occurs.

The CSF experiment files are intentionally not duplicated. The windowed
variant imports the reference's condition formation, timed fixation and
grating presentation, left/right response interpretation, original adaptive
staircase update mathematics, threshold estimation, and fixed-level random
schedule. Its separate `prepare_stimuli` selects the new circular grating.

## Windowed grating: researcher-facing inputs

| Field | Meaning | Example |
| --- | --- | --- |
| `aperture_diameter_deg` | Exact diameter of the circular support | 1.0° |
| `edge_mode` | `soft_edge` or `hard_edge` | `soft_edge` |
| `fade_width_deg` | Thickness of the annulus measured radially inward from support boundary | 0.1° |
| `frequencies_cpd` | The **same** scientific spatial-frequency conditions as the Gaussian CSF | `2,4,8` |
| `contrast_method` | Existing adaptive or constant-stimuli selection | `adaptive` |

With a **1.0° diameter** and a **0.1° radial fade**, the modulation
envelope is exactly 1 for radii <= 0.4°, falls smoothly only for radii
0.4° < r < 0.5°, and equals 0 at r >= 0.5°. Thus the flat central disk
has diameter 0.8°, *not* a 0.8°-radius central region.

For `hard_edge`, or for `soft_edge` with `fade_width_deg=0`, the
modulation envelope is 1 inside r < diameter/2 and 0 outside.

## Exact scientific equation

For local angular pixel coordinates x,y in **degrees**, let

```
r = hypot(x, y)
R = aperture_diameter_deg / 2
w = fade_width_deg  # only if edge_mode = soft_edge

E(r) = 1                              for r <= R - w
     = 0.5 * (1 + cos(pi*(r-(R-w))/w)) for R-w < r < R
     = 0                              for r >= R
```

For w=0, take E=1 at r<R and E=0 outside.

The rendered digital command is:

```
I(x,y) = background + (digital_peak_to_peak/2) * E(r) * sin(2*pi*f*x)
```

This is **digital peak-to-peak modulation**. It is NOT an optical Michelson
contrast or measured display luminance. At an arbitrary pixel within the
interior, full-envelope modulation means the carrier *amplitude envelope*
is not reduced, not that every pixel equals the maximum digital command.

The renderer rejects a nonzero fade wider than the radius, as well as
contrast values outside the local digital gamut. Fully off-screen required
support is invalid, while partially visible support is clipped only at
physical display pixel boundaries, without rescaling stimulus coordinates.
Hard boundaries introduce broadband spatial energy and can create sampling
artifacts; use the lab's geometry/precision and physical qualification
process before acquiring human data.

## Compatibility and data

The historic `contrast_sensitivity` experiment ID, stored runs,
adaptive responses, Gaussian parameters, stimulus identity and threshold
rules remain unchanged. The new experiment uses a unique ID and directory
label `contrast_sensitivity_windowed`.

**Both** use the existing shared `RunContext`, calibration rules, adaptive
or constant-stimuli methods, 20-column `trials.tsv`, and existing local
external data root. Constant-stimuli trials leave staircase-only fields
not-applicable, retaining the schema.

The new experiment's resolved metadata explicitly records the window's
diameter, fade mode, edge width and flat radius. It does not claim a
Gaussian sigma or Gaussian cutoff. Windowed and Gaussian thresholds may be
compared scientifically, but should not be pooled without addressing the
different spatial envelopes.

## Historical evidence and literature

The user's PhD thesis and an accompanying 2026 paper draft describe the
original CSF stimulus as a **Gaussian-windowed sinusoidal grating** with a
1° spatial spread, presented for 300 ms to left/right locations. The
available thesis passages do **not** specify a flat central window
with only a circular outer-edge taper. Earlier original Python source
was not located in the available file context; no exact historic shader
or Gaussian normalization can be verified from these prose accounts alone.

For literature examples:
- Contrast sensitivity can use standard sine-wave gratings, Gaussian
  Gabor patches, or circular grating patches; these are not necessarily
  psychophysically equivalent.
- qCSF/TuebingenCSTest favour Gaussian-smoothed edges, while some
  FrACT/F.A.C.T. variants use abrupt-edged circular patches;
  see `TuebingenCSTest — a useful method to assess the contrast
  sensitivity function` (2017,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5480558/).
- Aperture area and edge energy change sensitivity, so envelope, support
  and fade should be included in saved scientific metadata.

## Verification checklist

- Both experiments registered, choose both methods, and Review reflects
  the correct grating and scientist-chosen diameter/fade.
- Validate 1° diameter/0.1° radial fade: central region undiminished and
  boundary = background (including corners outside the circle).
- Validate 0 fade, fade greater than radius, and digital gamut limits.
- Confirm identical trial timeline and response key mapping.
- Run synthetic fixed and adaptive sessions, verify method/condition labels,
  saved source provenance, canonical columns and unique experiment IDs.
- Native Windows check: partial viewport clipping, Nyquist,
  TUI Review→Try navigation, physical luminance and timing remain separately
  qualified.
