# Frozen Stage C baseline

`stage_c_baseline_20261027.json` was captured before production migration from
merged Stage B commit `359bf663b233178b25a338ab09332357bb57bd78` on Windows
Python 3.11.15. Do not regenerate it from the migrated implementation.

The fixture contains all ten official registrations, complete ConfigField
declarations, response meanings, calibration/capability requirements, scientific
summary dictionaries and AST hashes of every original top-level function.
It also contains 46 complete seeded runs: both methods for every experiment at
seeds 0 and 19, plus original mode for orientation_task, probe_above_below and
example_experiment at both seeds. Each case freezes its full selected values,
completion status, accepted count and output hashes.

Capture used `simulations.run.simulate(..., analyse=False,
observer=TeachingObserver(accuracy=.65))` with previews disabled and disposable
configuration/data directories outside the repository. Adaptive settings use
n_down/n_up=1, initial_one_down_limit=2, reversal_termination=4,
threshold_reversals=2, one staircase per condition and max_trials=512 where those
fields apply. Teaching trial_count=10; fixed_contrasts='0,.01' with two repetitions.
Exact other values are recorded in each case, including nontrivial conditions.

Hashes use SHA-256 of UTF-8 canonical JSON (`sort_keys=True`,
`separators=(',', ':')`, `allow_nan=False`). The TSV is read as a complete list of
DictReader rows. Complete trial_actions, trial_presentations, adaptive_history,
adaptive_session, primary_thresholds and resolved_experiment JSON are hashed
when present. The only scientific JSON projection removes dictionary entries
named `ready_fixation`, which hold session-only slot provenance, not trial state.
Source/manifest hashes, host timestamps and the session sidecar are separately
validated rather than claimed to be byte-equivalent across source revisions.

`test_stage_c_event_first.py` compares every case with the opening off and on,
checks unchanged scientific function ASTs, and supplements simulation with the
actual software presentation path. The frozen Stage A and Stage B JSON fixtures
are unchanged. `legacy_stage_b_extension.py.txt` is the unmodified bundled
left/right starter from the same baseline, retained to test old authoring APIs,
software Ready and its original empty session opening.
