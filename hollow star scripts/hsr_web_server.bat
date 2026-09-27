@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (set "PY=%CODEX_PY%") else if exist "%SystemRoot%\py.exe" (set "PY=%SystemRoot%\py.exe") else (set "PY=python")
"%PY%" hollowstar_web_server.py
