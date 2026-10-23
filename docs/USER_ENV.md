# USER_env — interactive Python terminal

**Start here:** [Learn PsyCoLab](LEARN_PSYCOLAB.md) is the authoritative,
standalone stimulus → experiment → preview → simulation → Ready → run tutorial.
Type `python -m psychophysics_lab --learn` in USER_env to read it without the TUI.


**USER_env is a regular Windows Command Prompt with an activated Python
environment, not a second PsyCoLab TUI.** It uses its own Python 3.11 virtual
environment to let you run and debug trusted scripts by typing normal commands.

## Start a session

Double-click `run_user_env.bat` in the repository root. The launcher:

1. Finds a working Python 3.11 interpreter, reusing PsyCoLab's `.venv` Python
   as a bootstrap if the Windows `py -3.11` launcher cannot find it.
2. Creates `USER_env/` if needed. Installs PsyCoLab and all dependencies
   declared in `pyproject.toml` (including NumPy, Pyglet, Textual, Matplotlib).
3. Reuses installed packages when requirements have not changed, checks
   dependencies on each launch, and updates changed package requirements.
4. Activates `USER_env` and leaves a **plain persistent Command Prompt** open.

You can immediately paste ordinary commands, such as:

```cmd
python --version
python "C:\path\to\my_experiment.py"
python -m pip list
```

The terminal remains open when your script exits. Type `exit` to close it.
Quoted paths may contain spaces. The starting directory is the PsyCoLab repository
root, and any Python module you run directly needs a runnable entry point.

You can also activate USER_env manually in Command Prompt using
`call USER_env\Scripts\activate.bat`, or in PowerShell with
`.\USER_env\Scripts\Activate.ps1` if local execution policy permits.

**No separate USER_env graphical TUI is launched or installed.** The normal
PsyCoLab TUI still provides Build Stimuli, Build Experiments, source inspection,
experiment configuration and human-acquisition preflight.

## Automatic dependencies, including optional user packages

All built-in PsyCoLab dependencies are managed by the launcher. You do not need
to download or install them separately.

A new, researcher-authored script may import additional third-party libraries
that PsyCoLab cannot predict. On first launch, the setup automatically creates
`user_requirements.txt` alongside the BAT. This file is intentionally ignored
by Git. To request your own optional packages, add one pip requirement per line:

```text
# For my experiment (examples only)
scipy>=1.11
pandas>=2
```

Exit the terminal and double-click `run_user_env.bat` again. The bootstrap
detects changes to `user_requirements.txt`, installs those dependencies and
checks the resulting environment. You may instead use
`python -m pip install package-name` manually from the terminal. The
environment retains these installations between runs.

The *first* installation and genuinely new dependencies may need internet access
or a local pip cache; this launcher does not bundle offline wheels. A package
installation failure is shown rather than silently running an unvalidated
environment.

## Optional build/test/publish commands (no extra TUI)

The normal PsyCoLab TUI **does not generate stimulus files**.
Add a `LibraryStimulus` class directly to
`src/psychophysics_lab/stimulus_library.py`. Write experiment Python
files explicitly in `src/psychophysics_lab/experiments/` and use
`--dev-stage experiment ID`, `--dev-test ID` and
`--dev-ready experiment ID` to validate. There is no second
stimulus authoring interface.


## Scientific and safety boundaries

- USER_env is a Python virtual environment, **not a security sandbox**. Only run
  Python code and install packages you trust; they have your user permissions.
- Running an *arbitrary* Python script in USER_env does **not** automatically
  redirect its output. The script can save anywhere your user can write.
  Isolation of synthetic test data applies to PsyCoLab's development commands.
- This does not establish physical luminance, stimulus timing, flicker/SOA
  accuracy, monitor geometry or keyboard latency.
- Existing CSF presentation and human experiment preflight remain unchanged.

## Share, update and promote local science

`USER_env` is not an isolated external extension runtime. Use its supported
preview/test/publish commands on source currently recognised by PsyCoLab;
retain custom scientific edits on a private branch/fork. For safe Git updates
and an eventual sibling extension directory, see
[safe updates](SAFE_UPDATES_AND_LOCAL_WORK.md) and
[the international roadmap](INTERNATIONAL_LAB_ROADMAP.md).
