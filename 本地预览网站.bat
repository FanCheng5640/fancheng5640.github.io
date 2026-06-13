@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Local preview URL: http://localhost:4000
echo.
echo If the browser does not open automatically, copy the URL above.
echo Close this window to stop the local preview server.
echo.

start "" "http://localhost:4000"
bundle exec jekyll serve --host 127.0.0.1 --port 4000

echo.
echo Local preview server has stopped.
pause
