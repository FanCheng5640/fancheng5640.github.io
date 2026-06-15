Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = fso.BuildPath(projectDir, "scripts\stop_local_preview.ps1")

shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & scriptPath & Chr(34), 0, False
