@echo off
setlocal
cd /d "%~dp0"
title Spaceline Quick Setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick_setup.ps1"
if errorlevel 1 (
  echo.
  echo Setup stopped. Read the message above, then press any key.
  pause >nul
)
