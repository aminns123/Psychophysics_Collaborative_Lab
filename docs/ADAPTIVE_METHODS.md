# Adaptive procedures and step-size calculator

The response paradigm, the adaptive algorithm, and the experiment are distinct.

- **Response paradigm:** e.g. left/right spatial 2AFC or first/second interval
  2AFC. Both can encode whether a response was correct.
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

The retained reference CSF defaults remain exactly `logUNIT_UP = 0.35`
and `logUNIT_DW = 0.5488 * 0.35`; calculator use is explicit and optional.

Never silently change stored thresholds, reversal basis or response encoding
when introducing additional algorithms. Prefer unit-tested, registered
algorithms with documented stopping criteria and empirical convergence checks.
