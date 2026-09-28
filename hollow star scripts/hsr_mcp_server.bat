@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
call "%~dp0tools\run_python.bat"
"%PY%" hsr_mcp_server.py
exit /b %errorlevel%
