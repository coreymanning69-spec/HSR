@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Running the full HSR systems check from:
cd
echo.
call "%~dp0tools\run_python.bat"
"%PY%" hsr_full_check.py
echo.
echo Exit code: %errorlevel%
echo.
pause
