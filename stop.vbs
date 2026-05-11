' QQ Message Forwarding - One-Click Stop
' Double-click to run, auto-elevates to admin

Option Explicit

Dim WshShell, objShell, strPath, flagFile, fso, alreadyElevated
Dim waited

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
flagFile = strPath & "\.shutdown.flag"

' Create shutdown flag — tray.py monitor will detect it and do graceful shutdown
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(flagFile) Then
    fso.CreateTextFile(flagFile).Close()
End If

' Wait for tray.py to gracefully exit (up to 15 seconds)
waited = 0
Do While waited < 15
    WScript.Sleep 1000
    waited = waited + 1
    ' If flag file was deleted, tray.py handled shutdown cleanly
    If Not fso.FileExists(flagFile) Then Exit Do
Loop

' Force kill any remaining processes
WshShell.Run "taskkill /f /im python.exe >nul 2>&1", 0, True
WshShell.Run "taskkill /f /im pythonw.exe >nul 2>&1", 0, True
WshShell.Run "taskkill /f /im llbot.exe >nul 2>&1", 0, True
WshShell.Run "taskkill /f /im node.exe >nul 2>&1", 0, True
WshShell.Run "taskkill /f /im QQ.exe >nul 2>&1", 0, True
WshShell.Run "taskkill /f /im QQNT.exe >nul 2>&1", 0, True

' Clean up flag file if tray didn't
If fso.FileExists(flagFile) Then fso.DeleteFile(flagFile)

MsgBox "Service stopped!", vbInformation, "QQ Message Forwarding"
