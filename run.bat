@echo off
title Bot Pengingat Classroom ITATS
cd /d "%~dp0"

echo ====================================================
echo      Menjalankan Bot Pengingat Classroom ITATS      
echo ====================================================
echo.

if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" bot.py
) else (
    python bot.py
)

pause
