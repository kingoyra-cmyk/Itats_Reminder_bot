@echo off
title Tes Koneksi Telegram Bot
cd /d "%~dp0"

echo Menguji pengiriman notifikasi ke Telegram...
echo.

if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" bot.py --test
) else (
    python bot.py --test
)

echo.
pause
