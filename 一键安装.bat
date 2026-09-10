@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   OpenStoryline one-click installer
echo   building venv + downloading models + installing deps
echo   (you only provide the API key later)
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_all.ps1"
echo.
echo Done. You can close this window.
pause
