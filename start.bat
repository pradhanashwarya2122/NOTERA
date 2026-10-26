@echo off
setlocal
cd /d "%~dp0"
title Notera

rem --- find Python 3 ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo.
  echo  Notera needs Python 3.10 or newer, and it was not found.
  echo  Opening the download page. Install it ^(tick "Add python.exe to PATH"^), then run this file again.
  start "" https://www.python.org/downloads/
  pause
  exit /b 1
)

rem --- first run: private virtual environment so nothing touches your system Python ---
if not exist ".venv\Scripts\python.exe" (
  echo  Setting up Notera for the first time, this takes a minute...
  %PY% -m venv .venv
  if errorlevel 1 ( echo  Could not create the environment. & pause & exit /b 1 )
)
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 ( echo  Could not install requirements. Check your internet connection. & pause & exit /b 1 )

".venv\Scripts\python.exe" app.py --open
if errorlevel 1 pause
