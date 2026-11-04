# Python Workspace

Double-click **PsyCoLab.bat** and choose **3 - Python Workspace**. This opens a
normal Windows command prompt in the same terminal, with the verified PsyCoLab
environment active. The banner identifies its Python interpreter and whether it
is a source development or qualified environment. No second environment is made.

If the environment is not ready, choose **2 - Check / Repair** first. The launcher
never silently installs packages when entering a healthy workspace.

Run ordinary Python commands, including trusted scripts outside the checkout:

```bat
python --version
python -m pip list
python "D:\Research folder\my experiment.py" "argument with spaces"
python -m psychophysics_lab --learn
```

The command prompt remains open after a script exits. Type **exit** to return to
the PsyCoLab menu. Choose option 3 again to reopen it. Its initial working folder
is the source checkout; select explicit external locations for research data and
use script-relative paths when appropriate.

This is a development workspace, not a grant of calibration, study approval or
laboratory software qualification. Changing packages in a qualified environment
can invalidate its checks. Source dependencies are pinned; installing additional
packages deliberately can introduce conflicts that require review and retesting.
Optional packages and user_requirements.txt are never installed automatically.

The older run_user_env.bat and PsyCoLab_Python.bat names are temporary
compatibility entries. Existing USER_env folders and their personal files are
preserved; the current launcher does not select or rewrite them. See the
[launcher inventory and retirement policy](WINDOWS_LAUNCHERS.md).

For automation, use `PsyCoLab.bat --python "script path.py" arguments` to run once
with the same verified Python and preserve the script's exit code. Use
`PsyCoLab.bat --workspace` to open only the command workspace. The normal menu
displays operation failures and returns to its choices; selecting Exit closes
it normally. No script or acquisition is retried automatically.
