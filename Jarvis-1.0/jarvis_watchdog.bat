@echo off
REM Jarvis watchdog — cokerse yeniden baslatir (Startup / Task Scheduler)
cd /d "%~dp0"
title Jarvis Watchdog

if not exist ".venv\Scripts\python.exe" (
  echo [Jarvis] .venv yok, baslat.bat calistiriliyor...
  call baslat.bat
  exit /b
)

:loop
call .venv\Scripts\activate.bat
echo [%date% %time%] Jarvis baslatiliyor...
python main.py --host 0.0.0.0 --port 8787 --tray
echo [%date% %time%] Jarvis cikti (kod %ERRORLEVEL%). 3 sn sonra yeniden...
timeout /t 3 /nobreak >nul
goto loop
