@echo off
setlocal
call "%~dp0tools\run_python.bat"
"%PY%" "%~dp0play.py" %*
if errorlevel 1 pause
