@echo off
chcp 65001 >nul
title Ihracat Bedeli - EKRAN (bu pencereyi kapatmayin)
cd /d "%~dp0frontend"

if not exist node_modules (
  echo [HATA] Once kurulum.bat dosyasini calistirin.
  pause
  exit /b 1
)

echo Uygulama baslatiliyor... http://localhost:3000
echo Tarayici kendiliginden acilir. Kapatmak icin bu pencereyi kapatin.
call yarn start
pause
