@echo off
setlocal

set "ROOT=E:\nanobot-main\nanobot-webui-main"
set "WEB=%ROOT%\web"
set "WEB_DIST=%WEB%\dist"
set "SERVER_DIST=%ROOT%\webui\web\dist"
set "CONFIG=%ROOT%\runtime\config.webui.json"
set "WORKSPACE=E:\nanobot-main\dba1"
set "PORT=18780"

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
start "AI System Agent WebUI" "%ROOT%\.venv\Scripts\nanobot-webui.exe" --host 127.0.0.1 --port %PORT% --workspace "%WORKSPACE%" --config "%CONFIG%" --webui-only --log-level INFO

echo Done. Open http://127.0.0.1:%PORT%/
exit /b 0

:error
echo Failed to build or sync the WebUI.
exit /b 1
