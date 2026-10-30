# Native trial summaries and the durable boundary

A two-response Major Axis presentation test on integrated revision `017a06f`
exposed a saved-run validator failure: `trial_actions differs from durable
journal`. Canonical responses and adaptive updates were intact. At the next
trial's first flip, the existing presenter adds `next_flip_s` and
`actual_display_duration_s` to the previous response screen's live event. The
in-memory final summaries retained that same mutable event, although its durable
trial journal had already been committed. One file therefore acquired later
diagnostic observations that the authoritative durable record did not contain.

RunContext now takes detached copies for both final-summary collections at the
existing trial boundary. The journal, canonical answers, scientific updates,
renderer, frame scheduler, response mapping and on-disk schemas are unchanged.
There is no extra timed I/O and no weakening of validation. Partial/error trials
retain the same persistence boundary. In-trial software dwell observations remain
present in both files. Session-opening dwell retains its existing separately
flushed final provenance.

An intentional diagnostic limit is explicit: a response screen's eventual dwell
until the **next trial's** first flip is unknown when that response trial is
committed. It is not retroactively added to a finished summary. Software response
onset, accepted key, reaction time and phase offset remain recorded. These are
software observations, not measured photon/input timing. No past records are
rewritten; historical mismatches remain visible to the strict validator.

Regression tests execute the real Presentation phase player against the existing
injected clock/window, including consecutive accepted responses and an aborted
next trial. They fail on `017a06f` and require exact journal/summary equality after
the correction. The shared-source guard pins the complete corrected file and
checks that undoing only the three exact copy changes restores its historical
source hash. Frozen scientific fixtures remain unchanged.

A native response exercise and public run validation on the corrected revision
are still required before claiming completed native acceptance. This correction
does not establish physical qualification or repair old data in place.
