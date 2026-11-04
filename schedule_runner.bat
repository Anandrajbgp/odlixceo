@echo off
:: schedule_runner.bat - Windows Task Scheduler entry point
:: Register this file in Task Scheduler with a Daily trigger at 09:30 AM.
:: Set the PIPELINE_GOAL environment variable in the task settings if desired.

setlocal

:: Resolve the directory containing this batch file.
set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"

:: Fallback to system python if venv is absent.
if not exist "%VENV_PY%" (
    set "VENV_PY=python"
)

echo [%DATE% %TIME%] ops_scheduler starting... >> "%SCRIPT_DIR%scheduler.log"
"%VENV_PY%" "%SCRIPT_DIR%ops_scheduler.py" >> "%SCRIPT_DIR%scheduler.log" 2>&1
echo [%DATE% %TIME%] ops_scheduler finished (exit code %ERRORLEVEL%). >> "%SCRIPT_DIR%scheduler.log"

endlocal
