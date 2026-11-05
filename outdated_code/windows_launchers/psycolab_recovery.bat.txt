@echo off
rem Compatibility only. Use PsyCoLab.bat. Retirement: see docs/WINDOWS_LAUNCHERS.md.
rem Diagnose, explain and offer supported source repair. --restore undoes a repair.
call "%~dp0scripts\windows_startup.cmd" --recover "%~dp0." %*
exit /b %ERRORLEVEL%
