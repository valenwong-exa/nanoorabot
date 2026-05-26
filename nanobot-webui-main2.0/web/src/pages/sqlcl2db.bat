@echo off
setlocal

if "%~1"=="" (
    echo Usage:
    echo   %~nx0 connection_name
    echo.
    echo Example:
    echo   %~nx0 aidemo
    exit /b 1
)

set CONN_NAME=%~1
set SQL_FILE=%TEMP%\sqlcl_sysdate_%RANDOM%.sql

(
echo set heading off
echo set feedback off
echo set pagesize 0
echo set linesize 200
echo set sqlformat default
echo select to_char(sysdate,'YYYY-MM-DD HH24:MI:SS'^) from dual;
echo exit
) > "%SQL_FILE%"

sql -S -name %CONN_NAME% @"%SQL_FILE%"

del "%SQL_FILE%" >nul 2>nul

endlocal