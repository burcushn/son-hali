@echo off
chcp 65001 >nul
title Ihracat Bedeli - YEDEK AL
cd /d "%~dp0"

set DB=ihracat_bedeli
set HEDEF=%~dp0yedek\%date:~-4%-%date:~3,2%-%date:~0,2%
set MDUMP="C:\Program Files\MongoDB\Tools\100\bin\mongodump.exe"

if not exist %MDUMP% (
  echo [HATA] mongodump bulunamadi. MongoDB Database Tools kurulu mu?
  echo Indir: https://www.mongodb.com/try/download/database-tools
  pause
  exit /b 1
)

echo Yedek aliniyor: %HEDEF%
%MDUMP% --db=%DB% --out="%HEDEF%" || (echo [HATA] Yedek alinamadi. & pause & exit /b 1)

echo.
echo Yedek tamam: %HEDEF%
echo Bu klasoru harici disk veya kurumsal bulut alanina kopyalayin.
pause
