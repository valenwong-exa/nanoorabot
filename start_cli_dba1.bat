@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "CONFIG=%ROOT%\runtime\config.webui.json"
set "WORKSPACE=E:\nanobot-main\dba1"
set "NANOBOT_EXE=%ROOT%\.venv\Scripts\nanobot.exe"

if not exist "%NANOBOT_EXE%" (
    echo nanobot executable not found: "%NANOBOT_EXE%"
    goto :error
)

if not exist "%CONFIG%" (
    echo config file not found: "%CONFIG%"
    goto :error
)

cd /d "%ROOT%"

if "%~1"=="" (
    echo Starting nanobot CLI with config "%CONFIG%" and workspace "%WORKSPACE%"...
    "%NANOBOT_EXE%" agent --config "%CONFIG%" --workspace "%WORKSPACE%"
    exit /b %errorlevel%
)

echo Starting nanobot CLI with extra args: %*
"%NANOBOT_EXE%" agent --config "%CONFIG%" --workspace "%WORKSPACE%" %*
exit /b %errorlevel%

:error
exit /b 1


