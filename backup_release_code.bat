@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0.") do set "BACKUP_BASE=%%~fI"
for %%I in ("%BACKUP_BASE%\..") do set "ROOT=%%~fI"
set "SCRIPT_PATH=%~f0"
set "BOT30_SRC=%ROOT%\nanobot-main3.0"
set "WEBUI20_SRC=%ROOT%\nanobot-webui-main2.0"
set "SENSEVOICE_SRC=%ROOT%\SenseVoice-main"
set "WEBUI_RUNTIME_SRC=%WEBUI20_SRC%\runtime"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"

if not "%~1"=="" (
    set "TARGET=%BACKUP_BASE%\%~1"
) else (
    set "TARGET=%BACKUP_BASE%\release_3_0_!STAMP!"
)
set "RUNTIME_TARGET=%TARGET%\runtime"
set "LEGACY_CORE_TARGET=%TARGET%\nanobot-main2.2"
set "LEGACY_CORE_ARCHIVE=%BACKUP_BASE%\legacy_nanobot-main2.2_!STAMP!"

echo Creating 3.0 release code backup...
echo Target: %TARGET%

if not exist "%BACKUP_BASE%" mkdir "%BACKUP_BASE%"
if not exist "%TARGET%" mkdir "%TARGET%"

if not exist "%BOT30_SRC%" (
    echo Missing source directory: %BOT30_SRC%
    exit /b 1
)

if not exist "%WEBUI20_SRC%" (
    echo Missing source directory: %WEBUI20_SRC%
    exit /b 1
)

if not exist "%SENSEVOICE_SRC%" (
    echo Missing source directory: %SENSEVOICE_SRC%
    exit /b 1
)

if not exist "%WEBUI_RUNTIME_SRC%" (
    echo Missing runtime directory: %WEBUI_RUNTIME_SRC%
    exit /b 1
)

echo Copying backup script...
copy /Y "%SCRIPT_PATH%" "%TARGET%\" >nul

echo Syncing nanobot-main3.0 source...
robocopy "%BOT30_SRC%" "%TARGET%\nanobot-main3.0" /MIR /XJ ^
    /XD ".git" ".venv" "node_modules" "__pycache__" ".pytest_cache" ".ruff_cache" ".mypy_cache" ".cache" ".idea" ".vscode" "coverage" "build" "dist" ".dbg" ^
        "nanobot_ai.egg-info" "nanobot.egg-info" ^
    /XF "*.pyc" "*.pyo" "*.log" ".DS_Store" "Thumbs.db" "*.tsbuildinfo" ^
    /R:1 /W:1 /NDL /NFL /NJH /NJS
if errorlevel 8 goto :copy_error

echo Syncing nanobot-webui-main2.0 source...
robocopy "%WEBUI20_SRC%" "%TARGET%\nanobot-webui-main2.0" /MIR /XJ ^
    /XD ".git" ".venv" "node_modules" "__pycache__" ".pytest_cache" ".ruff_cache" ".mypy_cache" ".cache" ".idea" ".vscode" "coverage" "build" "dist" ".dbg" ^
        "runtime" "metadata_cache" "nanobot_webui.egg-info" ^
        "web\dist" "webui\web\dist" ^
    /XF "*.pyc" "*.pyo" "*.log" ".DS_Store" "Thumbs.db" "*.tsbuildinfo" ^
    /R:1 /W:1 /NDL /NFL /NJH /NJS
if errorlevel 8 goto :copy_error

echo Syncing SenseVoice-main source...
robocopy "%SENSEVOICE_SRC%" "%TARGET%\SenseVoice-main" /MIR /XJ ^
    /XD ".git" ".venv" "node_modules" "__pycache__" ".pytest_cache" ".ruff_cache" ".mypy_cache" ".cache" ".idea" ".vscode" "coverage" "build" "dist" ".dbg" ^
    /XF "*.pyc" "*.pyo" "*.log" ".DS_Store" "Thumbs.db" ^
    /R:1 /W:1 /NDL /NFL /NJH /NJS
if errorlevel 8 goto :copy_error

echo Copying and sanitizing runtime config files...
if not exist "%RUNTIME_TARGET%" mkdir "%RUNTIME_TARGET%"
for %%F in (
    "config.webui.json"
    "dangerous_tool_policy.json"
    "oracle_config.json"
    "tool_policy.json"
    "webui_config.json"
) do (
    if not exist "%WEBUI_RUNTIME_SRC%\%%~F" (
        echo Missing runtime file: %WEBUI_RUNTIME_SRC%\%%~F
        exit /b 1
    )
    copy /Y "%WEBUI_RUNTIME_SRC%\%%~F" "%RUNTIME_TARGET%\" >nul
    set "SANITIZE_FILE=%RUNTIME_TARGET%\%%~F"
    powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $path=$env:SANITIZE_FILE; $data=ConvertFrom-Json -InputObject (Get-Content -LiteralPath $path -Raw -Encoding UTF8); function Clear-Secrets($value) { if ($value -is [pscustomobject]) { foreach ($property in $value.PSObject.Properties) { $name=($property.Name -replace '[_-]','').ToLowerInvariant(); if (@('apikey','token','accesstoken','refreshtoken','secret','clientsecret','password','passwd','pwd','credential','privatekey') -contains $name) { $property.Value='' } else { Clear-Secrets $property.Value } } } elseif ($value -is [array]) { foreach ($item in $value) { Clear-Secrets $item } } }; Clear-Secrets $data; $json=ConvertTo-Json -InputObject $data -Depth 100; [IO.File]::WriteAllText($path, $json + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))"
    if errorlevel 1 (
        echo Failed to sanitize runtime file: %RUNTIME_TARGET%\%%~F
        exit /b 1
    )
)

if exist "%LEGACY_CORE_TARGET%" (
    echo Archiving legacy nanobot-main2.2 directory...
    if exist "%LEGACY_CORE_ARCHIVE%" (
        echo Legacy archive already exists: %LEGACY_CORE_ARCHIVE%
        exit /b 1
    )
    move "%LEGACY_CORE_TARGET%" "%LEGACY_CORE_ARCHIVE%" >nul
    if errorlevel 1 (
        echo Failed to archive legacy directory: %LEGACY_CORE_TARGET%
        exit /b 1
    )
    echo Legacy core archived at: %LEGACY_CORE_ARCHIVE%
)

echo.
echo 3.0 release code backup completed:
echo %TARGET%
exit /b 0

:copy_error
echo.
echo Backup failed during file copy.
exit /b 1
