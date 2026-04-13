@echo off
setlocal
cd /d %~dp0

rem 检查本地 .venv 是否存在，不存在则创建并安装依赖
if not exist ".venv\Scripts\activate.bat" (
    echo 正在创建虚拟环境...
    python -m venv .venv
    echo 正在安装依赖...
    .venv\Scripts\pip.exe install -r requirements.txt
)

rem 创建临时VBScript来隐藏cmd窗口
set "vbs=%temp%\gui_launcher_%random%.vbs"
(
echo Set objShell = CreateObject^(^"WScript.Shell^"^)
echo objShell.CurrentDirectory = "%cd%"
echo strCommand = "cmd /c .venv\Scripts\activate.bat && python app.py"
echo objShell.Run strCommand, 0, False
) > "%vbs%"

rem 运行VBScript（会隐藏cmd窗口）
cscript //nologo "%vbs%"

rem 删除临时文件
timeout /t 1 /nobreak >nul
del "%vbs%" 2>nul

endlocal
