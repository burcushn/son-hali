@echo off
chcp 65001 >nul
title Veritabani Geri Yukleme
setlocal
if "%DB_NAME%"=="" set DB_NAME=ihracat_db

echo yedekler klasorundeki dosyalar:
dir /b "%~dp0yedekler\*.archive"
echo.
set /p FILE=Geri yuklenecek dosya adi (ornek: mongo-yedek-20260601-0100.archive):
set ARCHIVE=%~dp0yedekler\%FILE%

if not exist "%ARCHIVE%" (
  echo Dosya bulunamadi: %ARCHIVE%
  pause
  exit /b 1
)

echo DIKKAT: Ayni isimli koleksiyonlar silinip yedekten yuklenecek.
set /p OK=Devam etmek icin e yazip Enter'a basin:
if /I not "%OK%"=="e" exit /b 0

docker ps --format "{{.Names}}" | findstr /X "ihracat-mongo" >nul
if %errorlevel%==0 (
  docker cp "%ARCHIVE%" ihracat-mongo:/tmp/geri.archive
  docker exec ihracat-mongo mongorestore --archive=/tmp/geri.archive --drop
  docker exec ihracat-mongo rm -f /tmp/geri.archive
) else (
  mongorestore --uri="mongodb://localhost:27017" --archive="%ARCHIVE%" --drop
)

echo.
echo Geri yukleme tamamlandi.
pause
