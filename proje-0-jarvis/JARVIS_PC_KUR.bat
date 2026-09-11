@echo off
chcp 65001 >nul
title Jarvis - Indir ve Kur
setlocal

set "DEST=%USERPROFILE%\Desktop\AntalyaGamejam"
set "REPO=https://github.com/Melihcglr/AntalyaGamejam.git"
set "BRANCH=cursor/windows-jarvis-asistan-bd5e"

echo ========================================
echo   Jarvis - PC'ye indir + kur
echo ========================================
echo Hedef: %DEST%
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [HATA] Git yok. Indir: https://git-scm.com/download/win
  start https://git-scm.com/download/win
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo [HATA] Python yok. Indir: https://www.python.org/downloads/
  echo Kurarken "Add python.exe to PATH" isaretle, sonra tekrar dene.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

if exist "%DEST%\.git" (
  echo [OK] Repo var, guncelleniyor...
  cd /d "%DEST%"
  git fetch origin
  git checkout %BRANCH%
  git pull origin %BRANCH%
) else (
  echo [1/2] Repo klonlaniyor...
  if exist "%DEST%" (
    echo Klasor var ama git degil. Silip yeniden mi? Manuel kontrol et: %DEST%
    pause
    exit /b 1
  )
  git clone -b %BRANCH% %REPO% "%DEST%"
  if errorlevel 1 (
    echo [HATA] git clone basarisiz.
    pause
    exit /b 1
  )
)

cd /d "%DEST%\asistan"
echo [2/2] Kurulum basliyor...
call KUR_WINDOWS.bat
endlocal
