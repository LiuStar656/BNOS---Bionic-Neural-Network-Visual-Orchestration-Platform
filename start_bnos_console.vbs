' BNOS Console Launcher — 无窗口静默启动
Dim shell, fso, basePath, python
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
basePath = fso.GetParentFolderName(WScript.ScriptFullName)

' 尝试 pythonw，失败则用 python
python = "pythonw"
On Error Resume Next
shell.Run """" & python & """ """ & basePath & "\launcher.py""", 0, False
If Err.Number <> 0 Then
    Err.Clear
    shell.Run "python """ & basePath & "\launcher.py""", 0, False
End If
On Error Goto 0
