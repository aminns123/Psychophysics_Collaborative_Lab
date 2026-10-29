@echo off
rem Recovery fallback only; does not automatically launch this application.
call "%~dp0scripts\windows_startup.cmd" --recover "%~dp0."
exit /b %ERRORLEVEL%
