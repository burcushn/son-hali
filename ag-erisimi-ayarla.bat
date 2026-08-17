@echo off
chcp 65001 >nul
title Ag Erisimi Ayarla — Diger PC'lerden Girebilmek Icin
setlocal EnableDelayedExpansion

echo ============================================================
echo   DIGER BILGISAYARLARDAN ERISIM AYARI
echo ============================================================
echo.
echo Bu script:
echo   1) Bu bilgisayarin ag IP adresini bulur
echo   2) frontend\.env ve backend\.env dosyalarini bu IP ile guncceller
echo   3) Windows Guvenlik Duvari'nda 3000 ve 8001 portlarini acar
echo.
echo NOT: Yonetici olarak calistirmalisiniz (sag tik - Yonetici olarak calistir)
echo.
pause

REM --- IP adresini bul ---
set IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
  set "CAND=%%a"
  set "CAND=!CAND: =!"
  if not "!CAND:~0,7!"=="127.0.0" if "!IP!"=="" set "IP=!CAND!"
)

echo Bulunan IP adresi: !IP!
echo.
set /p NEWIP=Bu IP dogru mu? Enter'a basin veya dogru IP'yi yazin: 
if not "%NEWIP%"=="" set IP=%NEWIP%
if "!IP!"=="" (
  echo IP adresi bulunamadi. "ipconfig" yazip IPv4 adresini elle girin.
  pause
  exit /b 1
)

REM --- .env dosyalarini guncelle ---
powershell -NoProfile -Command ^
  "$ip='!IP!';" ^
  "$f='%~dp0frontend\.env'; $b='%~dp0backend\.env';" ^
  "if(Test-Path $f){(Get-Content $f) -replace '^REACT_APP_BACKEND_URL=.*', ('REACT_APP_BACKEND_URL=http://'+$ip+':8001') | Set-Content -Encoding UTF8 $f; Write-Host 'frontend\.env guncellendi'} else {Write-Host 'frontend\.env bulunamadi!'};" ^
  "if(Test-Path $b){(Get-Content $b) -replace '^CORS_ORIGINS=.*', ('CORS_ORIGINS=\"http://'+$ip+':3000,http://localhost:3000\"') | Set-Content -Encoding UTF8 $b; Write-Host 'backend\.env guncellendi'} else {Write-Host 'backend\.env bulunamadi!'}"

REM --- Guvenlik duvari kurallari ---
netsh advfirewall firewall delete rule name="Ihracat Frontend 3000" >nul 2>&1
netsh advfirewall firewall delete rule name="Ihracat Backend 8001" >nul 2>&1
netsh advfirewall firewall add rule name="Ihracat Frontend 3000" dir=in action=allow protocol=TCP localport=3000 >nul
netsh advfirewall firewall add rule name="Ihracat Backend 8001" dir=in action=allow protocol=TCP localport=8001 >nul
echo Guvenlik duvari: 3000 ve 8001 portlari acildi.

echo.
echo ============================================================
echo   TAMAM!
echo ============================================================
echo   1) baslat-backend.bat ve baslat-frontend.bat pencerelerini
echo      KAPATIP yeniden acin (ayarlar yeni haliyle yuklensin).
echo   2) Diger bilgisayarlarda tarayiciya sunu yazin:
echo.
echo         http://!IP!:3000
echo.
echo   3) Kalici olsun isterseniz o bilgisayarlarda masaustu-kisayol.bat
echo      calistirip yukaridaki adresi girin (logolu kisayol olusur).
echo ============================================================
echo.
pause
