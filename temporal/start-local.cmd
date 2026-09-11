@echo off
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0serve.py" %*
) else (
  python "%~dp0serve.py" %*
)
if errorlevel 1 pause
