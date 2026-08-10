@echo off
chcp 65001 >nul
title Ihracat Bedeli - Ilk Kurulum
cd /d "%~dp0"

echo ============================================
echo   IHRACAT BEDELI KAPATMA SISTEMI - KURULUM
echo ============================================
echo.

where python >nul 2>&1 || (echo [HATA] Python bulunamadi. python.org'dan "Add to PATH" isaretli kurun. & pause & exit /b 1)
where node   >nul 2>&1 || (echo [HATA] Node.js bulunamadi. nodejs.org'dan kurun. & pause & exit /b 1)
where yarn   >nul 2>&1 || (echo [BILGI] yarn kuruluyor... & npm install -g yarn)

echo [1/2] Backend paketleri kuruluyor...
cd backend
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo [HATA] Backend kurulumu basarisiz. & pause & exit /b 1)
cd ..

echo.
echo [2/2] Frontend paketleri kuruluyor (birkac dakika surebilir)...
cd frontend
call yarn install || (echo [HATA] Frontend kurulumu basarisiz. & pause & exit /b 1)
cd ..

echo.
echo ============================================
echo   KURULUM TAMAMLANDI
echo   Simdi: baslat-backend.bat  ve  baslat-frontend.bat
echo ============================================
pause
