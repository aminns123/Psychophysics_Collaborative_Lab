@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   PsyCoLab USER_env - Researcher Development Workspace
echo ============================================================
echo This runs your authored Python code with your user permissions.
echo This is not an OS sandbox; only open code you trust.
echo Simulated data are isolated from human experiment data.
echo.
if exist "USER_env\Scripts\python.exe" goto launch
where py >nul 2>&1
if errorlevel 1 goto try_python
py -3.11 -m venv "USER_env"
if errorlevel 1 goto failed
goto install
:try_python
python -m venv "USER_env"
if errorlevel 1 goto failed
:install
"USER_env\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,11), 'PsyCoLab requires Python 3.11'"
if errorlevel 1 goto failed
"USER_env\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto failed
:launch
"USER_env\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
"USER_env\Scripts\python.exe" -m psychophysics_lab --user-env
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo USER_env could not start. Install Python 3.11, check dependencies and try again.
pause
exit /b 1
