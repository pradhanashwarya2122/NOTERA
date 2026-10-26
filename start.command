#!/bin/bash
# Double-click this file on a Mac (or run ./start.command on Linux).
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo " Notera needs Python 3.10 or newer, and it was not found."
  echo " Opening the download page. Install it, then double-click this file again."
  open "https://www.python.org/downloads/" 2>/dev/null || xdg-open "https://www.python.org/downloads/" 2>/dev/null
  read -n 1 -s -r -p "Press any key to close"
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo " Setting up Notera for the first time, this takes a minute..."
  python3 -m venv .venv || { echo " Could not create the environment."; read -n 1 -s -r -p "Press any key to close"; exit 1; }
fi
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt || { echo " Could not install requirements. Check your internet connection."; read -n 1 -s -r -p "Press any key to close"; exit 1; }

exec .venv/bin/python app.py --open
