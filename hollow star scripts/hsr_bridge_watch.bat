@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Starting the HSR phone-bridge watcher from:
cd
echo.
echo Leave this window open while you want to play from your phone.
echo Ctrl+C or close this window to stop it.
echo.
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" hsr_bridge_watch.py
) else if exist "%SystemRoot%\py.exe" (
    "%SystemRoot%\py.exe" hsr_bridge_watch.py
) else (
    python hsr_bridge_watch.py
)
echo.
echo Exit code: %errorlevel%
echo.
pause
