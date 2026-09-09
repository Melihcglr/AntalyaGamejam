@echo off
REM Windows acilista Jarvis'i baslat (Startup / Task Scheduler)
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call baslat.bat
) else (
  call .venv\Scripts\activate.bat
  start "Jarvis" /MIN python main.py --host 0.0.0.0 --port 8787
)
