# Derived staircase threshold analysis

Threshold summaries are **post-hoc derived analysis**. They do not modify
`trials.tsv`, `adaptive_session.json`, staircase rules, termination criteria or
any other acquisition record.

Outputs are written outside run folders:

```text
<external data workspace>/analysis/thresholds/
    <participant>/<experiment>/<run_uuid>/<timestamp>/
        staircase_thresholds.tsv
        threshold_by_condition.tsv
        threshold_analysis.json
        threshold_vs_condition.png
```

## Default convention

The current default is:

1. select accepted-response rows marked as reversals;
2. within each staircase, retain the final 80% of reversal observations;
3. use `ceil(N * 0.80)` for non-integer retained counts;
4. average those retained values to obtain one threshold per staircase;
5. average staircase thresholds sharing the same condition;
6. plot threshold contrast versus condition.

The default reversal value is `next_display_contrast`, because the current CSF
compatibility layer describes its legacy reversal basis as post-update. The TUI
also exposes `presented_display_contrast` so that alternative analyses are
explicit rather than silently redefining the acquisition.

The 80% fraction is configurable and is not an acquisition rule. Any scientific
decision to change the preferred threshold estimator should be discussed and
versioned independently of the staircase implementation.
