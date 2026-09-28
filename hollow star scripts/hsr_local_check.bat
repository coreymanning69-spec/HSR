@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Running hollowstar_host.py local-check from:
cd
echo.
call "%~dp0tools\run_python.bat"
"%PY%" hollowstar_host.py local-check
echo.
echo Exit code: %errorlevel%
echo.
pause
