@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
for %%I in ("%ROOT%\..\nanobot-main2.2") do set "NANOBOT_ROOT=%%~fI"
set "CONFIG=%ROOT%\runtime\config.webui.json"
set "WORKSPACE=E:\nanobot-main\dba1"
set "NANOBOT_EXE=%NANOBOT_ROOT%\.venv\Scripts\nanobot.exe"

if not exist "%NANOBOT_ROOT%" (
    echo nanobot-main2.2 root not found: "%NANOBOT_ROOT%"
    goto :error
)

if not exist "%NANOBOT_EXE%" (
    echo nanobot executable not found: "%NANOBOT_EXE%"
    goto :error
)

if not exist "%CONFIG%" (
    echo config file not found: "%CONFIG%"
    goto :error
)

cd /d "%NANOBOT_ROOT%"

if "%~1"=="" (
    echo Starting nanobot-main2.2 CLI with config "%CONFIG%" and workspace "%WORKSPACE%"...
    "%NANOBOT_EXE%" agent --config "%CONFIG%" --workspace "%WORKSPACE%"
    exit /b %errorlevel%
)

echo Starting nanobot-main2.2 CLI with extra args: %*
"%NANOBOT_EXE%" agent --config "%CONFIG%" --workspace "%WORKSPACE%" %*
exit /b %errorlevel%

:error
exit /b 1


