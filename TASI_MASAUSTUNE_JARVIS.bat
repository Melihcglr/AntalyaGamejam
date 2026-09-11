@echo off
chcp 65001 >nul
title Jarvis → Desktop\Jarvis
setlocal
set "SRC=%~dp0Jarvis-1.0"
if not exist "%SRC%\main.py" (
  echo [HATA] Jarvis-1.0 bulunamadi: %SRC%
  pause
  exit /b 1
)
call "%SRC%\YEDEKLE_MASAUSTU.bat"
endlocal
