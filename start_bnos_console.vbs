' BNOS Console Launcher — 无窗口静默启动
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
basePath = fso.GetParentFolderName(WScript.ScriptFullName)

' 优先 pythonw（无控制台），其次 python
python = WshShell.ExpandEnvironmentStrings("%PYTHON%")
If python = "%PYTHON%" Then python = "pythonw"

On Error Resume Next
WshShell.Run """" & python & """ """ & basePath & "\launcher.py""", 0, False
If Err.Number <> 0 Then
    WshShell.Run "python """ & basePath & "\launcher.py""", 0, False
End If
