# Researcher experiment files

Edit an experiment Python file here and the relevant class in
`../stimulus_library.py`. Every experiment follows the same seven sections:

1. **Settings and stimuli** — defaults, units, stimulus choices and response meanings.
   The TUI supplies the selected values for a run.
2. **Conditions and trial order** — `make_conditions()` declares conditions and scheduling.
3. **Prepare stimuli** — `prepare_stimuli()` applies condition geometry and appearance.
4. **One trial** — `make_trial()` shows the chronological displays, sounds and response period.
5. **Responses and adaptation** — correctness, numeric changes, optional initial phase and bounds.
6. **Run and finish** — `procedure()` chooses a condition, prepares stimuli, presents the
   trial, interprets the response, updates the experiment, then checks whether to finish.
7. **Framework connection** — validation and `SPEC = definition()` connect the science
   above to the TUI, calibration and shared data saving.

Response interpretation and updates execute as actions inside `run.play_trial()`;
the comments in each loop identify that sequence. Do not apply them a second time
after the call. Fixed-trial experiments state that they have no adaptation.

Start with `probe_above_below.py` for a fixed-trial experiment, or `csf_thesis.py`
for independent adaptive staircases. `orientation_adaptive.py` illustrates a
fixed response count with adaptive contrast. The three historical reconstructions
retain their original scientific quirks and acquisition blocks.

`_internal/` contains discovery, declarations, validation infrastructure and
historical design compatibility. Researchers do not edit it to create experiments.
`__init__.py` is the required package entry point; it contains no experiment science.
The edited custom file `new_probe_vertical_line_stimulus.py` remains subject to its
existing Draft/Test/Ready checks; changing source does not silently publish it.
