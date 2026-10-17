# Framework internals

These files support the experiment files in the parent folder. Researchers do
not edit them to add an experiment or change its scientific design.

- `spec.py`: field declarations, coercion and experiment validation infrastructure.
- `responses.py`: reusable response decoding and index-equality correctness.
- `registry.py`, `contributions.py`: registration and discovery of parent-folder files.
- `library_builder.py`: compatibility with historical saved JSON designs.
- `source_names.py`: one documented source rename while preserving saved-run IDs.
- `flanker_response.py`: historical CSF specification alias, not an authoring example.

Scientific settings, stimulus placement, trial order and timing, response meanings,
numeric adaptive updates and stopping decisions belong in the parent experiment.
Shared adaptive engines live in `../../adaptive/`; each experiment explains the
scientific semantics it relies on and supplies the chosen run values.
