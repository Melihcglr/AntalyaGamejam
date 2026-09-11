@echo off
chcp 65001 >nul
title Jarvis 1.0 - Kurulum / Baslat
cd /d "%~dp0"

echo ========================================
echo   Jarvis 1.0
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [HATA] Python yok. https://www.python.org/downloads/
  echo Kurarken "Add python.exe to PATH" isaretle.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Sanal ortam...
  python -m venv .venv
  if errorlevel 1 (
    echo [HATA] venv basarisiz
    pause
    exit /b 1
  )
  call .venv\Scripts\activate.bat
  echo [2/3] Paketler (biraz surer)...
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [UYARI] Paket hatasi. PyAudio icin:
    echo   pip install pipwin ^&^& pipwin install pyaudio
    pause
  )
) else (
  call .venv\Scripts\activate.bat
  echo [OK] Ortam hazir.
)

if not exist "config.json" (
  copy config.example.json config.json >nul
  echo [OK] config.json olusturuldu — pc_mac / esp / api_token duzenle.
)

echo.
echo [3/3] Jarvis 1.0 basliyor...
echo Panel: http://127.0.0.1:8787
echo.
start "" http://127.0.0.1:8787
python main.py --host 0.0.0.0 --port 8787
pause
