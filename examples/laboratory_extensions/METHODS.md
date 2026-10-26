# Import methods; keep your scientific experiment readable

`experiments/demolab__line_strength.py` is a complete opt-in example using the
installed `LinePatch`, `TeachingAdaptiveMethod`, `ConstantContrastMethod`,
`fixed_level_schedule`, timeline and canonical runner. It vendors no engine.
Its conditions are 1° and 2° eccentricity. Strength is a **digital increment**
above grey 0.5, with line intensity `0.5 + strength`, bounded to [0, 0.5].
This is a short discrimination demonstration, not a luminance threshold study.

Copy this folder to a separate laboratory source location and explicitly enable
that trusted folder in PsyCoLab. Existing folders are never overwritten. Select
`demolab__line_strength`, Test it, then mark the tested revision Ready. Choose
Adaptive for the finite n-down/n-up demonstration, or Constant stimuli for
preselected levels. The default fixed plan has two eccentricities × three levels
× five presentations = 30 responses. Targets are binary left/right, balanced
within each condition/level to within one for odd repetitions. A different
response paradigm needs its own planner. Zero increment is an intentional catch.

Review shows the selected method, one representative stimulus, timings, strength
mapping and planned count. Full schedule, seed, actual strengths and conditions
are saved through existing resolved metadata and the unchanged 20-column TSV.
Fixed runs leave staircase-only values blank and report observed accuracy;
psychometric fitting is a separate scientific decision.

Tested/Ready fingerprints include the imported framework methods, adaptive
engine, renderer and recording path. Updating those scientific dependencies
returns an unchanged local experiment to Draft and requires retesting; it does
not edit the laboratory source or historical runs. Saved run source inventories
and extension fingerprints retain provenance. These APIs are available on this
development baseline; pin its commit pending a separately approved versioned
release. Earlier tags may not export these APIs. Do not copy engines to work
around an older installation: use a compatible pinned framework.

Headless synthetic checks validate this example. Actual display geometry,
photometry and timing require the laboratory's separate physical evidence.
