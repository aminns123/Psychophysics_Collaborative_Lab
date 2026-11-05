@echo off
rem Compatibility only. Use PsyCoLab.bat. Retirement: see docs/WINDOWS_LAUNCHERS.md.
rem Same verified Python as Run_PsyCoLab; no separate USER_env installation.
call "%~dp0scripts\windows_startup.cmd" --python "%~dp0." %*
exit /b %ERRORLEVEL%
