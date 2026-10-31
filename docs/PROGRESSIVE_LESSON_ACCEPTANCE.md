# Progressive laboratory lesson software acceptance

Baseline: merged develop `8f493fa0a54cbe57109943120b5e410e77c0541a`.
The primary [lesson guide](../examples/laboratory_extensions/LESSONS.md) contains
the progression table, normal workflow and one concrete exercise per lesson.

## Scientific and teaching boundaries

All three keep the same left/right line discrimination and F/J meanings.
Beginner is a finite alternating task with no adaptive machinery. Intermediate
adds distance cells, separate histories and the installed contrast methods.
Advanced adds distance × length cells, an independently declared soft-edged
line, retention and optional onset/answer cues. They are separate ordinary Python
files, not imports of official experiments renamed as local science.

A1 contains the editable choices, chronological events and explicit measurement
units. A2 contains the selection, strength mapping, validation and stopping.
B uses existing execution/record projection and registration. Beginner needs no
staircase vocabulary. Intermediate deliberately explains condition versus target
versus track versus repetition, before adding richer factors. Independent tracks
make the advanced example longer; source shortening is not the acceptance metric.
No lesson claims that a finite teaching staircase yields a justified threshold.

Only opt-in bundle sources, documentation, learning links and tests change.
The two established starters/presets and official scientific sources remain
unchanged. Learning buttons open files; no scientific Configure/Review logic is
added. No new engine, configuration language, registry layer or generator exists.
Existing starter provisioner leaves existing folders byte-for-byte unchanged.

## Reproducible software exercise

`tests/test_progressive_lessons.py` creates disposable source copies and private
configuration/data roots, then starts fresh subprocesses for each lesson and
each source route. It uses the actual Textual widgets and canonical simulation,
not a substituted experiment or parallel runner. Its checks include:

- Project discovery and explicitly trusted external-folder discovery, Draft →
  Test → Ready, custom stimulus Preview → Ready, and changed-source invalidation.
- Generic Configure without scientific panels; declared conditions, responses,
  timing and unit-labelled observations in Review; actual local Python source
  links, including a same-name project decoy in the external route.
- Generic parameter editor, invalid draft retention/correction, presets,
  refresh/resume and read-only preservation of experiment/stimulus/core sources.
- Both declared methods, fixed/adaptive distinctions, exact repeated trial bytes,
  independent histories, saved measurements, geometry/intensity preparation,
  response keys/correctness, 20 canonical columns, validator and historical reader.
- Non-finite/duplicate/boundary inputs, unsafe geometry, undersized plans,
  requested optional audio and zero-response / mid-run interruption preservation.

Representative commands (from an isolated Windows development checkout):

```text
.venv-dev\Scripts\python.exe -m pytest -q tests/test_progressive_lessons.py
.venv-dev\Scripts\python.exe -m pytest
.venv-dev\Scripts\python.exe scripts/portability_check.py
```

## Acceptance matrix

| Criterion | Outcome / evidence |
|---|---|
| Beginner in project and external routes | PASS: deterministic runs, generic editing and saved data |
| Intermediate, both methods and routes | PASS: independent tracks/fixed schedules, recordings and interruption checks |
| Advanced, both methods and routes | PASS: custom stimulus, factors, software UI and saved data |
| Existing source and lab-folder preservation | PASS in disposable exercises; existing provisioner regressions retained |
| Portability | PASS; final exact-source CI result recorded in PR |
| Complete Windows regression | Required; final executed result recorded in PR |
| Independent first-time scientist understanding | NOT VERIFIED; no human was observed completing the exercises |
| Native display, physical audio/contrast/timing | NOT VERIFIED; software tests do not qualify apparatus |

The UI evidence is Textual's real software interaction harness. It is not native
human acceptance, an independently installed student computer, or a qualification
of a psychophysical measurement protocol. Existing calibration/qualification,
source trust, researcher override and environment-role safeguards remain intact.
