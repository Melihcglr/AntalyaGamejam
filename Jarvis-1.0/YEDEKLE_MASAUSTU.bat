@echo off
chcp 65001 >nul
title Jarvis → Masaustu (yerel calisma alani)
setlocal EnableExtensions

set "SRC=%~dp0"
REM Sonundaki \ kaldir
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"
set "DEST=%USERPROFILE%\Desktop\Jarvis"

echo ========================================
echo   BURADAKI HER SEY → Masaustu\Jarvis
echo   Yerel klasor + yerel git (bulutsuz)
echo ========================================
echo Kaynak: %SRC%
echo Hedef : %DEST%
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [HATA] Python yok: https://www.python.org/downloads/
  echo Kurarken "Add python.exe to PATH" isaretle.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
  echo [UYARI] Git yok — klasor kopyalanacak, yerel repo acilamayacak.
  echo Istege bagli: https://git-scm.com/download/win
  set "HAS_GIT=0"
) else (
  set "HAS_GIT=1"
)

if not exist "%DEST%" (
  echo [1/4] Masaustu\Jarvis olusturuluyor...
  mkdir "%DEST%"
) else (
  echo [1/4] Masaustu\Jarvis zaten var — uzerine yazilacak...
)

echo [2/4] Tum dosyalar tasiniyor...
robocopy "%SRC%" "%DEST%" /E /XD .venv __pycache__ .git .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /nc /ns /np
if errorlevel 8 (
  echo [HATA] Kopyalama basarisiz
  pause
  exit /b 1
)

REM Eski "Jarvis 1.0" varsa birlestir
if exist "%USERPROFILE%\Desktop\Jarvis 1.0\main.py" (
  echo [+] Eski "Jarvis 1.0" icerigi de birlestiriliyor...
  robocopy "%USERPROFILE%\Desktop\Jarvis 1.0" "%DEST%" /E /XD .venv __pycache__ .git .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /nc /ns /np
)

cd /d "%DEST%"

if "%HAS_GIT%"=="1" (
  if not exist ".git" (
    echo [3/4] Yerel git deposu aciliyor ^(uzak YOK^)...
    git init
    git branch -m main
    git add .
    git -c user.email="jarvis@local" -c user.name="Jarvis" commit -m "Jarvis — masaustu yerel calisma alani"
  ) else (
    echo [3/4] Yerel repo var — yedek commit...
    git add .
    git -c user.email="jarvis@local" -c user.name="Jarvis" commit -m "Jarvis — guncelleme %DATE% %TIME%" 2>nul
  )
) else (
  echo [3/4] Git yok — sadece klasor tamam.
)

echo.
echo [OK] Yerel calisma alani: %DEST%
echo [4/4] Kurulum / baslatma...
echo Panel: http://127.0.0.1:8787
echo.
call "%DEST%\BASLAT.bat"
endlocal
