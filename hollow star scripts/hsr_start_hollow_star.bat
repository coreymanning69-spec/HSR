@echo off
REM One-click entry point. Keeps diagnostics visible and lets the Python app
REM own clean browser/server shutdown. Unexpected failures remain inspectable.
title Hollow Star
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    set "PY=%CODEX_PY%"
) else if exist "%SystemRoot%\py.exe" (
    set "PY=%SystemRoot%\py.exe"
) else (
    set "PY=python"
)

cls
echo.
echo   ============================================================
echo                     H O L L O W   S T A R
echo   ============================================================
echo.

if /i "%~1"=="install" goto install
if /i "%~1"=="web" goto web
if /i "%~1"=="tkinter" goto tkinter
if /i "%~1"=="pygame" goto pygame
if /i "%~1"=="check" goto check

REM Normal startup is always the existing Web HSR interface. Optional
REM adapters are developer-only entry points and never start automatically.
goto web

:install
echo.
echo   Installing optional local Python libraries...
"%PY%" -m pip install -r requirements-local.txt
if errorlevel 1 (
    echo.
    echo   [ !! ] Installation failed. Review the pip output above.
    pause
    exit /b 1
)
echo.
echo   [ OK ] Optional local libraries installed.
pause
exit /b 0

:tkinter
echo.
echo   Starting Tkinter local tools...
"%PY%" run_tkinter.py
exit /b %errorlevel%

:pygame
echo.
echo   Starting Pygame local client...
"%PY%" run_pygame.py
exit /b %errorlevel%

:check
echo.
echo   Running local engine check...
if not exist ".local" mkdir ".local"
"%PY%" hollowstar_host.py local-check
pause
exit /b %errorlevel%

:web


echo   Starting up...
echo.
if not exist ".local" mkdir ".local"
"%PY%" hollowstar_host.py local-check > ".local\hsr_start_check.txt" 2>&1
if errorlevel 1 (
    echo   [ !! ]  The engine check did not pass.
    echo           Startup stopped. Run local-check and resolve the reported error.
    exit /b 1
) else (
    echo   [ OK ]  Engine checked out.
)
REM The web server skips its own duplicate local-check on first start.
set "HSR_LOCAL_CHECK_DONE=1"
echo.
echo   ============================================================
echo.
echo      HOLLOW STAR IS RUNNING
echo.
echo      Live engine readout follows below: inputs, timings, debug.
echo      Closing the game window stops everything.
echo.
echo   ============================================================
echo.

REM The web server is the one lifecycle owner. It reuses a healthy instance,
REM starts the singleton watcher, and recovers that watcher after a crash.
"%PY%" hollowstar_app.py
set "HSR_EXIT=%errorlevel%"
if not "%HSR_EXIT%"=="0" (
    echo.
    echo   [ !! ] Hollow Star stopped unexpectedly.
    echo         Review .local\logs\hsr_app.log before closing this window.
    pause
    exit /b %HSR_EXIT%
)

echo.
echo   Hollow Star has stopped. You can close this window.
echo.
exit /b 0
