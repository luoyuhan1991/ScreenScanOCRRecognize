@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

rem 使用上层目录的虚拟环境
set "VENV_PATH=..\.venv\Scripts"

rem 检查虚拟环境是否存在
if not exist "%VENV_PATH%\activate.bat" (
    echo 错误：虚拟环境不存在！
    echo 请先在根目录创建虚拟环境：python -m venv .venv
    pause
    exit /b 1
)

rem 安装依赖（如果需要）
"%VENV_PATH%\pip.exe" install -r requirements.txt -q 2>nul

rem 创建临时VBScript来隐藏cmd窗口
set "vbs=%temp%\start_launcher_%random%.vbs"
(
echo Set objShell = CreateObject^("WScript.Shell"^)
echo objShell.CurrentDirectory = "%cd%"
echo strCommand = "cmd /c ""%VENV_PATH%\activate.bat"" && python app.py"
echo objShell.Run strCommand, 0, False
) > "%vbs%"

rem 运行VBScript（会隐藏cmd窗口）
cscript //nologo "%vbs%"

rem 删除临时文件
timeout /t 1 /nobreak >nul
del "%vbs%" 2>nul

endlocal
