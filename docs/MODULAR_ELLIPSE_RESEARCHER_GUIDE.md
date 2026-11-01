# Modular Ellipse Centre — researcher guide

**Implementation:** `src/psychophysics_lab/experiments/ellipse_modular_centre.py`  
**Stimuli:** `EllipseRing`, `ProbeLine`, `GaussianFixationSpot` in `src/psychophysics_lab/stimulus_library.py`  
**Status:** new software-validation protocol in PR #202; no physical qualification or approved human acquisitions.

## The intended reading order

1. **A1 — What is the experiment?** The top of the Python file declares `STIMULI`, editable `FIELDS`, session opening, `interval_stimuli()` and `trial_events()`.
2. **A2 — How is it decided and measured?** Conditions, stimulus parameters, validity, adaptive staircase rules or fixed-level schedule, stopping, estimator and data meanings.
3. **B — How does PsyCoLab run it?** Only the existing execution adapter and experiment registration. The researcher does not need to change TUI or graphics engine code.

## One list of stimuli

```python
STIMULI = {
    "ellipse": "ellipse_ring",
    "probe": "probe_line",
    "fixation": "gaussian_fixation_spot",
}
```

Keys are experiment-local **slot names**; values are IDs for independently authored stimulus classes. The `experiment(..., stimuli=STIMULI)` API derives the allowed stimulus families and defaults. You no longer need to maintain two independent dictionaries. This new optional API does **not** change established experiments.

### What controls the appearance?

| Object | Researcher inputs | Renderer's scientific shape |
| --- | --- | --- |
| Ellipse ring | Outer horizontal semi-axis, b/a ratio per condition, inner axial inset, orientation, X/Y position, display contrast | Nested rotated ellipses; **inset is along both axes**, not constant normal stroke width |
| Probe line | Width, length, X/Y offset **relative to ellipse centre**, adaptive start or fixed display contrast | Independent vertical, rectangular line, fractionally covered subpixel boundaries |
| Gaussian fixation | Sigma, display contrast, trial X/Y position | Separate Gaussian spot, independent of the ring/probe |
| Shared background | Normalized digital command | Every composited layer must use the same background |
| Timing / response | Once-only start key and settle, fixation, two intervals, gap, optional beep, response mapping | Trial order is declared explicitly, not hidden in a graphics function |
| Methods | Adaptive staircases and thresholds; or fixed contrasts and presentations per condition | Shared PsyCoLab contrast method and canonical recording |

The ring may be hidden via `ring_present` to test a no-ring condition. Geometry is still checked against the real monitor viewport; a large requested ring must be visually and physically qualified.

### How the order works

`interval_stimuli()` declares objects **back to front**. The ring is placed first, the probe only in the target interval, fixation last. In the opt-in compositor, the opacity/coverage mask controls where later objects cover earlier ones. A transparent patch does **not** erase a previous object's pixels merely by enclosing them in its rectangular raster. A subpixel probe uses fractional coverage. This is **occlusion**, not addition of digital increments.

The once-only ready/settle fixation is drawn at the screen centre. The editable trial fixation X/Y controls apply to the repeated trial events. Both are visible in the source.

## Contrast and provenance

For bright digital markings:

```text
display contrast = (mark command - background command) / (1 - background command)
mark command = background command + display contrast*(1 - background command)
```

For background 0.25 and contrast 0.50, the requested full-coverage mark command is 0.625. On a fractional pixel, the command is mixed by the stimulus coverage. **This is not physical luminance Weber contrast**, nor the old Ellipse Centre's additive digital probe increment.

The new experiment ID is `ellipse_modular_centre`. Existing experiment IDs (`ellipse_centre`, `ellipse_major_axis`, line-position studies) and `detection_scene` are unchanged. Old saved records retain their original scientific meanings. New records still use the canonical 20-column TSV and explicitly describe the new digital contrast units in metadata.

## Before calling the experiment ready

- Test original and changed configuration values in Review, then inspect an actual preview of the complete stimulus layers and the two target intervals. An individual-stimulus preview **cannot prove** the final composite appearance.
- Run both adaptive and constant-stimuli synthetic trials and check saved data, conditions, target balance, units, abort behaviour and file provenance.
- On a Windows lab PC check actual monitor binding, calibration, 6° semi-axis/full-diameter visibility, pixel sampling, floating-point rendering, hardware timing/response input and measured luminance. The software's passing tests alone do not establish these properties.
- Keep the new study in software-validation mode until independent physical and researcher acceptance.

Follow-up work: Issue #200 (template/local-to-official authoring), #201 (common modular composition), #198 (scientific Review parameters). Do not migrate existing studies in this initial PR.
