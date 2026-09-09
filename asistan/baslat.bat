@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [Jarvis] Sanal ortam olusturuluyor...
  python -m venv .venv
  if errorlevel 1 (
    echo Python bulunamadi. https://www.python.org/downloads/
    pause
    exit /b 1
  )
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

if not exist "config.json" (
  copy config.example.json config.json >nul
  echo config.json olusturuldu. API anahtarini istersen buraya yaz.
)

echo Kontrol paneli: http://127.0.0.1:8787
python main.py %*
endlocal
