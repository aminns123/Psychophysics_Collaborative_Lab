# PsyCoLab experiment lifecycle contract

This document defines how a PsyCoLab acquisition run ends. Termination is part
of the scientific data contract, not just GUI behaviour.

## Final statuses

| Status | Meaning | Process exit |
|---|---|---|
| `completed` | All configured scientific/adaptive termination criteria were satisfied. | Normal (`0`) |
| `max_trials_reached` | The accepted-response safety ceiling was reached before all criteria completed. | Normal (`0`) |
| `aborted_by_user` | The researcher deliberately pressed Escape. | Normal (`0`) |
| `error` | Unexpected software/data/runtime failure. | Error/non-zero |

A manual abort is therefore scientifically distinct from successful completion,
but it is not a software crash.

## Accepted-response durability

`trials.tsv` is canonical. Every accepted participant response is appended,
flushed and fsynced before the experiment proceeds. Therefore:

- if response 37 has been accepted and Escape is pressed afterwards, response 37
  remains in the run;
- if Escape is pressed during the next fixation/stimulus before a response is
  accepted, no trial 38 is invented;
- derived files such as `trials_readable.txt` are generated during finalisation
  and can always be recreated from `trials.tsv`.

## Automatic adaptive completion

After each accepted response the adaptive state is updated. If that response
causes the final unfinished staircase to satisfy its reversal criterion, the
sequence is:

```text
accept response
    ↓
update adaptive state
    ↓
append + flush trials.tsv
    ↓
save adaptive_session.json
    ↓
recognise all staircases complete
    ↓
stop accepting input / clear queued trials
    ↓
close Pyglet experiment window
    ↓
write final snapshots + trials_readable.txt + manifest + runs_index.csv
    ↓
return to terminal and report completed
```

No additional participant response is accepted once the adaptive run is no
longer `running`.

## Escape

Escape is intercepted before the legacy Pyglet key handler can treat it as an
ordinary key event. PsyCoLab first writes `aborted_by_user` to the adaptive
session metadata, then clears queued trials and requests clean GUI exit.

Finalisation then records the same status in `manifest.json`, `runs_index.csv`
and top-level workspace state. The terminal reports the number of accepted
responses and exact run folder.

## Maximum-response ceiling

`max_trials_reached` is not equivalent to `completed`. It means the configured
safety ceiling was reached while at least one staircase remained unfinished.
The terminal summary reports completed and unfinished staircase identities.

## Terminal behaviour

When launched with `run_psycolab.bat`, the command window deliberately pauses
after a normal return as well as after errors. This allows a researcher to verify
the final status and saved-data location before closing the terminal.

When PsyCoLab is launched directly from an existing PowerShell/Command Prompt,
the program simply returns to that shell normally.
