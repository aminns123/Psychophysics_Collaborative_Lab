@echo off
rem Compatibility only. Use PsyCoLab.bat. Retirement: see docs/WINDOWS_LAUNCHERS.md.
rem Start PsyCoLab; first-time source setup runs only when no environment exists.
call "%~dp0scripts\windows_startup.cmd" --source "%~dp0." %*
exit /b %ERRORLEVEL%
