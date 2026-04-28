@echo off
setlocal

set "NANOBOT_ROOT=E:\nanobot-main\nanobot-015post1"
set "WORKSPACE_ROOT=E:\nanobot-main\dba1"
set "WEBUI_RUNTIME_CONFIG=E:\nanobot-main\nanobot-webui-main\runtime\config.webui.json"
set "NANOBOT_VENV=%NANOBOT_ROOT%\.venv"
set "NANOBOT_PYTHON=%NANOBOT_VENV%\Scripts\python.exe"

if not exist "%WORKSPACE_ROOT%" (
    echo Workspace not found: %WORKSPACE_ROOT%
    exit /b 1
)

if not exist "%WEBUI_RUNTIME_CONFIG%" (
    echo WebUI runtime config not found: %WEBUI_RUNTIME_CONFIG%
    exit /b 1
)

echo [1/3] Preparing nanobot virtual environment...
if not exist "%NANOBOT_PYTHON%" (
    where uv >nul 2>nul
    if %errorlevel%==0 (
        call uv venv "%NANOBOT_VENV%"
    ) else (
        call python -m venv "%NANOBOT_VENV%"
    )
    if errorlevel 1 goto :error
)

echo [2/3] Installing local nanobot 015post source...
cd /d "%NANOBOT_ROOT%"
where uv >nul 2>nul
if %errorlevel%==0 (
    call uv pip install --python "%NANOBOT_PYTHON%" -e "%NANOBOT_ROOT%"
) else (
    call "%NANOBOT_PYTHON%" -m pip install -e "%NANOBOT_ROOT%"
)
if errorlevel 1 goto :error

echo [3/3] Starting nanobot CLI with workspace %WORKSPACE_ROOT%...
echo Using config: %WEBUI_RUNTIME_CONFIG%
cd /d "%NANOBOT_ROOT%"
call "%NANOBOT_PYTHON%" -m nanobot agent -w "%WORKSPACE_ROOT%" -c "%WEBUI_RUNTIME_CONFIG%"
exit /b %errorlevel%

:error
echo Failed to start nanobot CLI.
exit /b 1
