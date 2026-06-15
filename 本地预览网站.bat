@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Local preview URL: http://localhost:4000
echo.
echo Visible debug mode. For normal use without a terminal window, double-click:
echo 本地预览网站.vbs
echo.
echo Auto reload is enabled for page, style, and data edits.
echo If the browser does not open automatically, copy the URL above.
echo Close this window to stop the local preview server.
echo.

start "" "http://localhost:4000"
bundle exec jekyll serve --host 127.0.0.1 --port 4000 --livereload --force_polling

echo.
echo Local preview server has stopped.
pause
