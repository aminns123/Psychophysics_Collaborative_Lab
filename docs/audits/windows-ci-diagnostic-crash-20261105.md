# Windows CI diagnostic crash — 5 November 2026

Release PR #220 (`develop` 10b174b → `main` 340889c) displayed two failures:

- [Windows group 2](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/42060180205/job/127359331024)
  stopped during `test_completed_official_method_matrix[ellipse_major_axis-adaptive-1729]`.
  At exactly 30 seconds, the log begins `Timeout (0:00:30)!`, then reports
  `Windows fatal exception: access violation` inside the stack dump, with
  Matplotlib marker frames. There is no pytest assertion failure or final summary.
- The required `test (windows-latest)` gate correctly failed because that group
  did not complete. Scientific smoke and the other three groups passed.

PR #219 previously stopped during the same timeout-dump mechanism at a different
test, then passed in full on the identical commit after retry. This repeat pattern
is evidence for a diagnostic-path failure, not evidence that any experiment is
scientifically correct or that every possible native crash has the same cause.

The optional pytest `faulthandler_timeout=30` requests a background all-thread
stack dump; it does **not** impose an execution deadline. Python documents its
[watchdog thread](https://docs.python.org/3.11/library/faulthandler.html#dumping-the-tracebacks-after-a-timeout),
and pytest tracks [Windows access violations while dumping threads](https://github.com/pytest-dev/pytest/issues/7022).
The installed pytest 8.4.2 implementation calls `dump_traceback_later` when this
setting is positive. The observed CI logs are consistent with that reported
class of failure; an exact upstream root cause has not been proven here.

## Narrow mitigation

The Windows shard runner explicitly sets this optional timeout dump to zero.
`-X faulthandler` and pytest's fatal-fault handler remain enabled, along with
verbose test names, normal assertion/exception reports and warning logs. Genuine
crashes and nonzero pytest exits still fail the shard. A 45-minute Actions job
deadline bounds actual hangs externally; previous successful groups took about
13–19 minutes. The required gate is unchanged.

The partition, scientific tests, fixtures, assertions, dependencies, experiment
source, stimuli, adaptation, data formats and local research records are unchanged.
No automatic retry, test exclusion or success-on-error behaviour is introduced.

Regression checks launch real pytest child processes: passing and deliberately
failing assertions must retain fatal capture, disable only timed dumps, and return
their actual exit status. Another check verifies every test module belongs to
exactly one group. Complete Windows results are recorded in the repair PR.

PR #220 remains a separate, unmerged release PR. This mitigation is submitted
to `develop` for review; it does not directly change either protected branch.
