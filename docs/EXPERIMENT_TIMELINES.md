# Trial timelines and scientific actions

Start with [the chronological beginner guide](START_HERE_EXPERIMENTS.md).
TrialTimeline and RunContext.play_trial are the authoritative public sequence;
Phase and load_timeline keep earlier visual-only JSON experiments compatible.

| Action | Input | Effect / automatic record |
|---|---|---|
| Show | name, duration integer or ConfigField name, slot or Stimulus placements | Timed static display, resolved parameters, software/virtual events |
| CollectResponse | declared response meanings, timeout, optional visible slot | Framework maps TUI keys, timestamps and records one valid response |
| RecordState | label, optional state fields | Detached finite JSON state, condition, resolved stimuli and response snapshot |
| UpdateState | function(state, response), optional action name | Immutable inputs; validate and replace scientific state |
| UpdateAdaptive | registered algorithm instance, staircase identity, update_value(state,response,step), state_key | Shared algorithm updates state and records before/after history |

Each action name in a trial must be unique. Exactly one response stage is
required. Only non-rendering actions may follow it. Adaptive actions require a
preceding response. UpdateState before response receives None as response.
A timed show must be positive; response timeout 0 waits for a valid key.
Timeout and Escape preserve partial events and never invent a response.

State is finite JSON data with string keys, not arbitrary objects or file handles.
Callback inputs are recursively read-only. Historical snapshots are detached
from later changes. Callbacks are trusted Python, not an OS sandbox: they must
perform only scientific calculation, without file access or rendering.

All visual parameters are resolved and images prepared before the timed trial.
Stimulus positions are degrees from screen centre, checked for clipping on the
live calibrated display. Multiple patches are opaque and draw in written order.
UpdateState changes scientific state, used to construct the next trial; it does
not mutate already prepared images. Dynamic/frame-driven stimuli remain future
work and are required before replacing the full CSF shader path.

## Records

trial_actions.json separates each trial's plan from its execution events and
records initial/final state. Every event is associated with trial/action index.
RecordState snapshots include scientific state, stimuli/parameters, condition,
and the response if collected. Live software clocks and virtual schedules have
different labels; neither certifies photon onset or HID latency.

trial_presentations.json remains compatible and contains accepted responses'
visual phase observations and extra scalar measurements. Canonical trials.tsv
retains its documented schema. No custom columns or researcher file writes.

The sequence itself performs no disk IO. Accepted responses, state events and
adaptive history flush at the end of the trial, also on exceptions. A valid
response remains saved if a later scientific update fails. A crash/power loss
during a trial can lose that in-memory trial; completed trial files remain.
The ordinary runner still owns preflight, source provenance, manifests and
completion/abort/error lifecycle. validate_run checks action associations,
partial records and canonical response consistency.

## Configuration compatibility

New beginner JSON contains schema_version, experiment_id and values. Python
contains the action sequence. The same ConfigField schema validates settings
and TUI overrides; resolved configuration and source JSON/hash are saved.

Earlier timeline JSON with schema_version=1 and phases continues to use
load_timeline, including explicit {"field":"timing_name"} duration references.
No Python expression is evaluated. Existing CSF five-phase JSON remains active
through its legacy adapter; this is not evidence of full migration.

See [architecture audit](TRIAL_ACTION_ARCHITECTURE.md) and
[CSF migration evidence](CSF_ACTION_MIGRATION.md).
