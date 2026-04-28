@echo off
setlocal

set "NANOBOT_015POST_ROOT=E:\nanobot-main\nanobot-015post1"
set "WEBUI_ROOT=E:\nanobot-main\nanobot-webui-main"
set "WEBUI_VENV=%WEBUI_ROOT%\.venv"
set "WEBUI_PYTHON=%WEBUI_VENV%\Scripts\python.exe"
set "WEBUI_EXE=%WEBUI_VENV%\Scripts\nanobot-webui.exe"

echo [1/4] Preparing WebUI virtual environment...
if not exist "%WEBUI_PYTHON%" (
    where uv >nul 2>nul
    if %errorlevel%==0 (
        call uv venv "%WEBUI_VENV%"
    ) else (
        call python -m venv "%WEBUI_VENV%"
    )
    if errorlevel 1 goto :error
)

echo [2/4] Stopping existing WebUI process...
powershell -NoProfile -Command "$port=18780; $pids=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($pids) { $pids | ForEach-Object { Stop-Process -Id $_ -Force }; Write-Output ('Stopped PID(s): ' + ($pids -join ', ')) } else { Write-Output 'No process listening on port 18780' }"
powershell -NoProfile -Command "$exe='%WEBUI_EXE%'; Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -eq $exe } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo [3/4] Binding WebUI to local nanobot 015post source...
where uv >nul 2>nul
if %errorlevel%==0 (
    call uv pip install --python "%WEBUI_PYTHON%" -e "%WEBUI_ROOT%"
    if errorlevel 1 goto :error
    call uv pip install --python "%WEBUI_PYTHON%" -e "%NANOBOT_015POST_ROOT%"
) else (
    call "%WEBUI_PYTHON%" -m pip install -e "%WEBUI_ROOT%"
    if errorlevel 1 goto :error
    call "%WEBUI_PYTHON%" -m pip install -e "%NANOBOT_015POST_ROOT%"
)
if errorlevel 1 goto :error

echo [4/4] Starting 015post WebUI...
cd /d "%WEBUI_ROOT%"
call "%WEBUI_ROOT%\start_webui_dba1.bat"
exit /b %errorlevel%

:error
echo Failed to start WebUI bound to local nanobot 015post source.
exit /b 1
