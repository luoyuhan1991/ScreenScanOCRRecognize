@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

rem Install dependencies to outer venv if needed
..\.venv\Scripts\pip.exe install -r requirements.txt -q 2>nul

rem Create temp VBScript to hide cmd window
set "vbs=%temp%\gui_launcher_%random%.vbs"
(
echo Set objShell = CreateObject^(^"WScript.Shell^"^)
echo objShell.CurrentDirectory = "%cd%"
echo strCommand = "cmd /c ..\.venv\Scripts\activate.bat && python app.py"
echo objShell.Run strCommand, 0, False
) > "%vbs%"

cscript //nologo "%vbs%"

timeout /t 1 /nobreak >nul
del "%vbs%" 2>nul

endlocal
