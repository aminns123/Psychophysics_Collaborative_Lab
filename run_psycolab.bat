@echo off
rem Normal TUI entry point; read-only environment checks precede launch.
rem Fresh maintainer Git checkouts: run setup_psycolab_dev.bat once first.
call "%~dp0scripts\windows_startup.cmd" --source "%~dp0." %*
exit /b %ERRORLEVEL%
