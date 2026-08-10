@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
for %%I in ("%ROOT%\..") do set "RELEASE_ROOT=%%~fI"
set "NANOBOT_ROOT=%RELEASE_ROOT%\nanobot-main3.0"
if not defined CONFIG (
    if exist "%RELEASE_ROOT%\runtime\config.webui.json" (
        set "CONFIG=%RELEASE_ROOT%\runtime\config.webui.json"
    ) else (
        set "CONFIG=%ROOT%\runtime\config.webui.json"
    )
)
if not defined WORKSPACE set "WORKSPACE=%RELEASE_ROOT%\dba1"
if not defined PYTHON_EXE set "PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe"

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
