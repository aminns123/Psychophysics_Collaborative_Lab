# PsyCoLab authoring contract — single route

**Researcher-facing sources:** one `src/psychophysics_lab/stimulus_library.py`
for all new stimulus classes, and one independent
`src/psychophysics_lab/experiments/<id>.py` for each custom experiment.
No stimulus file generator, separate stimulus registration, or automatic
experiment-copy wizard in the TUI.

Every `LibraryStimulus` class in the shared library has `PARAMETERS`,
`render(parameters, x_deg, y_deg)`, and `SPEC`. The engine discovers
classes and validates generated digital pixel values. New classes can use
`default_config=""` for inline parameter defaults. Existing historic IDs
may still have their JSON defaults for reproducibility.

The experiment defines conditions, `TrialTimeline`, placements in visual
degrees, responses and adaptive algorithms. It references stimulus IDs
rather than duplicating rendering mathematics. Optional `Beep` actions
are experiment-owned, never added inside a stimulus renderer.

Manual experiment files are registered once with
`--dev-stage experiment ID`, virtually tested with `--dev-test ID`, and
published with `--dev-ready experiment ID`. No files are generated.
A **Ready** software result is not physical monitor or audio validation.

The historic JSON-only experiment engine and old CSF acquisition modules
are retained as compatibility/runtime dependencies, **not** as alternative
ways researchers should author new stimuli and experiments. Their files
are not listed on the Build Stimuli screen.

Read [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md) for the complete short workflow.
See [REPO_SURFACE_AUDIT.md](REPO_SURFACE_AUDIT.md) for retention decisions.
