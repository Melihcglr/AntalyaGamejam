@echo off
REM Windows acilista Jarvis watchdog (Startup / Task Scheduler)
cd /d "%~dp0"
start "JarvisWatchdog" /MIN cmd /c jarvis_watchdog.bat
