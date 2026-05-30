' QQ Forward - One-Click Start

Option Explicit

Dim WshShell, objShell, strPath, fso, alreadyElevated

alreadyElevated = False
If WScript.Arguments.Count > 0 Then
    If WScript.Arguments(0) = "/elevated" Then alreadyElevated = True
End If

Set WshShell = CreateObject("WScript.Shell")

If Not alreadyElevated Then
    Set objShell = CreateObject("Shell.Application")
    objShell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34) & " /elevated", "", "runas", 1
    WScript.Quit
End If

' 项目根目录（scripts/ 的上一级）
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))

' Check Python
On Error Resume Next
WshShell.Run "python --version", 0, True
If Err.Number <> 0 Then
    MsgBox "Python not found. Please install Python and add to PATH.", vbCritical, "Startup Failed"
    WScript.Quit 1
End If
On Error Goto 0

' Clean up stale shutdown flag
Dim flagFile : flagFile = strPath & "\.shutdown.flag"
If fso.FileExists(flagFile) Then fso.DeleteFile(flagFile)

' Start app
WshShell.Run "pythonw " & Chr(34) & strPath & "\main.py" & Chr(34), 0, False
