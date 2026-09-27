@echo off
REM Unattended phone-bridge watcher launch for Task Scheduler.
REM No pause; logs to .local; exits with the watcher's real exit code so
REM Task Scheduler's restart-on-failure can detect a crash and relaunch it.
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set "LOG=%~dp0.local\hsr_bridge_watch_scheduled.log"
if not exist "%~dp0.local" mkdir "%~dp0.local"
echo. >> "%LOG%"
echo ==== watcher launch %DATE% %TIME% ==== >> "%LOG%"
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" hsr_bridge_watch.py >> "%LOG%" 2>&1
) else if exist "%SystemRoot%\py.exe" (
    "%SystemRoot%\py.exe" hsr_bridge_watch.py >> "%LOG%" 2>&1
) else (
    python hsr_bridge_watch.py >> "%LOG%" 2>&1
)
echo exit code: %errorlevel% >> "%LOG%"
exit /b %errorlevel%
