# Display contrast: proposed bright-stimulus scientific convention

**Status: draft contract only. Not yet the selected acquisition convention in all official experiments.** Do not use this document to reinterpret existing runs, thresholds or stimulus presets. Related: #198, #197.

## Researcher's definition

For brighter-than-background pixels under a normalized digital command scale:

```text
C_disp = (I_stim - I_background) / (1 - I_background)
I_stim = I_background + C_disp * (1 - I_background)
```

Example: at background `0.25`, a chosen display contrast `0.5` produces a requested pixel command of `0.625`.

The contrast is **relative to available digital headroom above background**, not a raw additive increment, absolute pixel intensity, optical Weber contrast or calibrated Michelson contrast. At full-white background, there is no upper headroom and this positive-contrast convention is undefined. For dark decrements or two-sided grating modulation, a separate explicitly declared convention is necessary.

## Important difference from current main/develop code

Existing `DetectionScene` bright probe and ellipse-ring acquisition uses **raw digital increments above background**, and stores those values in the established scientific outputs. Do **not** simply relabel those legacy values as this new display contrast; e.g. at background `0.25`, an old increment `0.5` is display contrast `0.5 / 0.75 = 0.66666...`, not `0.5`.

The existing CSF family uses **digital peak-to-peak sinusoidal grating modulation** with a background and envelope. It is not identical to headroom-normalized bright-only contrast. Orientation/learning stimuli may likewise use other declared modulation conventions.

## Researcher-facing goal

For applicable bright probes and ellipses, Review should present *Background intensity*, *Starting probe display contrast* / *Fixed probe display contrasts*, and *Ellipse display contrast*, plus the effective digital pixel command and condition-specific headroom/overlap constraints. Separate controls for ellipse outer radius and inner axial inset require their own scientific design approval.

## Compatibility and implementation gates (not implemented by this draft)

1. Inventory each official and bundled lab experiment's actual strength quantity (digital difference, grating peak-to-peak, orientation modulation, or no contrast).
2. Define an explicit per-experiment selected contrast convention and preserve the legacy meaning of existing experiment JSON, stimulus presets, manifests, thresholds and 20-column trial records.
3. Convert selected new contrasts to existing renderer commands **at the acquisition boundary**, with zero clamping, while keeping all adaptive/fixed mathematics and randomization scientifically valid.
4. Verify round trips with nonzero background, both contrast methods, ring/probe overlap limits and intended display gamut. Retain original frozen scientific tests; add independent new-convention fixtures rather than changing expected historical digests.
5. Qualify native TUI Review editing and the researcher path on Windows. No optical-luminance claims without measured photometry and stimulus timing.

The pure conversion functions in `methods/display_contrast.py` implement only the mathematical contract. They are intentionally not wired to participant acquisition in this draft PR. This is a deliberately small, non-breaking preliminary PR to `develop`, not an authorised scientific unit migration.
