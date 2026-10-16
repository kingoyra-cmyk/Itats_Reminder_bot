@echo off
title Login Otomatis Classroom ITATS
cd /d "%~dp0"

echo ====================================================
echo    LOGIN OTOMATIS CLASSROOM ITATS (AUTO-COOKIE)
echo ====================================================
echo.

if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" auto_login.py
) else (
    python auto_login.py
)

echo.
pause
