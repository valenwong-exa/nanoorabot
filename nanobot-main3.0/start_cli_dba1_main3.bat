@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
for %%I in ("%ROOT%\..\nanobot-webui-main2.0") do set "WEBUI_ROOT=%%~fI"
for %%I in ("%ROOT%\..\dba1") do set "DEFAULT_WORKSPACE=%%~fI"
if not defined PYTHON_EXE set "PYTHON_EXE=%WEBUI_ROOT%\.venv\Scripts\python.exe"
if not defined CONFIG (
    if exist "%ROOT%\..\runtime\config.webui.json" (
        for %%I in ("%ROOT%\..\runtime\config.webui.json") do set "CONFIG=%%~fI"
    ) else (
        set "CONFIG=%WEBUI_ROOT%\runtime\config.webui.json"
    )
)
if not defined WORKSPACE set "WORKSPACE=%DEFAULT_WORKSPACE%"

if not exist "%PYTHON_EXE%" (
    echo Python not found: "%PYTHON_EXE%"
    goto :error
)

if not exist "%CONFIG%" (
    echo Config file not found: "%CONFIG%"
    goto :error
)

if not exist "%WORKSPACE%" (
    echo Workspace not found: "%WORKSPACE%"
    goto :error
)

cd /d "%ROOT%"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"

if "%~1"=="" (
    echo Starting nanobot-main3.0 CLI from source with config "%CONFIG%" and workspace "%WORKSPACE%"...
    "%PYTHON_EXE%" -m nanobot.cli.commands agent --config "%CONFIG%" --workspace "%WORKSPACE%"
    exit /b %errorlevel%
)

echo Starting nanobot-main3.0 CLI from source with extra args: %*
"%PYTHON_EXE%" -m nanobot.cli.commands agent --config "%CONFIG%" --workspace "%WORKSPACE%" %*
exit /b %errorlevel%

:error
exit /b 1
