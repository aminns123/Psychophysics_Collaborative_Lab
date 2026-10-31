@echo off
setlocal EnableExtensions
rem Internal bootstrap shared by normal launch and explicit recovery. No Python.
if not "%~1"=="--source" if not "%~1"=="--recover" exit /b 2
rem Claim a private directory atomically. RANDOM can repeat across cmd processes
rem or be fixed by an inherited environment variable; it is not a unique-file API.
set /a "PSYCOLAB_BOOTSTRAP_ATTEMPT=0"
:allocate_host
set /a "PSYCOLAB_BOOTSTRAP_ATTEMPT+=1"
set "PSYCOLAB_NATIVE_DIR=%TEMP%\PsyCoLab-launch-%RANDOM%-%RANDOM%-%PSYCOLAB_BOOTSTRAP_ATTEMPT%"
mkdir "%PSYCOLAB_NATIVE_DIR%" >nul 2>&1
if not errorlevel 1 goto host_owned
if %PSYCOLAB_BOOTSTRAP_ATTEMPT% LSS 32 goto allocate_host
set "PSYCOLAB_BOOTSTRAP_LOG=No private temporary directory could be created under %TEMP%."
goto bootstrap_failed
:host_owned
set "PSYCOLAB_NATIVE_HOST=%PSYCOLAB_NATIVE_DIR%\PsyCoLabStartup.exe"
set "PSYCOLAB_BOOTSTRAP_LOG=%PSYCOLAB_NATIVE_DIR%\bootstrap.log"
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /codepage:65001 /target:winexe /platform:x64 /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll /r:Microsoft.CSharp.dll /out:"%PSYCOLAB_NATIVE_HOST%" "%~2\packaging\windows\GuidedSetup.cs" >"%PSYCOLAB_BOOTSTRAP_LOG%" 2>&1
if errorlevel 1 goto bootstrap_failed
"%PSYCOLAB_NATIVE_HOST%" %*
set "PSYCOLAB_NATIVE_RESULT=%ERRORLEVEL%"
if not "%PSYCOLAB_NATIVE_RESULT%"=="0" exit /b %PSYCOLAB_NATIVE_RESULT%
rem Only our atomically claimed files; never remove an occupied candidate or
rem recursively delete a directory. Preserve failed attempts and their reports.
del /q "%PSYCOLAB_NATIVE_HOST%" "%PSYCOLAB_BOOTSTRAP_LOG%" >nul 2>&1
rmdir "%PSYCOLAB_NATIVE_DIR%" >nul 2>&1
exit /b %PSYCOLAB_NATIVE_RESULT%
:bootstrap_failed
rem Static native fallback, without script-file policy bypass or evaluated input.
powershell.exe -NoLogo -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show(('PsyCoLab startup recovery could not open. Nothing was installed or repaired. Ask the administrator to restore the reviewed launcher files and Windows .NET Framework support. Bootstrap report: '+[Environment]::GetEnvironmentVariable('PSYCOLAB_BOOTSTRAP_LOG')), 'PsyCoLab startup')"
echo PsyCoLab native startup is unavailable. Administrator report: "%PSYCOLAB_BOOTSTRAP_LOG%"
exit /b 1
