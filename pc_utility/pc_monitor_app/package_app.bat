@echo off
chcp 65001 > nul
echo ==========================================================
echo 📦 ĐÓNG GÓI CÀI ĐẶT SMART DESK STUDIO PRO FOR WINDOWS
echo ==========================================================
cd /d "%~dp0"
python package_app.py
pause
