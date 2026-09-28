@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Hollow Star deterministic D&D sandbox
echo Type: sandbox RUN_ID SEED SELECTOR   (for example: sandbox tavern-1 brave-seed divine:Doran)
echo Then use: say hello to Mara, insult the bartender, attack Brann, light the oil lamp, or go east
echo.
call "%~dp0tools\run_python.bat"
"%PY%" play.py %*
if errorlevel 1 pause
