@echo off
chcp 65001 >nul
title Jarvis 1.0 - Repo → Masaustu yedek
setlocal

set "ROOT=%~dp0"
set "SRC=%ROOT%Jarvis-1.0"
set "DEST=%USERPROFILE%\Desktop\Jarvis 1.0"

echo ========================================
echo   AntalyaGamejam → Desktop\Jarvis 1.0
echo   Yerel klasor + yerel git (bulutsuz)
echo ========================================
echo.

if not exist "%SRC%\main.py" (
  echo [HATA] Jarvis-1.0 paketi bulunamadi: %SRC%
  pause
  exit /b 1
)

call "%SRC%\YEDEKLE_MASAUSTU.bat"
endlocal
