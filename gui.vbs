Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' 切换到脚本目录
objShell.CurrentDirectory = strScriptPath

' 构建命令：激活虚拟环境并运行GUI
strCommand = "cmd /c .venv\Scripts\activate.bat && python gui.py"

' 以隐藏窗口方式运行
objShell.Run strCommand, 0, False
