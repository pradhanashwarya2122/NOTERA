@echo off
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
echo Pulling your latest notes from the private notes repo (a GitHub sign-in may open the first time)...
python app.py --sync-once
start "" http://127.0.0.1:5151/
python app.py
