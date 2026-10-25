# Psychophysical paradigms, response alternatives and scientific terminology

This is the **current researcher-facing terminology convention** for PsyCoLab.
Read it with the [experiment authoring guide](../src/psychophysics_lab/experiments/README.md)
and [adaptive methods](ADAPTIVE_METHODS.md). It documents the existing
experiments; it does **not** change experiment identities, trial schemas,
saved `PARADIGM` strings, acquisition algorithms or historical records.

## Describe the trial, not just the number of response keys

For each experiment, distinguish four independent facts:

1. **Presentation:** how many stimulus intervals are shown; whether signals
   appear at simultaneous spatial locations or at different times.
2. **Alternatives:** what the participant must judge (left/right target
   location, above/below position, target in first/second interval, sign of
   orientation, etc.).
3. **Response mapping:** which physical keys report those alternatives.
4. **Measurement and estimator:** what quantity varies, how adaptation changes
   it (if applicable), when the experiment stops, and how the reported result
   is calculated from the **presented** responses/staircase observations.

A task may have two response keys without presenting two comparison stimuli.
Do not infer presentation count from `ResponseParadigm` alone.

## Recommended terminology

| Term | Meaning in this documentation | Example |
| --- | --- | --- |
| **2AFC** — two-alternative forced choice | A frequently used umbrella term for choosing between two experimentally defined alternatives. Literature varies: some authors reserve it for two spatial alternatives or two stimuli; others include temporal alternatives. Always specify the actual design. | Target presented at the left *or* right location, participant reports location |
| **Spatial 2AFC** | Two alternative spatial target locations are relevant on each trial. Specify whether both locations are presented or only one contains the target. | `contrast_sensitivity.py` left/right grating target |
| **2IFC** — two-interval forced choice | Two sequential temporal intervals; the observer reports which interval contained the target (or which met a stated comparison criterion). | `ellipse_centre.py` and `ellipse_major_axis.py`, target in first or second interval |
| **Single-interval, two-response classification/discrimination** | A single target is shown, with two possible category/position judgments. Often called a binary forced-choice judgment; it is not automatically equivalent to the classic two-presentation 2AFC design. | One line above **or** below fixation, or a single tilt judged negative/positive |
| **2AFTC** | **Do not use** as PsyCoLab's name for a temporal task. | Write **2IFC** instead |

**Terminological caution:** published authors do not all use 2AFC and 2IFC
identically. A manuscript should report the number of presentation intervals,
stimuli and alternatives, not just the acronym. Do not infer that two response
keys alone guarantee a canonical 2AFC signal-detection model.

### Existing source implementations

| Experiment files | Presentation and response | Preferred written description |
| --- | --- | --- |
| `contrast_sensitivity.py` | A grating on one of two sides; left/right response | Spatial two-alternative forced-choice target-location task |
| `ellipse_centre.py`, `ellipse_major_axis.py` | Two sequential stimulus intervals; probe in one; first/second response | Two-interval forced-choice (**2IFC**) detection |
| `line_position_baseline.py`, `line_position_flanker.py` | One probe interval; line position above/below; above/below response | Single-interval, binary above/below position discrimination |
| `new_probe_vertical_line_stimulus.py`, `probe_above_below.py` | One probe interval; above/below response | Teaching binary position task, not a temporal 2IFC trial |
| `orientation_task.py`, `orientation_adaptive.py` | One orientation judgment, negative/positive response | Binary orientation-sign discrimination |
| `example_experiment.py` | Simple left/right line-position teaching task | Teaching binary left/right position judgment; inspect `make_trial` before assuming simultaneous comparison stimuli |

The code's existing `PARADIGM = "two_alternative_forced_choice"` label
can cover its binary-response tasks. It **does not by itself establish** that
each task used two stimulus presentations. The ellipse tasks already use
`PARADIGM = "two_interval_forced_choice"`. Do not rename these persisted
identifiers or modify response mappings merely to standardise prose: such
a change requires a separately reviewed schema/protocol migration.

## Statistical and measurement cautions

- **Response count is not interval count.** With two balanced correct
  alternatives, chance accuracy is commonly 50% under random guessing; it
  does not prove lack of response or interval bias.
- **2IFC does not remove bias automatically.** Interval-order biases can
  affect performance; preserve/inspect target-interval assignments and
  responses in saved trial data.
- **An n-down/m-up staircase is not a threshold definition.** Step ratios,
  initial phases, boundaries, reversals, censoring and termination affect
  the result. Do not promise 75% correct or unbiased recovery from a two-choice
  label alone. The declared `primary_estimator` and relevant
  `primary_rule()` define the stored threshold computation for that study.
- **Presented versus next contrast matters.** Analysers must distinguish
  stimulus strength actually presented on a reversal trial from the
  subsequent adaptive state. A threshold from final reversals is not
  interchangeable with a full psychometric-function fit.
- **Digital intensity is not measured luminance.** A grating's
  peak-to-peak digital modulation, a bright probe's increment over
  background, Weber contrast and Michelson contrast are different quantities.
  Calibrated optical contrast requires measured display behavior.
- **Software timing is not physical timing.** Frame plans do not establish
  emitted-photon onset/offset. Likewise, successful `--dev-test` and
  `--dev-ready` are software checks, not participant-protocol qualification.

## How to review a new experiment scientifically

Read `FIELDS`, `RESPONSES`, `PARADIGM`,
`make_conditions()`, `choose_condition()`,
`prepare_stimuli()`, `make_trial()`, `interpret_response()`,
the adaptive update, `is_finished()`, `primary_rule()` where present,
and `SPEC`. Then verify that a representative generated trial and its
recorded target/response fields match that narrative.

For each experiment, a researcher should be able to state:

- What exactly appears in interval one (and interval two if present)?
- What are the two responses and which physical keys mean what?
- Is the target location/interval randomised and balanced as intended?
- What changes after an accepted response; what is held constant?
- Which units are digital commands, degrees, cycles/degree or measured
  photometric quantities?
- What constitutes a completed staircase/study and what makes an
  estimate unavailable?

Do this separately for headless simulations and physically presented human
runs. A simulation can validate software invariants but cannot certify the
screen or the scientific assumptions of an observer model.

## References and nomenclature choices

- García-Pérez and Alcalá-Quintana (2011), *Attention, Perception, &
  Psychophysics* 73:2332–2352, DOI
  [10.3758/s13414-011-0167-x](https://doi.org/10.3758/s13414-011-0167-x):
  explicitly discusses authors who distinguish spatial **2AFC** and
  temporal **2IFC** and others who use **2AFC** for both.
- [Suboptimality in Perceptual Decision Making](https://pmc.ncbi.nlm.nih.gov/articles/PMC6110994/):
  discusses ambiguities in the 2AFC label and spatial/temporal designs.
- [Bias and Sensitivity in Two-Interval Forced Choice Procedures](https://pmc.ncbi.nlm.nih.gov/articles/PMC5839130/):
  clearly defines a two-interval task and cautions that it is not
  automatically free from bias.
- García-Pérez (1998), *Vision Research* 38:1861–1881,
  DOI [10.1016/S0042-6989(97)00340-4](https://doi.org/10.1016/S0042-6989(97)00340-4):
  published context for opt-in fixed-log-step staircase calculations;
  not a universal guarantee of threshold criterion.
