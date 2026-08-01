@echo off
title ESP32 CYD Smart Dashboard Studio
cd /d "%~dp0"

echo Installing / Verifying requirements...
python -m pip install -r requirements.txt

echo Starting ESP32 CYD Dashboard Studio in System Tray...
python main.py
