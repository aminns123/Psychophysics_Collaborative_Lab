# Non-identifying compatibility fixtures

These files are **synthetic representations of older file shapes**, not real
acquisition records or measured calibration observations.

- `older_shape_monitor_profile.json` omits modern optional monitor fields,
  profile revision and current verification metadata. It contains **no** readings.
- `older_shape_workspace.json` represents a saved request missing modern
  `show_response_instructions`; its obsolete data-root and override values must
  not be blindly reactivated.
- `unversioned_trial_table.tsv` imitates a historical file with named columns
  but no manifest. It is not a fully validated PsyCoLab trial-schema-1 run.

These fixtures prove only the explicit read paths exercised by the tests. Real
laboratory archives are **not** checked into Git and require owner-provided,
non-identifying examples before wider historical support can be asserted.
Do not pass these artificial files off as physical acquisition evidence.
