@echo off
chcp 65001 >nul
cd /d "%~dp0"

python scripts\collect_site_images.py
if errorlevel 1 (
  echo.
  echo 生成个人图片库失败，请查看上面的错误信息。
  pause
  exit /b %errorlevel%
)

echo.
echo 已生成：%cd%\个人图片库\图片索引.html
start "" "%cd%\个人图片库\图片索引.html"
pause
