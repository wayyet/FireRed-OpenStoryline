@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在测试大模型 API 连通性，请稍候...
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" test_api.py
) else (
    python test_api.py
)
echo.
echo ============================================================
echo 测试完成。结果已保存到 test_result.txt
echo 按任意键关闭本窗口。
pause >nul
