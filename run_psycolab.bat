@echo off
rem Sole normal batch entry point; read-only qualification precedes application launch.
call "%~dp0scripts\windows_startup.cmd" --source "%~dp0." %*
exit /b %ERRORLEVEL%
