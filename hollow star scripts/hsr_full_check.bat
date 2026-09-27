@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Running the full HSR systems check from:
cd
echo.
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" hsr_full_check.py
) else if exist "%SystemRoot%\py.exe" (
    "%SystemRoot%\py.exe" hsr_full_check.py
) else (
    python hsr_full_check.py
)
echo.
echo Exit code: %errorlevel%
echo.
pause
