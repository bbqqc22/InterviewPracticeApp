@echo off
REM Double-click this file to start the app. First run installs what it needs (internet required once).
cd /d "%~dp0"
title Petrophysicist Interviewer Pro

set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY ( where python >nul 2>nul && set PY=python )
if not defined PY (
  if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set PY="%LOCALAPPDATA%\Python\bin\python.exe"
  )
)
if not defined PY (
  echo Python was not found. Install it from https://www.python.org/downloads/
  echo IMPORTANT: tick "Add python.exe to PATH" on the first installer screen, then double-click this file again.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo Setting up for the first time - this takes a minute or two...
  %PY% -m venv .venv
  if errorlevel 1 ( echo Could not create the environment. & pause & exit /b 1 )
)
call ".venv\Scripts\activate.bat"
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Installing packages failed. Check your internet connection and run this file again.
  pause
  exit /b 1
)

echo Starting the app. Your browser will open. Close this window to stop the app.
python -m streamlit run interviewer_pro_needApassword.py --browser.gatherUsageStats false --server.address 127.0.0.1
echo.
echo The app stopped. If you saw an error above, copy it and paste it to Claude.
pause
