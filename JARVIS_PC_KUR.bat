@echo off
chcp 65001 >nul
title Proje 0 Jarvis - Masaustune kur
setlocal
set "DEST=%USERPROFILE%\Desktop\Proje0-Jarvis"
set "REPO=https://github.com/Melihcglr/AntalyaGamejam.git"
set "BRANCH=cursor/windows-jarvis-asistan-bd5e"
echo Proje 0 Jarvis → %DEST%
where git >nul 2>&1 || (echo Git yok & start https://git-scm.com/download/win & pause & exit /b 1)
where python >nul 2>&1 || (echo Python yok & start https://www.python.org/downloads/ & pause & exit /b 1)
if exist "%DEST%\BASLAT.bat" (
  cd /d "%DEST%"
  git -C "%DEST%" pull 2>nul
  call BASLAT.bat
  exit /b
)
git clone -b %BRANCH% %REPO% "%TEMP%\AntalyaGamejam-tmp"
mkdir "%DEST%" 2>nul
xcopy /E /I /Y "%TEMP%\AntalyaGamejam-tmp\proje-0-jarvis\*" "%DEST%\" >nul
rmdir /S /Q "%TEMP%\AntalyaGamejam-tmp"
cd /d "%DEST%"
call BASLAT.bat
endlocal
