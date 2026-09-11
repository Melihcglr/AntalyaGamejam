@echo off
chcp 65001 >nul
title Jarvis Windows Kurulum
cd /d "%~dp0"

echo ========================================
echo   Jarvis - Windows kurulum
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [HATA] Python bulunamadi.
  echo 1^) https://www.python.org/downloads/
  echo 2^) Kurarken "Add python.exe to PATH" isaretle
  echo 3^) Bu pencereyi kapatip KUR_WINDOWS.bat'i tekrar calistir
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

python --version
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Sanal ortam olusturuluyor...
  python -m venv .venv
  if errorlevel 1 (
    echo [HATA] venv olusturulamadi.
    pause
    exit /b 1
  )
  call .venv\Scripts\activate.bat
  echo [2/3] Paketler kuruluyor (biraz surer)...
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo [UYARI] Bazi paketler hata vermis olabilir.
    echo PyAudio icin: pip install pipwin ^&^& pipwin install pyaudio
    pause
  )
) else (
  call .venv\Scripts\activate.bat
  echo [OK] Sanal ortam hazir.
)

if not exist "config.json" (
  copy config.example.json config.json >nul
  echo [OK] config.json olusturuldu.
)

echo.
echo [3/3] Jarvis baslatiliyor...
echo Panel: http://127.0.0.1:8787
echo Kapatmak icin bu pencereyi kapat.
echo.
start "" http://127.0.0.1:8787
python main.py --host 0.0.0.0 --port 8787
pause
