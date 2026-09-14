@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ============================================================
echo   PsyCoLab - Psychophysics Collaborative Lab
echo ============================================================
echo.

if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml was not found next to this launcher.
    echo Please run this file from the PsyCoLab repository.
    pause
    exit /b 1
)

set "PSYCOLAB_PYTHON="

where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PSYCOLAB_PYTHON=py -3.11"
)

if not defined PSYCOLAB_PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
        if not errorlevel 1 set "PSYCOLAB_PYTHON=python"
    )
)

if not defined PSYCOLAB_PYTHON (
    where python3 >nul 2>nul
    if not errorlevel 1 (
        python3 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
        if not errorlevel 1 set "PSYCOLAB_PYTHON=python3"
    )
)

if not defined PSYCOLAB_PYTHON (
    echo ERROR: PsyCoLab currently requires Python 3.11.
    echo.
    echo Install a 64-bit Python 3.11 interpreter, then run this launcher again.
    echo PsyCoLab intentionally keeps the tested Python 3.11 / Pyglet 1.5.27
    echo baseline while the legacy OpenGL renderer is being validated.
    pause
    exit /b 1
)

echo Preparing the local PsyCoLab environment...
%PSYCOLAB_PYTHON% "scripts\launcher_setup.py"
if errorlevel 1 (
    echo.
    echo ERROR: PsyCoLab environment setup failed.
    echo Review the messages above. No experiment has been started.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe was not created.
    pause
    exit /b 1
)

echo.
echo Starting PsyCoLab...
echo.
".venv\Scripts\python.exe" -m psychophysics_lab
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo PsyCoLab exited with code %APP_EXIT%.
    pause
)

exit /b %APP_EXIT%
