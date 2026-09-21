Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
currentPath = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentPath
WshShell.Run "pythonw main.py", 0, False
