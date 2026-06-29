@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "WEBUI_ROOT=%ROOT%\nanobot-webui-main2.0"
set "WEB=%WEBUI_ROOT%\web"
set "WEB_DIST=%WEB%\dist"
set "SERVER_WEB=%WEBUI_ROOT%\webui\web"
set "SERVER_DIST=%SERVER_WEB%\dist"
set "NANOBOT_ROOT=%ROOT%\nanobot-main2.2"
set "CONFIG=%ROOT%\runtime\config.webui.json"
set "ORACLE_CONFIG=%ROOT%\runtime\oracle_config.json"
set "TOOL_POLICY=%ROOT%\runtime\tool_policy.json"
set "LOG_DIR=%ROOT%\runtime\logs"
set "START_LOG=%LOG_DIR%\start_webui_dba1.log"
if not defined WORKSPACE (
    if exist "%ROOT%\dba1" (
        set "WORKSPACE=%ROOT%\dba1"
    ) else if exist "%ROOT%\workspace" (
        set "WORKSPACE=%ROOT%\workspace"
    ) else if exist "%ROOT%\runtime\workspace\dba1" (
        set "WORKSPACE=%ROOT%\runtime\workspace\dba1"
    )
)
if not defined PORT set "PORT=18780"
set "PYTHON_EXE=%NANOBOT_ROOT%\.venv\Scripts\python.exe"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
call :log "==== start_webui_dba1 ===="
call :log "ROOT=%ROOT%"
call :log "WEBUI_ROOT=%WEBUI_ROOT%"
call :log "WORKSPACE=%WORKSPACE%"
call :log "PORT=%PORT%"
call :log "PYTHON=%PYTHON_EXE%"
call :log "CONFIG=%CONFIG%"
call :log "ORACLE_CONFIG=%ORACLE_CONFIG%"
call :log "TOOL_POLICY=%TOOL_POLICY%"

if not exist "%WEB%\package.json" (
    echo Frontend project not found: "%WEB%\package.json"
    goto :error
)

if not exist "%SERVER_WEB%" (
    echo Server static directory not found: "%SERVER_WEB%"
    goto :error
)

if not exist "%NANOBOT_ROOT%" (
    echo nanobot-main2.2 root not found: "%NANOBOT_ROOT%"
    goto :error
)

if not exist "%PYTHON_EXE%" (
    echo Python executable not found: "%PYTHON_EXE%"
    goto :error
)

if not exist "%CONFIG%" (
    echo Config file not found: "%CONFIG%"
    goto :error
)

if not exist "%ORACLE_CONFIG%" (
    echo Oracle config file not found: "%ORACLE_CONFIG%"
    goto :error
)

if not exist "%TOOL_POLICY%" (
    echo Tool policy file not found: "%TOOL_POLICY%"
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

echo [1/4] Checking port %PORT%...
call :log "[1/4] Checking port %PORT%"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    echo Killing PID %%P on port %PORT%...
    call :log "Killing PID %%P on port %PORT%"
    taskkill /PID %%P /F >nul 2>&1
)

echo [2/4] Building frontend...
call :log "[2/4] Building frontend"
cd /d "%WEB%"
call npm run build
if errorlevel 1 goto :error
if not exist "%WEB_DIST%\index.html" (
    echo Frontend build output not found: "%WEB_DIST%\index.html"
    goto :error
)

echo [3/4] Syncing static assets...
call :log "[3/4] Syncing static assets"
if not exist "%SERVER_WEB%" mkdir "%SERVER_WEB%"
robocopy "%WEB_DIST%" "%SERVER_DIST%" /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :error
if not exist "%SERVER_DIST%\index.html" (
    echo Server static output not found: "%SERVER_DIST%\index.html"
    goto :error
)

echo [4/4] Starting WebUI...
echo --oracle-audit --oracle-memory not enabled.
call :log "[4/4] Starting WebUI"
call :log "NANOBOT_ROOT=%NANOBOT_ROOT%"
cd /d "%WEBUI_ROOT%"
start "AI System Agent WebUI 2.2" cmd /d /k ""%PYTHON_EXE%" -m webui --host 0.0.0.0 --port %PORT% --workspace "%WORKSPACE%" --config "%CONFIG%" --log-level DEBUG --oracle-config "%ORACLE_CONFIG%" --tool-policy "%TOOL_POLICY%" 
set "PORT_READY="
for /l %%I in (1,1,15) do (
    timeout /t 1 /nobreak >nul
    netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
    if not errorlevel 1 (
        set "PORT_READY=1"
        goto :port_ready
    )
)

if not defined PORT_READY (
    call :log "WebUI is not listening on port %PORT% after 15 seconds"
    echo WebUI did not start successfully. Check logs:
    echo   "%START_LOG%"
    echo   and the visible "AI System Agent WebUI 2.2" console window.
    goto :error
)

:port_ready
call :log "WebUI is listening on port %PORT%"

echo Done. Open http://127.0.0.1:%PORT%/
exit /b 0

:error
call :log "Failed to start WebUI"
echo Failed to build or sync the WebUI.
exit /b 1

:log
echo [%date% %time%] %~1>>"%START_LOG%"
exit /b 0
