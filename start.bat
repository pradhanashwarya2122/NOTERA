@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Notera

rem --- colours (Windows 10 and newer) ---
for /f %%a in ('echo prompt $E^| cmd') do set "ESC=%%a"
set "C1=%ESC%[38;5;75m"
set "C2=%ESC%[38;5;141m"
set "C3=%ESC%[38;5;213m"
set "DIM=%ESC%[90m"
set "OFF=%ESC%[0m"

rem --- a random logo each launch ---
set /a LOGO=%random% %% 3
cls
echo.
if "%LOGO%"=="0" goto logo0
if "%LOGO%"=="1" goto logo1
goto logo2

:logo0
echo %C1%    _   _       _                  %OFF%
echo %C1%   ^| \ ^| ^| ___ ^| ^|_ ___ _ __ __ _  %OFF%
echo %C2%   ^|  \^| ^|/ _ \^| __/ _ \ '__/ _` ^| %OFF%
echo %C2%   ^| ^|\  ^| (_) ^| ^|^|  __/ ^| ^| (_^| ^| %OFF%
echo %C3%   ^|_^| \_^|\___/ \__\___^|_^|  \__,_^| %OFF%
goto logodone

:logo1
echo %C1%         .-"""-.        %OFF%
echo %C1%        / .===. \       %OFF%
echo %C2%        \/ 6 6 \/       %OFF%
echo %C2%        ( \___/ )       %OFF%
echo %C3%     ___ooo___ooo___    %OFF%
echo %C3%       N O T E R A      %OFF%
goto logodone

:logo2
echo %C1%      +--------------+  %OFF%
echo %C1%      ^|  *  *  *  *  ^|  %OFF%
echo %C2%      ^|  N O T E R A ^|  %OFF%
echo %C2%      ^|  ~~~~~~~~~~  ^|  %OFF%
echo %C3%      +--------------+  %OFF%
goto logodone

:logodone
echo %DIM%        your notes, calm and fast%OFF%
echo.

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

rem --- already running? just open it ---
powershell -NoProfile -Command "try{(New-Object Net.Sockets.TcpClient('127.0.0.1',5151)).Close();exit 0}catch{exit 1}" >nul 2>nul
if not errorlevel 1 (
  echo  %C1%Notera is already running. Opening it...%OFF%
  start "" http://127.0.0.1:5151/
  timeout /t 2 >nul
  exit /b 0
)

rem --- first run: private virtual environment so nothing touches your system Python ---
if not exist ".venv\Scripts\python.exe" (
  echo  Setting up Notera for the first time, this takes a minute...
  %PY% -m venv .venv
  if errorlevel 1 ( echo  Could not create the environment. & pause & exit /b 1 )
)
".venv\Scripts\python.exe" -c "import flask" >nul 2>nul
if errorlevel 1 (
  echo  Installing what Notera needs...
  ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
  if errorlevel 1 ( echo  Could not install requirements. Check your internet connection. & pause & exit /b 1 )
)

rem --- a short loading bar ---
set "BAR="
<nul set /p "=%DIM% starting %OFF%"
for /l %%i in (1,1,24) do (
  <nul set /p "=%C2%#%OFF%"
  ping -n 1 -w 25 127.0.0.1 >nul
)
echo.
echo.

".venv\Scripts\python.exe" app.py --open
if errorlevel 1 pause
