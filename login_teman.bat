@echo off
title Login Otomatis Akun Teman ITATS
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   🔑 LOGIN OTOMATIS CLASSROOM ITATS UNTUK TEMAN
echo   (Beda Jurusan / Beda Kelas / Beda Semester)
echo ============================================================
echo.

python auto_login_teman.py

echo.
pause
