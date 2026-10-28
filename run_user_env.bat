@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo   PsyCoLab USER_env - Interactive Python Terminal
echo ============================================================
echo This runs your authored Python code with your user permissions.
echo This is not an OS sandbox; only open code you trust.
echo USER_env isolates Python packages, not arbitrary script files or output.
echo.

if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml was not found next to this launcher.
    goto failed
)

rem Use a verified Python 3.11 interpreter. The Windows py launcher can
rem exist without a registered 3.11 runtime, so never trust "where py" alone.
rem A functioning main PsyCoLab .venv is a valid bootstrap for USER_env.
set "USERENV_BOOTSTRAP="

if exist "USER_env\Scripts\python.exe" (
    "USER_env\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 set "USERENV_BOOTSTRAP="USER_env\Scripts\python.exe""
)

if not defined USERENV_BOOTSTRAP (
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
        if not errorlevel 1 set "USERENV_BOOTSTRAP=".venv\Scripts\python.exe""
    )
)

if not defined USERENV_BOOTSTRAP if defined PSYCOLAB_BOOTSTRAP_PYTHON (
    if not exist "%PSYCOLAB_BOOTSTRAP_PYTHON%" (
        echo ERROR: PSYCOLAB_BOOTSTRAP_PYTHON does not name an existing interpreter.
        goto failed
    )
    set "USERENV_BOOTSTRAP="%PSYCOLAB_BOOTSTRAP_PYTHON%""
)

if not defined USERENV_BOOTSTRAP (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
        if not errorlevel 1 set "USERENV_BOOTSTRAP=py -3.11"
    )
)

if not defined USERENV_BOOTSTRAP (
    for /f "delims=" %%P in ('where python3.11.exe 2^>nul') do (
        if not defined USERENV_BOOTSTRAP (
            "%%P" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
            if not errorlevel 1 set "USERENV_BOOTSTRAP="%%P""
        )
    )
)

if not defined USERENV_BOOTSTRAP (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
        if not errorlevel 1 set "USERENV_BOOTSTRAP=python"
    )
)

if not defined USERENV_BOOTSTRAP (
    where python3 >nul 2>nul
    if not errorlevel 1 (
        python3 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
        if not errorlevel 1 set "USERENV_BOOTSTRAP=python3"
    )
)

if not defined USERENV_BOOTSTRAP (
    echo ERROR: No working Python 3.11 interpreter was found.
    echo If run_psycolab.bat works, verify .venv\Scripts\python.exe exists.
    echo For fresh setup see docs\WINDOWS_ENVIRONMENT.md for the exact qualified
    echo interpreter and PSYCOLAB_BOOTSTRAP_PYTHON. Do not replace global Python.
    goto failed
)

echo Preparing isolated USER_env with Python 3.11...
%USERENV_BOOTSTRAP% "scripts\launcher_setup.py" --user-env
if errorlevel 1 (
    echo ERROR: USER_env dependency setup or validation failed.
    goto failed
)

if not exist "USER_env\Scripts\python.exe" (
    echo ERROR: USER_env\Scripts\python.exe was not created.
    goto failed
)

rem Activate the environment in this process. A child Command Prompt inherits
rem the Python/PATH environment, so "python" can run any trusted .py script.
rem Do NOT auto-open the optional Textual development workbench.
call "USER_env\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Could not activate USER_env.
    goto failed
)

python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
if errorlevel 1 (
    echo ERROR: USER_env activation did not select Python 3.11.
    goto failed
)

echo.
echo ============================================================
echo   USER_env is ready - Python 3.11
echo ============================================================
echo.
echo Paste your own commands at the prompt, for example:
echo   python "C:\path\to\my_experiment.py"
echo.
echo Optional scientific development commands:
echo   python -m psychophysics_lab --dev-list
echo   python -m psychophysics_lab --dev-preview my_stimulus
echo   python -m psychophysics_lab --dev-test my_experiment
echo   python -m psychophysics_lab --dev-ready experiment my_experiment
echo.
echo PsyCoLab packages are installed and checked automatically.
echo To add extra third-party packages, edit user_requirements.txt
echo and reopen this launcher.
echo.
echo Type exit when you want to close this terminal.
echo.
rem Keep an interactive terminal open even when launched by double-click.
"%ComSpec%" /D /K "title PsyCoLab USER_env - Python 3.11"
exit /b 0

:failed
echo.
echo USER_env could not start. Please review the specific error above.
pause
exit /b 1
