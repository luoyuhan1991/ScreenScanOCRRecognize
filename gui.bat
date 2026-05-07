@echo off
cd /d %~dp0
if not exist ".venv\Scripts\pythonw.exe" (
    echo [错误] 未找到 .venv\Scripts\pythonw.exe
    echo 请先创建虚拟环境: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" app.py
