Set WshShell = CreateObject("WScript.Shell")
Set FileSystem = CreateObject("Scripting.FileSystemObject")

ScriptDir = FileSystem.GetParentFolderName(WScript.ScriptFullName)
PowerShellScript = FileSystem.BuildPath(ScriptDir, "local_google_scholar_auto_sync.ps1")

Command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & PowerShellScript & Chr(34)
WshShell.Run Command, 0, False
