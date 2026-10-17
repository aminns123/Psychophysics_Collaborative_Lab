# Historical JSON library-builder description

**This document describes an older optional JSON-only spatial builder, not
the current recommended scientific authoring route.**

The ONLY normal workflow is documented in
[LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md): add visual stimulus classes to
`src/psychophysics_lab/stimulus_library.py`, compose reusable Scenes,
and write one Python experiment in `experiments/<task>.py` with settings
in `configs/experiments/<task>.json`.

The JSON builder is retained internally for compatibility with past work,
not presented as a competing way to start new experiments. No generated
Python stimulus files or registry edits are required.
