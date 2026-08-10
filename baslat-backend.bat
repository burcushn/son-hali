@echo off
chcp 65001 >nul
title Ihracat Bedeli - BACKEND (bu pencereyi kapatmayin)
cd /d "%~dp0backend"

if not exist .venv (
  echo [HATA] Once kurulum.bat dosyasini calistirin.
  pause
  exit /b 1
)

call .venv\Scripts\activate
echo Backend baslatiliyor... http://localhost:8001
echo Kapatmak icin bu pencereyi kapatin.
python -m uvicorn server:app --host 0.0.0.0 --port 8001
pause
