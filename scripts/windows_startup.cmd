@echo off
setlocal EnableExtensions
rem Internal bootstrap shared by normal launch and explicit recovery. No Python.
if not "%~1"=="--source" if not "%~1"=="--recover" exit /b 2
set "PSYCOLAB_NATIVE_HOST=%TEMP%\PsyCoLab-launch-%RANDOM%-%RANDOM%.exe"
set "PSYCOLAB_BOOTSTRAP_LOG=%PSYCOLAB_NATIVE_HOST%.log"
if exist "%PSYCOLAB_NATIVE_HOST%" goto bootstrap_failed
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /codepage:65001 /target:winexe /platform:x64 /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll /r:Microsoft.CSharp.dll /out:"%PSYCOLAB_NATIVE_HOST%" "%~2\packaging\windows\GuidedSetup.cs" >"%PSYCOLAB_BOOTSTRAP_LOG%" 2>&1
if errorlevel 1 goto bootstrap_failed
"%PSYCOLAB_NATIVE_HOST%" %*
exit /b %ERRORLEVEL%
:bootstrap_failed
rem Static native fallback, without script-file policy bypass or evaluated input.
powershell.exe -NoLogo -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show(('PsyCoLab startup recovery could not open. Nothing was installed or repaired. Ask the administrator to restore the reviewed launcher files and Windows .NET Framework support. Bootstrap report: '+[Environment]::GetEnvironmentVariable('PSYCOLAB_BOOTSTRAP_LOG')), 'PsyCoLab startup')"
echo PsyCoLab native startup is unavailable. Administrator report: "%PSYCOLAB_BOOTSTRAP_LOG%"
exit /b 1
