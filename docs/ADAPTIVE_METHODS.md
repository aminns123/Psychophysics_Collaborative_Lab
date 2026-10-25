# Adaptive procedures and step-size calculator

The response paradigm, the adaptive algorithm, and the experiment are distinct.

- **Response paradigm:** e.g. a left/right spatial 2AFC target-location task,
  a single-interval binary above/below judgment, or first/second **2IFC**
  (two-interval forced choice). Each task defines its actual interval count,
  alternatives and response keys, not just an acronym. See
  [psychophysical terminology](PSYCHOPHYSICS_METHODS_AND_TERMINOLOGY.md).
- **Adaptive algorithm:** how accepted observations change future conditions.
  The working legacy `consecutive_up_down` algorithm is registered under
  `src/psychophysics_lab/adaptive/`. Its `AdaptiveRun` supports independent
  staircases, response streaks, reversals and a trial ceiling.
- **Experiment:** explicitly declares which algorithm and which configuration
  controls it permits. The routine TUI does not choose the algorithm.

An algorithm may define a different future contract (e.g. posterior updating
for QUEST/Psi); registering a new name does not automatically make it compatible
with the legacy CSF acquisition adapter. Existing
`Events.staircase` imports remain supported by a compatibility shim.

## Optional fixed-log-step calculator

The reference CSF experiment takes `n_down` consecutive correct responses to
move **down** and `n_up` consecutive incorrect responses to move **up**.
These are **response counts**, distinct from step magnitudes.

The default probe-contrast update uses a log10-sized multiplicative step:

```text
UP:   C_next = C_now * 10**logUNIT_UP
DOWN: C_next = C_now * 10**(-logUNIT_DW)
HOLD: C_next = C_now
```

The opt-in TUI buttons implement published García-Pérez (1998) **down/up
step-size magnitude ratios**, only when the experiment explicitly declares the
supported 2AFC fixed-log-contrast convention:

| Rule | down / up step magnitude |
| --- | ---: |
| 1-down / 1-up | 0.2845 |
| 2-down / 1-up | 0.5488 |
| 3-down / 1-up | 0.7393 |
| 4-down / 1-up | 0.8415 |

Reference: García-Pérez, M. A. (1998). *Forced-choice staircases with fixed
step sizes: asymptotic and small-sample properties*. Vision Research 38,
1861–1881. DOI: [10.1016/S0042-6989(97)00340-4](https://doi.org/10.1016/S0042-6989(97)00340-4).

These are conditional literature settings, **not universally optimal ratios**.
A rule alone does not uniquely establish a statistically optimal target.
Changing response counts does not automatically change any step magnitude.
Unsupported settings (for example 2-up or 4AFC) must be entered manually or
implemented with separately validated theory.

The **current public CSF experiment's** code defaults are
`logUNIT_UP = 0.36` and `logUNIT_DW = 0.30294` (see
`src/psychophysics_lab/experiments/contrast_sensitivity.py`). Its default
response counts are `n_down = 4` and `n_up = 1`; `0.30294 / 0.36 = 0.8415`,
the listed **4-down/1-up** ratio. These are editable protocol defaults, not
measured optimal values; calculator use is explicit and optional.
Historical scripts and archived runs may have different defaults and must
be interpreted using their own saved configuration.

Never silently change stored thresholds, reversal basis or response encoding
when introducing additional algorithms. Prefer unit-tested, registered
algorithms with documented stopping criteria and empirical convergence checks.


## Modern detection protocols: explicit bounded strength

The modern CSF, line baseline/flanker and ellipse protocols default to four-down,
one-up, with log10 steps up .36 and down .30294, matching thesis Table 4.4.
These are multipliers of about 2.291 and .498 respectively. The down/up log-step
ratio is .8415, corresponding to nominal 85.84% performance under the cited
fixed-step model. These are historical study choices, not a universal optimum;
step size relative to the observer's psychometric slope, lapses and boundaries
still affects finite-run bias and precision. The TUI retains the researcher's
chosen counts and step sizes, including manual alternatives.

Here C means the experiment's declared strength: a digital increment above
background for the line/ellipse tasks, and peak-to-peak modulation for modern
CSF. It does not mean total pixel intensity or calibrated optical contrast.

An adaptive overshoot now saturates at the declared bound and continues; flat
holds do not count as reversals. The upper-bound equation is local to each
experiment. The shared bounded_log_step function only performs numerical stepping
and protects against floating-point overflow/underflow. Its tiny positive floor
lets a log staircase increase again rather than becoming stuck at exact zero.
Canonical presented/next strengths, requested step events and saved bounds allow
analysis to flag boundary-affected staircases. Historical replay is unchanged.


## Reversal reference for new and historical procedures

Modern CSF, line/ellipse and orientation-adaptive procedures supply
`starting_values` to `AdaptiveRun`: the initial displayed strength establishes
the reference, its first movement establishes direction, and the first change
of nonzero direction is a reversal. Holds at a bound are not reversals. The
saved snapshot records `reversal_convention: starting_presentation` and corrected
protocol versions distinguish newly acquired data. This can change stopping and
which early reversal enters a threshold; old records are not recalculated.

Historical replay omits `starting_values` and retains first-recorded-update
seeding. Custom procedures can deliberately choose either convention. Consecutive
response counts, selected step sizes and initial one-down rules are unchanged.
