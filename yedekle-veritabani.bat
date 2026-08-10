@echo off
chcp 65001 >nul
title Veritabani Yedegi Aliniyor
setlocal
if "%DB_NAME%"=="" set DB_NAME=ihracat_db
set STAMP=%date:~-4%%date:~3,2%%date:~0,2%-%time:~0,2%%time:~3,2%
set STAMP=%STAMP: =0%
if not exist "%~dp0yedekler" mkdir "%~dp0yedekler"
set OUT=%~dp0yedekler\mongo-yedek-%STAMP%.archive

docker ps --format "{{.Names}}" | findstr /X "ihracat-mongo" >nul
if %errorlevel%==0 (
  echo Docker konteyneri kullaniliyor...
  docker exec ihracat-mongo mongodump --db=%DB_NAME% --archive=/tmp/yedek.archive
  docker cp ihracat-mongo:/tmp/yedek.archive "%OUT%"
  docker exec ihracat-mongo rm -f /tmp/yedek.archive
) else (
  echo Yerel mongodump kullaniliyor...
  mongodump --uri="mongodb://localhost:27017" --db=%DB_NAME% --archive="%OUT%"
)

echo.
echo Yedek olusturuldu: %OUT%
pause
