' QQ Forward - One-Click Start
' Double-click to run, auto-elevates to admin

Option Explicit

Dim WshShell, objShell, strPath, fso, alreadyElevated

' Check if already elevated (re-launched with /elevated flag)
alreadyElevated = False
If WScript.Arguments.Count > 0 Then
    If WScript.Arguments(0) = "/elevated" Then alreadyElevated = True
End If

Set WshShell = CreateObject("WScript.Shell")

' Auto-elevate to admin on first run
If Not alreadyElevated Then
    Set objShell = CreateObject("Shell.Application")
    objShell.ShellExecute "wscript.exe", _
        Chr(34) & WScript.ScriptFullName & Chr(34) & " /elevated", "", "runas", 1
    WScript.Quit
End If

' Get script directory
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Check Python
On Error Resume Next
WshShell.Run "python --version", 0, True
If Err.Number <> 0 Then
    MsgBox "Python not found. Please install Python and add to PATH.", vbCritical, "Startup Failed"
    WScript.Quit 1
End If
On Error Goto 0

' Clean up stale shutdown flag from previous run
Dim flagFile : flagFile = strPath & "\.shutdown.flag"
If fso.FileExists(flagFile) Then fso.DeleteFile(flagFile)

' Start tray app — handles all startup internally (splash + LLBot + Flask + UI)
WshShell.Run "pythonw " & Chr(34) & strPath & "\tray.py" & Chr(34), 0, False
