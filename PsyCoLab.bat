@echo off
rem The authoritative Windows entry point. The native menu needs no Python.
call "%~dp0scripts\windows_startup.cmd" --entry "%~dp0." %*
exit /b %ERRORLEVEL%
