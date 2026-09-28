@echo off
REM Shared interpreter resolution for every HSR launcher.
REM Usage from a launcher (after its own setlocal):  call "%~dp0tools\run_python.bat"
REM Sets PY to the Codex runtime, then the py launcher, then plain python.
REM No setlocal here on purpose: PY must survive back into the caller.
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    set "PY=%CODEX_PY%"
) else if exist "%SystemRoot%\py.exe" (
    set "PY=%SystemRoot%\py.exe"
) else (
    set "PY=python"
)
exit /b 0
