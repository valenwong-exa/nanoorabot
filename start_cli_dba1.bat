@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "WEBUI_ROOT=%ROOT%\nanobot-webui-main2.0"
set "NANOBOT_ROOT=%ROOT%\nanobot-main3.0"
set "CONFIG=%ROOT%\runtime\config.webui.json"
if not defined WORKSPACE (
    if exist "%ROOT%\dba1" (
        set "WORKSPACE=%ROOT%\dba1"
    ) else if exist "%ROOT%\workspace" (
        set "WORKSPACE=%ROOT%\workspace"
    ) else if exist "%ROOT%\runtime\workspace\dba1" (
        set "WORKSPACE=%ROOT%\runtime\workspace\dba1"
    )
)
if not defined PYTHON_EXE set "PYTHON_EXE=%WEBUI_ROOT%\.venv\Scripts\python.exe"

if not exist "%NANOBOT_ROOT%" (
    echo nanobot-main3.0 root not found: "%NANOBOT_ROOT%"
    goto :error
)

if not exist "%PYTHON_EXE%" (
    echo Python executable not found: "%PYTHON_EXE%"
    goto :error
)

if not exist "%CONFIG%" (
    echo config file not found: "%CONFIG%"
    goto :error
)

if not defined WORKSPACE (
    echo Workspace is not configured.
    echo Please set WORKSPACE before running this script, for example:
    echo   set "WORKSPACE=D:\your-workspace"
    goto :error
)

if not exist "%WORKSPACE%" (
    echo Workspace not found: "%WORKSPACE%"
    goto :error
)

cd /d "%NANOBOT_ROOT%"
set "PYTHONPATH=%NANOBOT_ROOT%;%PYTHONPATH%"

if "%~1"=="" (
    echo Starting nanobot-main3.0 CLI with config "%CONFIG%" and workspace "%WORKSPACE%"...
    "%PYTHON_EXE%" -m nanobot agent --config "%CONFIG%" --workspace "%WORKSPACE%"
    exit /b %errorlevel%
)

echo Starting nanobot-main3.0 CLI with extra args: %*
"%PYTHON_EXE%" -m nanobot agent --config "%CONFIG%" --workspace "%WORKSPACE%" %*
exit /b %errorlevel%

:error
exit /b 1

