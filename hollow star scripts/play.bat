@echo off
setlocal
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" "%~dp0play.py" %*
) else if exist "%SystemRoot%\py.exe" (
    "%SystemRoot%\py.exe" "%~dp0play.py" %*
) else (
    python "%~dp0play.py" %*
)
if errorlevel 1 pause
