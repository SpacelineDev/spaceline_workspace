@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build Spaceline EXE

echo.
echo  SPACELINE WORKSPACE - WINDOWS EXE BUILDER
echo  ======================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer first.
    echo https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

if not exist ".build-venv\Scripts\python.exe" (
    echo [1/4] Creating build environment...
    python -m venv .build-venv
    if errorlevel 1 goto failed
)

call ".build-venv\Scripts\activate.bat"
if errorlevel 1 goto failed

echo [2/4] Installing app and EXE builder dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements-dev.txt "pyinstaller>=6.15"
if errorlevel 1 goto failed

echo [3/4] Running tests...
python -m pytest -q
if errorlevel 1 goto failed

echo [4/4] Building the standalone Windows executable...
python -m PyInstaller --noconfirm --clean Spaceline.spec
if errorlevel 1 goto failed

echo.
echo BUILD COMPLETE
 echo Your executable is:
echo %CD%\dist\Spaceline.exe
echo.
echo Copy the EXE wherever you want. Your projects, notes and settings remain in Documents\Spaceline.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Review the error above; no new executable was confirmed.
pause
exit /b 1
