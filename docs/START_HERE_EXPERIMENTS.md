# Start here: learn stimulus and experiment building

**New canonical standalone tutorial:**
[LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md).

It covers, in order: architecture → create a white line → preview image →
publish stimulus → assemble a new above/below task from the library →
simulate → publish experiment → configure and run → inspect output.

Read it in any editor or run this in `run_user_env.bat`:

```cmd
python -m psychophysics_lab --learn
```

**Authoring rules:** [AUTHORING_CONTRACT.md](AUTHORING_CONTRACT.md).
**Advanced trial details:** [TRIAL_ACTION_ARCHITECTURE.md](TRIAL_ACTION_ARCHITECTURE.md).
**CSF hardware boundary:** [CSF_ACTION_MIGRATION.md](CSF_ACTION_MIGRATION.md).

The built-in `example_experiment.py` remains a worked **left/right**
demonstration for reading; it is **not** the default advanced authoring
template. New Python experiment scaffolds are task-neutral and deliberately
require the researcher to fill in the science. Simple spatial two-choice
experiments should use the JSON-only library builder first.
