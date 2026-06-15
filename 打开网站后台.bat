@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Opening local private website dashboard...
echo The generated dashboard is in the local folder and is not published to GitHub Pages.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\open_admin_dashboard.ps1"

if errorlevel 1 (
  echo.
  echo Failed to open the local website dashboard.
  pause
)
