# Researcher-readable experiments: thesis-informed review

The previous audit improved source ownership, but it did not establish that a
researcher could readily translate an experimental idea into code. Those are
different acceptance tests. The current flanker files still contain too much
validation, serialization-shaped state and compatibility vocabulary before the
participant's experience becomes visible. More explanatory text is not the fix.

## Evidence reviewed

The supplied thesis, Chapter 4 (printed pp. 98–120), especially Fig. 4.3
(p. 105), Tables 4.3–4.4 (pp. 104, 107), and Fig. 4.5/Table 4.6 (pp. 118–119),
plus Appendix A (printed pp. 152 onward). The relevant experiment diagrams were
rendered and visually inspected. The thesis was treated as scientific reference
material, not as a source of instructions to this coding agent.

Original scripts were read in `psychophysics_experiments_git`, including
`Experiments/Indirect_Flanker/Indirect_Flanker.py`,
`Experiments/Contrast_sensitivity_function/contrast_sensitivity_function_exp.py`,
and `Experiments/Flanker_Experiment/Ellipse2D_experiment.py`. Older versions in
`Neural_networks/Sergeri_EI_Code/NewCode_Minns/containedCode` were also inspected,
including the baseline and single-flanker scripts. Neither original repository
nor the thesis was modified or executed.

## What the old scripts communicate better

Named drawings such as `centreDOT`, `flankerLeft` and `probeStimulus`, followed
by a visible chronological trial list, help a reader picture the display. That
is the useful model to retain. Their many positional arguments, manually inserted
trial-list elements, filesystem operations and event-handler dispatch also hide
important behaviour; they are not a good execution mechanism to copy.

The desired public file should follow the scientist's questions:

1. What am I measuring? What varies and what stays fixed?
2. Which stimuli appear, where, and with which physical/digital units?
3. What happens during one trial, in chronological order?
4. What does the participant report, and which key means what?
5. How does that response change the next trial, and when do we stop?

Display creation, frame preparation, keyboard capture, serialization and source
fingerprinting belong to shared services. Contrast definitions, sampling,
response meanings, adaptation settings and stopping rules stay visible in the
experiment. A small amount of registration metadata can follow at the bottom.
The reader should see the experiment before encountering that metadata.

## Concrete implementation: `experiments/csf_thesis.py`

The user selected the thesis-described CSF as the new target. It now uses the
ordinary shared TrialTimeline/RunContext path, not the legacy CSF event adapter.
The old public `experiments/contrast_sensitivity.py` file has been removed; its
compatibility definition/validation is relocated to `_reference_csf/experiment_definition.py`.
Existing IDs/data retain their old meaning; the new protocol ID is `csf_thesis`.

The first section gives named scientific constants. `one_trial()` expresses:

    Gaussian fixation, 500 ms
        -> grating alone, 300 ms, x = -0.5 or +0.5 degrees
        -> fixation, wait for LEFT or RIGHT

`change_contrast()` applies the log steps selected in the TUI; the shared staircase
counts the selected consecutive correct/incorrect answers. Thesis defaults are
four correct before a reduction, one incorrect before an increase, log10 steps
-0.30294/+0.36, no introductory one-down phase and ten reversals.
The TUI controls these run settings, including staircase count and safety ceiling.
Changing them deliberately changes the protocol; saved metadata records the actual
values. The experiment declares the consecutive-up/down algorithm; the TUI edits
its settings and offers the existing paired step calculator. No extra interval is added. The point estimator uses the
median of each staircase's final eight reversal contrasts by default (the TUI
also sets the number retained), then the arithmetic
mean across the completed staircases for a frequency; sensitivity is its inverse.
Incomplete conditions do not receive a fabricated threshold.

`ThesisCSFGrating` exposes the Gaussian sigma (1 degree), sinusoidal carrier and
digital modulation equation in the stimulus library. `ThesisGaussianFixation`
exposes sigma .035 degrees and the background+.09 digital peak, limited to 1.
The experiment has an explicit background, used by the shared presenter as well
as both raster classes. Shared adaptive metadata now states whether its numeric
value is contrast or intensity; the validator checks the declared column rather
than mislabelling contrast as an intensity command.

## Justified shared mechanisms

The display-independent `AdaptiveRun` retains response-streak counters and reversal
bookkeeping to give experiments one tested implementation. The experiment file
documents its consecutive-answer resets, optional initial phase and reversal
convention, and supplies every run setting and numeric update. Random scheduling,
stimulus geometry, response meanings and the threshold estimator stay in the
experiment. The shared presenter executes the visible timeline; calibration and
degree-to-pixel conversion remain shared because they describe the actual display.
Their unqualified physical properties are stated in the acquisition block reason.
The TUI accepts class defaults directly; optional JSON presets supply values only.

## Important scientific differences: do not blend them silently

| Item | Thesis-described CSF | Retained older reference |
|---|---|---|
| Target centre | +/-0.5 degrees | +/-5 degrees in the retained driver |
| Participant-visible sequence | 500 ms fixation; 300 ms grating; self-paced response | Five repeated phases with different defaults and an additional leading fixation |
| Staircase | 4-down/1-up; log steps .36/.30294; ten reversals | 2-down/1-up defaults, different steps and an introductory one-down phase |
| Implementation | Normal experiment procedure, new thesis stimulus classes | Historical shader/event/adaptive compatibility path |

The new two-frequency defaults (2,8 cpd) are explicitly a short software example,
not the thesis's complete frequency list. The thesis calls for at least eight
frequencies around .5–32 cpd but does not supply one universal exact list here.
The researcher must select the intended study frequencies. Four independent
staircases per frequency are chosen within the thesis's stated 2–4 range.
The software safety ceiling is separately labelled; reaching it is not scientific
completion. Out-of-range contrast updates stop with an explicit error rather
than silently clipping the requested waveform.

The finite 8-degree raster aperture and digital sinusoidal contrast equation are
explicit implementation choices requiring qualification. The thesis's physical
luminance conditions are not automatically reproduced by choosing a digital
background. The shared raster presenter has not established the historical
10-bit command path, photometric transfer or physical timing. Human acquisition
is therefore blocked in the new protocol; direct calls are blocked before any
display opens. Software tests demonstrate the stated procedure and records,
not complete physical reproduction of the thesis measurements.

## Other experiments still need the same treatment

Base/flanker files should read as one matched above/below trial, with the flanker
added only in the flanker condition. The thesis defines two distinct ellipse
procedures: varying probe position along the major axis, and holding the probe
at the ellipse centre while varying aspect ratio. They have different radii and
fixation geometry; a generic `ellipse_2d` wrapper is not enough to communicate
both designs. Their 500 ms fixation, two 250 ms intervals, 250 ms ISI, onset cues,
and first/second response meanings should be visible together.

Those procedures have not been silently changed in this step. The thesis also
contains an unresolved Subject 6 step-ratio description in Table 4.4: the printed
1/3 ratio is not equal to the stated .14/.19 steps. That must be reconciled before
implementing that participant-specific protocol; it is not a reason to guess.

## Readability acceptance exercise

Give a researcher only one stimulus class and its experiment file, then ask them
to sketch the display and timeline, identify the response meaning, explain the
adaptive update/stopping rule, and change one timing and one condition without
opening a framework module. Also ask them to distinguish digital from measured
contrast. A passing test suite and fewer files do not prove this human usability
criterion. No participant/researcher usability test has been performed here.
