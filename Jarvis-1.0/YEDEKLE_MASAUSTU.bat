@echo off
chcp 65001 >nul
title Jarvis 1.0 - Masaustune yedek + yerel repo
setlocal EnableExtensions

set "SRC=%~dp0"
set "DEST=%USERPROFILE%\Desktop\Jarvis 1.0"

echo ========================================
echo   Jarvis 1.0 → Masaustu (yerel, bulutsuz)
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
  echo [UYARI] Git yok — klasor kopyalanacak ama yerel repo acilamayacak.
  echo Istege bagli: https://git-scm.com/download/win
  set "HAS_GIT=0"
) else (
  set "HAS_GIT=1"
)

if exist "%DEST%\main.py" (
  echo [OK] Hedef zaten var. Icerik guncelleniyor...
) else (
  echo [1/4] Masaustu klasoru olusturuluyor...
  mkdir "%DEST%" 2>nul
)

echo [2/4] Dosyalar kopyalaniyor...
robocopy "%SRC%." "%DEST%" /E /XD .venv __pycache__ .git .pytest_cache /XF config.json *.pyc /NFL /NDL /NJH /NJS /nc /ns /np
if errorlevel 8 (
  echo [HATA] Kopyalama basarisiz
  pause
  exit /b 1
)

cd /d "%DEST%"

if "%HAS_GIT%"=="1" (
  if not exist ".git" (
    echo [3/4] Yerel git deposu aciliyor ^(uzak sunucu YOK^)...
    git init
    git add .
    git -c user.email="jarvis@local" -c user.name="Jarvis 1.0" commit -m "Jarvis 1.0 — yerel masaustu yedegi"
    echo [OK] Yerel repo: %DEST%
  ) else (
    echo [3/4] Yerel repo zaten var — yeni commit...
    git add .
    git -c user.email="jarvis@local" -c user.name="Jarvis 1.0" commit -m "Jarvis 1.0 — yedek guncelleme %DATE% %TIME%" 2>nul
  )
) else (
  echo [3/4] Git yok — sadece klasor yedegi tamam.
)

echo.
echo [4/4] Kurulum / baslatma...
echo Panel: http://127.0.0.1:8787
echo.
call "%DEST%\BASLAT.bat"
endlocal
