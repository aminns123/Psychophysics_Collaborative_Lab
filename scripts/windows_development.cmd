@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
echo PsyCoLab first-time source setup - Python 3.11 x64
echo This prepares the existing development environment; no display calibration is granted.
rem One bootstrap discovery path shared by setup and the consolidated launcher.
if exist ".venv-dev\Scripts\python.exe" (
    ".venv-dev\Scripts\python.exe" -I -B "scripts\developer_setup.py"
    goto finished
)
if defined PSYCOLAB_BOOTSTRAP_PYTHON (
    "%PSYCOLAB_BOOTSTRAP_PYTHON%" -I -B "scripts\developer_setup.py"
    goto finished
)
py -3.11 -I -B -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>nul
if not errorlevel 1 (
    py -3.11 -I -B "scripts\developer_setup.py"
    goto finished
)
python -I -B -c "import sys; assert sys.version_info[:2] == (3, 11)" >nul 2>nul
if not errorlevel 1 (
    python -I -B "scripts\developer_setup.py"
    goto finished
)
echo Python 3.11 is required. Install 64-bit Python 3.11 with your Python install manager:
echo   py install 3.11
echo Or download Python 3.11 from python.org. Reopen PsyCoLab.bat afterwards and choose 2 - Check / Repair PsyCoLab.
echo An existing Python installation and your global PATH will not be changed by PsyCoLab.
exit /b 1
:finished
exit /b %ERRORLEVEL%
