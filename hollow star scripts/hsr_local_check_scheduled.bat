@echo off
REM Unattended local-check / handshake refresh for Task Scheduler.
REM Same interpreter resolution as the other launchers; no pause, logs to .local.
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set "LOG=%~dp0.local\hsr_local_check.log"
if not exist "%~dp0.local" mkdir "%~dp0.local"
echo. >> "%LOG%"
echo ==== local-check %DATE% %TIME% ==== >> "%LOG%"
call "%~dp0tools\run_python.bat"
"%PY%" hollowstar_host.py local-check >> "%LOG%" 2>&1
echo exit code: %errorlevel% >> "%LOG%"
exit /b %errorlevel%
