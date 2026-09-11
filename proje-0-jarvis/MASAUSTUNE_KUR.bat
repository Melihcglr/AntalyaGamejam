@echo off
chcp 65001 >nul
title Proje 0 Jarvis - Masaustune kur
setlocal

set "DEST=%USERPROFILE%\Desktop\Proje0-Jarvis"
set "REPO=https://github.com/Melihcglr/AntalyaGamejam.git"
set "BRANCH=cursor/windows-jarvis-asistan-bd5e"

echo ========================================
echo   Proje 0 Jarvis → Masaustu
echo ========================================
echo Hedef: %DEST%
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [HATA] Git yok: https://git-scm.com/download/win
  start https://git-scm.com/download/win
  pause
  exit /b 1
)
where python >nul 2>&1
if errorlevel 1 (
  echo [HATA] Python yok: https://www.python.org/downloads/
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

if exist "%DEST%\.git" (
  echo Repo var, guncelleniyor...
  cd /d "%DEST%"
  git fetch origin
  git checkout %BRANCH%
  git pull origin %BRANCH%
) else if exist "%DEST%" (
  echo [UYARI] %DEST% var ama git degil.
  echo Silip yeniden kurmak icin klasoru sil, tekrar calistir.
  pause
  exit /b 1
) else (
  echo Klonlaniyor...
  git clone -b %BRANCH% %REPO% "%TEMP%\AntalyaGamejam-tmp"
  if errorlevel 1 (
    echo clone basarisiz
    pause
    exit /b 1
  )
  mkdir "%DEST%" 2>nul
  xcopy /E /I /Y "%TEMP%\AntalyaGamejam-tmp\proje-0-jarvis\*" "%DEST%\"
  if errorlevel 1 (
    rem fallback: asistan klasoru
    xcopy /E /I /Y "%TEMP%\AntalyaGamejam-tmp\asistan\*" "%DEST%\"
  )
  rmdir /S /Q "%TEMP%\AntalyaGamejam-tmp"
)

cd /d "%DEST%"
echo Kurulum basliyor...
call BASLAT.bat
endlocal
