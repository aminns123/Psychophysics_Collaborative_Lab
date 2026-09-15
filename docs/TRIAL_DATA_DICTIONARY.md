# PsyCoLab canonical trial data dictionary

**Canonical trial schema version:** `1`

Every newly created PsyCoLab run contains:

```text
trials.tsv
trials_readable.txt
trial_data_dictionary.tsv
```

`trials.tsv` is the canonical append-only accepted-response record.
`trials_readable.txt` is a derived fixed-width view of the same rows for human
inspection. Each column is padded independently to the width of its longest
header/value, so values line up underneath their titles. The readable file is
regenerated at run finalisation and can always be recreated from `trials.tsv`.
`trial_data_dictionary.tsv` is the self-contained definition of every column,
including experiment-specific encodings. This means a copied run remains
understandable without needing to inspect PsyCoLab's Python source.

The dictionary itself has one row per `trials.tsv` column and records:

- schema version;
- experiment ID;
- column order;
- column name;
- logical type;
- units or encoding;
- meaning;
- notes.

## Canonical `trials.tsv` columns

| Column | Core meaning |
|---|---|
| `trial_index` | 1-based accepted-response number across the whole run. |
| `recorded_utc` | UTC timestamp when the canonical row was written. |
| `event_time_s` | Runtime event time supplied by the experiment engine. |
| `staircase_id` | Active adaptive-staircase identifier. |
| `staircase_trial_index` | Accepted-response count within that staircase. |
| `stimulus_condition` | Experiment-defined stimulus condition. |
| `stimulus_position_px` | Experiment-defined pixel position. |
| `target_alternative` | Correct/target response alternative. |
| `participant_response` | Participant's encoded response. |
| `response_key` | Actual accepted key/input label. |
| `correct` | `1` if response matched target, otherwise `0`. |
| `presented_display_contrast` | Normalised display contrast actually shown for this response. |
| `presented_screen_intensity` | Digital screen intensity actually shown for this response. |
| `step` | Adaptive decision: `hold`, `down`, or `up`. |
| `reversal` | `1` if this response created a staircase reversal. |
| `reversal_count` | Cumulative reversals for this staircase after the response. |
| `next_display_contrast` | Post-response contrast calculated for the next use of this staircase. |
| `next_screen_intensity` | Post-response digital intensity calculated for the next use of this staircase. |
| `staircase_complete` | `1` if the staircase met its configured completion criterion. |
| `run_status` | Adaptive/run status immediately after this accepted response. |

## The most important distinction: `presented_*` versus `next_*`

For scientific reconstruction:

```text
presented_*
```

is what the participant **actually saw** on the response being recorded.

```text
next_*
```

is what the adaptive rule calculated **after** that response for a later
presentation of the same staircase.

Never use `next_*` as though it were the stimulus on the current row.

## Display contrast

The canonical display-contrast columns use PsyCoLab's normalised display
contrast:

\[
C_{\mathrm{disp}} = \frac{I_n-I_b}{I_M-I_b}
\]

where `I_n` is the probe/digital intensity, `I_b` the background command and
`I_M` the maximum command.

This is **not conventional Weber contrast**. Historical code/file names may
still contain the word `weber` for backwards compatibility.

## Current CSF-specific encodings

The per-run `trial_data_dictionary.tsv` records these automatically for the
current `contrast_sensitivity` reference experiment:

- `target_alternative`: `0 = left`, `1 = right`;
- `participant_response`: `0 = left`, `1 = right`;
- `response_key`: `LEFT` or `RIGHT`;
- `stimulus_position_px`: horizontal x-position of the selected 2AFC target;
- `stimulus_condition`: retained legacy CSF condition value.

### Important current limitation for `stimulus_condition`

The current reference CSF uses legacy condition values derived from the retained
`31.5` spatial scaling (currently `63` and `252`). PsyCoLab deliberately does
**not** label these values as cycles/degree yet. Their physical interpretation
remains part of the deferred stimulus/spatial-calibration review.

`resolved_experiment.json` should be used alongside `trials.tsv` for the
resolved screen geometry, alternative positions and other concrete runtime
settings.

## Legacy response file

`legacy_response.txt` is retained for compatibility with historical analysis.
It is **not** the preferred record for new analysis.

Its historical six logical columns are:

1. stimulus condition;
2. target/probe alternative;
3. participant/human alternative;
4. staircase identity;
5. post-update legacy contrast value;
6. post-update screen intensity.

Unlike canonical `trials.tsv`, the final two legacy quantities are the
**post-response / next-state values**, not necessarily what the participant saw
on the current response. New analysis should therefore prefer `trials.tsv`.

## Future experiments

The core trial dictionary supplies general definitions. Each `ExperimentSpec`
can override the meanings/encodings that are experiment-specific.

This keeps documentation close to the experiment while ensuring every acquired
run receives its own exact dictionary automatically.
