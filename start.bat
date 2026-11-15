@echo off
setlocal
cd /d "%~dp0"
title Spaceline

echo.
echo  SPACELINE WORKSPACE
 echo -------------------------------
echo  Starting your private workspace...
echo.

set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python was not found. Install Python 3.10 or newer, then run this file again.
        echo https://www.python.org/downloads/windows/
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating the local Python environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto failed
)

call ".venv\Scripts\activate.bat"

if not exist ".venv\.spaceline_ready_0.9.6" (
    echo [2/3] Installing Spaceline dependencies. Internet is needed for this first setup...
    python -m pip install --upgrade pip
    if errorlevel 1 goto failed
    python -m pip install -r requirements.txt
    if errorlevel 1 goto failed
    echo ready>".venv\.spaceline_ready_0.9.6"
) else (
    echo [2/3] Dependencies already installed.
)

echo [3/4] Checking the embedded Chromium browser engine...
python -c "import os; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); path=p.chromium.executable_path; p.stop(); raise SystemExit(0 if os.path.isfile(path) else 1)" >nul 2>nul
if errorlevel 1 (
    echo Chromium is missing. Spaceline will download the Playwright browser engine now.
    echo This is a one-time download and may take several minutes.
    python -m playwright install chromium
    if errorlevel 1 (
        echo.
        echo WARNING: Chromium could not be installed. Spaceline can still start, but its Browser panel will remain unavailable.
        echo Check your internet connection, then run: .venv\Scripts\python.exe -m playwright install chromium
        echo.
    ) else (
        echo Chromium installed successfully.
    )
) else (
    echo Chromium is already installed.
)

echo [4/4] Launching Spaceline in your browser...
echo Keep this window open while using Spaceline. Press Ctrl+C to stop it.
echo.
python run.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo Spaceline could not start. Read the error above. If this is the first run, check your internet connection.
pause
exit /b 1
