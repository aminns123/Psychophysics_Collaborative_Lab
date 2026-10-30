@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo PsyCoLab maintainer setup - separate .venv-dev, CPython 3.11 x64
echo Downloads the project development dependencies. No laboratory qualification is granted.
if exist ".venv-dev\Scripts\python.exe" (
    ".venv-dev\Scripts\python.exe" -I -B "scripts\developer_setup.py"
    goto finished
)
py -3.11 -I -B -c "import sys" >nul 2>nul
if not errorlevel 1 (
    py -3.11 -I -B "scripts\developer_setup.py"
    goto finished
)
python -I -B -c "import sys" >nul 2>nul
if not errorlevel 1 (
    python -I -B "scripts\developer_setup.py"
    goto finished
)
echo No working Python was found. Install 64-bit Python 3.11, then reopen this setup.
pause
exit /b 1
:finished
set "PSYCOLAB_SETUP_EXIT=%ERRORLEVEL%"
if not "%PSYCOLAB_SETUP_EXIT%"=="0" echo Review the setup error above before retrying.
pause
exit /b %PSYCOLAB_SETUP_EXIT%
