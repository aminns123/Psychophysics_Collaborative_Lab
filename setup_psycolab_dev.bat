@echo off
rem Compatibility only. Use PsyCoLab.bat. Retirement: see docs/WINDOWS_LAUNCHERS.md.
rem Compatibility setup entry. Keep until a clean Windows acceptance run qualifies retirement.
call "%~dp0scripts\windows_development.cmd"
set "PSYCOLAB_SETUP_EXIT=%ERRORLEVEL%"
pause
exit /b %PSYCOLAB_SETUP_EXIT%
