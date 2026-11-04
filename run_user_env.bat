@echo off
rem Compatibility name: use the same environment as the application.
call "%~dp0PsyCoLab_Python.bat" %*
exit /b %ERRORLEVEL%
