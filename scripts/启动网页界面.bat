@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".\.venv\Scripts\python.exe" (
  echo [X] venv not found. Run 一键安装.bat first.
  pause & exit /b 1
)
call ".\.venv\Scripts\activate.bat"
set PYTHONPATH=src
echo Starting Web UI at http://127.0.0.1:7860  (Ctrl+C to stop)
python -m uvicorn agent_fastapi:app --host 127.0.0.1 --port 7860
pause
