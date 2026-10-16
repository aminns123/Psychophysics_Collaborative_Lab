# Trial actions: architecture decision and migration audit

Baseline: main ad7c132 (PR #42 merged), inspected 2026-10-16 in
C:/Users/alexz/Personal_Folder/Git_Folder/Psychophysics_Shanghi.
Git status was clean, including untracked files. The tracked researcher drafts
probe_white_line and test_single_probe_and_fixation and authoring inventory are retained.

## Decision

The researcher owns stimulus appearance, conditions, order, response meaning and
scientific updates. Extend TrialTimeline/Phase and RunContext.play_trial rather
than introduce a second experiment runner. Keep existing phase JSON readable.

Add Show and CollectResponse convenience declarations, RecordState, UpdateState
and UpdateAdaptive. A trial has one response; non-rendering actions may follow it.
A Show can contain several independently positioned opaque grayscale patches,
in explicit drawing order (later patches cover earlier patches). This is not
alpha compositing, arbitrary sub-frame scheduling or a dynamic shader API.

Resolve timing field references before presentation. Pre-render visual stages.
RecordState takes detached finite JSON snapshots; functions receive immutable
state and response values and return validated replacements. Python callbacks
are trusted scientific code, not a sandbox: their contract forbids IO/rendering.
The framework itself writes only at the end of a trial (including abort/error),
outside the timed phase loop. A crash/power loss during a trial can lose that
in-memory trial; completed trials remain durable. Planned actions and observed
events are separate, with explicit virtual versus software timing basis.

## Evidence-based source audit

| Location | Classification and execution evidence | Problem / action |
|---|---|---|
| src/psychophysics_lab/core/runner.py | Active universal run owner; simulations/run.py also calls run_request | Retain preflight, provenance, finalization and output layout |
| researcher.py, core/timeline.py, core/presentation.py | Active public authoring and static presentation; orientation and example procedures call play_trial | Consolidate present/play_trial display and recording; add non-rendering actions here |
| stimuli/registry.py, experiments/registry.py, adaptive/registry.py | Active distinct scientific registries | Different responsibilities, not duplicates; retain |
| contributions.py, experiments/contributions.py, authoring.py | Built-in allowlist plus explicit draft/Ready inventory loading the SAME registries | Retain; correct outdated instructions requiring edits to framework registry |
| Experiments/contrast_sensitivity_function.py | Active legacy CSF entry selected by experiments/contrast_sensitivity.py | Retain until shader, event and scientific parity; JSON phase wrapper is not migration |
| Events/stimuliC.py, libC.py, packages.zip | Active CSF shader/window/runtime, imported by above | No deletion; raster renderer cannot yet establish equivalent floating-point commands/phase/geometry |
| Events/adaptiveMethods.py, adaptive_session.py | Active condition selection, file/event adaptation and six-column/canonical CSF output; used by simulations/csf.py too | Preserve adapter; extract only demonstrably identical reusable mathematics |
| Events/staircase.py | Compatibility re-export of adaptive/staircase.py | Intentional alias, not duplicate algorithm; retain historical imports |
| Events/display_contrast.py | Active digital contrast equations used by renderer validation, analysis and CSF | Preserve definitions; no physical luminance claim |
| Functions/functionsForUse.py, Interface/config.py | Active legacy state/config/file helpers imported by CSF and its simulation | Not obsolete; remove only after adapter migration |
| simulations/registry.py, scenarios/ | Testing-specific observer factories and scenarios, using core runner | Not competing human execution engines; retain |
| data/session.py, trials.py, workspace.py | Authoritative run persistence and provenance | Reuse; action events get versioned sidecar, no arbitrary new TSV columns |
| example_stimulus.py / example_experiment.py | PR42 active beginner source and scaffold templates | Keep simple line; replace indirect phase-only teaching sequence with explicit action list |
| orientation_task / orientation_adaptive | Active advanced examples sharing one procedure | Use as advanced integration; no Gabor math in beginner |
| stimuli/probe_white_line.py, experiments/test_single_probe_and_fixation.py | Researcher drafts in authoring/components.json | Preserve byte-for-byte; never classify test_* scientific files as disposable tests |
| blueprints/, scaffold.py, simulations/scaffold.py | Scientific and observer/scenario templates for different jobs | Retain separate purposes; no duplicate runner |
| ui/setup.py, development.py, run_user_env.bat | Normal TUI building/testing and plain Python terminal, PR41 | Retain one GUI; do not restore removed USER_env GUI |
| docs/EXPERIMENT_TIMELINES.md | Partly stale registration/phase-only instructions | Update to current Ready workflow and extended actions |

No source is proved obsolete merely by its name. The safe cleanup target is
duplicated public presentation loops and stale documentation, not historical
scientific code. Import evidence: CSF -> Events/Interface/Functions/libC;
simulations/csf -> LegacyStaircaseSession -> shared adaptive registry;
public procedures -> RunContext -> Presentation -> common data services.

## Original PhD reference inspected

aminns123/psychophysics_experiments_git:
- Ellipse2D_experiment.py builds ordered fixation/probe/mask/delay/response objects
  and simultaneous lists of stimuli. Preserve that readable chronological intent.
- Functions/functionUSE.py (287592a): Trial_ADMs (line 20852) mixes state selection,
  file reads and display roles; record_event (4148) dispatches by trial-name strings.
  Replace artificial visual objects with typed non-rendering actions.
- stimuliC.py (1c3e629): ellipse/annulus shader geometry is stimulus-owned.
- libC.py (904122a): on_key_press (464) routes keys to logger then advances trial;
  do not duplicate this handler in new researcher modules.

## CSF parity boundary and strategy

Existing CSF: one leading fixation, then fixation -> new_condition -> stimuli ->
interval -> response; left/down/left-shift versus right/up/right-shift mappings.
Independent interleaved staircases; initial one-down phase; configured n-down/n-up;
legacy logarithmic contrast update; reversal counting on post-update intensities,
ignoring flats and excluding placeholder row; global response ceiling versus
per-staircase reversal completion. Saved presented and next quantities are distinct.

Capture fixed-response reference traces through the real legacy event adapter,
then compare shared action execution: selected identities, conditions/targets,
presented/next commands, steps, streaks, reversal counts and stop status.
Use existing threshold analyser on canonical/legacy fixtures. Cover response
ceiling, reversal completion, multiple conditions, initial phase, abort/fail.
Do not replace human CSF without matching shader/geometry/contrast, leading
fixation, timeout/key filtering, calibration preflight and historical outputs.
Hardware photometry, photon timing, HID latency remain NOT TESTED here.

Implementation order: audit commit; action model/executor/partial recording;
beginner and advanced examples + authoring/docs; deterministic CSF development
validation (retain legacy default where parity incomplete); full tests Windows
and Ubuntu CI; reviewable PR with criterion-level evidence, never auto-merge.
