@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "WEB_DIR=%ROOT_DIR%web"
set "PORT=18890"
set "URL=http://127.0.0.1:%PORT%/"
set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"

if not exist "%WEB_DIR%\index.html" (
    echo Gallery page not found: %WEB_DIR%\index.html
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [1/3] Stopping any process listening on port %PORT%...
powershell -NoProfile -Command "$port=%PORT%; $pids=Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($pids) { $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; Write-Output ('Stopped PID(s): ' + ($pids -join ', ')) } else { Write-Output 'No process listening on target port.' }"
if errorlevel 1 (
    echo Failed while stopping existing port listener.
    exit /b 1
)

echo [2/3] Opening browser: %URL%
start "" "%URL%"

echo [3/3] Starting static gallery server from %WEB_DIR%...
echo Press Ctrl+C to stop the server.
cd /d "%WEB_DIR%"
call "%PYTHON_EXE%" -m http.server %PORT%
exit /b %errorlevel%
