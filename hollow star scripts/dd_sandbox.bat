@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Hollow Star deterministic D&D sandbox
echo Type: sandbox RUN_ID SEED SELECTOR   (for example: sandbox tavern-1 brave-seed divine:Doran)
echo Then use: say hello to Mara, insult the bartender, attack Brann, light the oil lamp, or go east
echo.
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" play.py %*
) else if exist "%SystemRoot%\py.exe" (
    "%SystemRoot%\py.exe" play.py %*
) else (
    python play.py %*
)
if errorlevel 1 pause
