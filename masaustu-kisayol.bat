@echo off
chcp 65001 >nul
title Masaustu Kisayolu Olustur — Ihracat Bedeli Sistemi
setlocal

echo ============================================================
echo   IHRACAT BEDELI SISTEMI - MASAUSTU KISAYOLU
echo ============================================================
echo.
echo Uygulamanin adresini yazin.
echo   Ornek (kendi PC'nizde ):  http://localhost:3000
echo   Ornek (sirket sunucusu):  http://192.168.1.50
echo   Ornek (Emergent yayin  ):  https://....emergent.host
echo.
set /p APPURL=Adres: 
if "%APPURL%"=="" set APPURL=http://localhost:3000

set ICON=%~dp0frontend\public\favicon.ico
set DESK=%USERPROFILE%\Desktop
set NAME=Ihracat Bedeli Sistemi

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%DESK%\%NAME%.lnk');" ^
  "$chrome=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe' -EA SilentlyContinue).'(default)';" ^
  "$edge=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe' -EA SilentlyContinue).'(default)';" ^
  "$b=if($chrome){$chrome}else{$edge};" ^
  "if($b){$s.TargetPath=$b;$s.Arguments='--app=%APPURL%'}else{$s.TargetPath='%APPURL%'};" ^
  "if(Test-Path '%ICON%'){$s.IconLocation='%ICON%'};" ^
  "$s.Description='Ihracat Bedeli Kapatma ve Banka Bildirim Sistemi';$s.Save()"

echo.
if exist "%DESK%\%NAME%.lnk" (
  echo TAMAM: Masaustunde "%NAME%" kisayolu olusturuldu.
  echo Cift tiklayarak uygulamayi acabilirsiniz ^(tarayici cubugu olmadan, program gibi^).
) else (
  echo Kisayol olusturulamadi. Kilavuz: MASAUSTU-KISAYOL.md
)
echo.
pause
