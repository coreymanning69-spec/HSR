@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Running hollowstar_host.py local-check from:
cd
echo.
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" hollowstar_host.py local-check
) else if exist "%SystemRoot%\py.exe" (
    "%SystemRoot%\py.exe" hollowstar_host.py local-check
) else (
    python hollowstar_host.py local-check
)
echo.
echo Exit code: %errorlevel%
echo.
pause
