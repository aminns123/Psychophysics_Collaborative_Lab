@echo off
rem Compatibility only. Use PsyCoLab.bat. Retirement: see docs/WINDOWS_LAUNCHERS.md.
rem Compatibility name: use the same environment as the application.
call "%~dp0PsyCoLab_Python.bat" %*
exit /b %ERRORLEVEL%
