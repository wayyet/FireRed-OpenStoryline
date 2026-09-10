@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".\.venv\Scripts\python.exe" (
  echo [X] venv not found. Run 一键安装.bat first.
  pause & exit /b 1
)
call ".\.venv\Scripts\activate.bat"
set PYTHONPATH=src
echo Starting OpenStoryline MCP server ...
python -m open_storyline.mcp.server
pause
