@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" hsr_mcp_server.py
) else if exist "%SystemRoot%\py.exe" (
    "%SystemRoot%\py.exe" hsr_mcp_server.py
) else (
    python hsr_mcp_server.py
)
exit /b %errorlevel%
