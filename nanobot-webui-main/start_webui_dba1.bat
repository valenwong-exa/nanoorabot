@echo off
setlocal

set "ROOT=D:\nanoorabot-main\nanobot-webui-main"
set "WEB=%ROOT%\web"
set "WEB_DIST=%WEB%\dist"
set "SERVER_DIST=%ROOT%\webui\web\dist"
set "CONFIG=D:\nanoorabot-main\nanobot-runtime\config.webui.json"
set "WORKSPACE=D:\nanoorabot-main\nanobot-runtime\workspace\dba1"
set "PORT=18780"
set "CONDA_ENV=nanobot-webui"

echo [1/4] Building frontend...
cd /d "%WEB%"
call npm run build
if errorlevel 1 goto :error

echo [2/4] Syncing static assets...
if exist "%SERVER_DIST%" rmdir /s /q "%SERVER_DIST%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -Recurse -Force '%WEB_DIST%' '%ROOT%\webui\web\'"
if errorlevel 1 goto :error

echo [3/4] Checking port %PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    echo Killing PID %%P on port %PORT%...
    taskkill /PID %%P /F >nul 2>&1
)

echo [4/4] Starting WebUI...
cd /d "%ROOT%"
set "CONDA_BAT="
if defined CONDA_EXE set "CONDA_BAT=%CONDA_EXE%"
if not defined CONDA_BAT (
    for /f "delims=" %%I in ('where conda.bat 2^>nul') do if not defined CONDA_BAT set "CONDA_BAT=%%I"
)
if not defined CONDA_BAT (
    for /f "delims=" %%I in ('where conda 2^>nul') do if not defined CONDA_BAT set "CONDA_BAT=%%I"
)
if not defined CONDA_BAT (
    echo Failed to find conda. Please make sure conda is installed and available in PATH.
    goto :error
)

call "%CONDA_BAT%" activate "%CONDA_ENV%"
if errorlevel 1 (
    echo Failed to activate conda environment "%CONDA_ENV%".
    goto :error
)

start "AI System Agent WebUI" "%CONDA_PREFIX%\Scripts\nanobot-webui.exe" --host 127.0.0.1 --port %PORT% --workspace "%WORKSPACE%" --config "%CONFIG%" --webui-only --log-level INFO

echo Done. Open http://127.0.0.1:%PORT%/
exit /b 0

:error
echo Failed to build or sync the WebUI.
exit /b 1
