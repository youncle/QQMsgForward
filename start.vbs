' QQ Forward - One-Click Start
' Double-click to run, auto-elevates to admin

Option Explicit

Dim WshShell, objShell, strPath, llbotExe, trayScript, fso
Dim llbotPort, maxWait, alreadyElevated

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

' Paths
llbotExe = strPath & "\LLBot-CLI-Win-x64\llbot.exe"
trayScript = strPath & "\tray.py"
llbotPort = 3000
maxWait = 20

' Check LLBot executable
If Not fso.FileExists(llbotExe) Then
    MsgBox "Cannot find LLBot:" & vbCrLf & llbotExe, vbCritical, "Startup Failed"
    WScript.Quit 1
End If

' Clean up stale shutdown flag from previous run
Dim flagFile : flagFile = strPath & "\.shutdown.flag"
If fso.FileExists(flagFile) Then fso.DeleteFile(flagFile)

' Check Python
On Error Resume Next
WshShell.Run "python --version", 0, True
If Err.Number <> 0 Then
    MsgBox "Python not found. Please install Python and add to PATH.", vbCritical, "Startup Failed"
    WScript.Quit 1
End If
On Error Goto 0

' If already running, kill existing processes first
If IsPortOpen(llbotPort) Then
    Dim pid : pid = GetPortPid(llbotPort)
    If pid <> "" Then
        WshShell.Run "taskkill /f /pid " & pid & " >nul 2>&1", 0, True
    End If
    WshShell.Run "taskkill /f /im python.exe >nul 2>&1", 0, True
    WshShell.Run "taskkill /f /im pythonw.exe >nul 2>&1", 0, True
    WshShell.Run "taskkill /f /im llbot.exe >nul 2>&1", 0, True
    ' Wait for port to be released
    Dim waitedKill : waitedKill = 0
    Do While IsPortOpen(llbotPort) And waitedKill < 10
        WScript.Sleep 1000
        waitedKill = waitedKill + 1
    Loop
    If IsPortOpen(llbotPort) Then
        MsgBox "Failed to stop existing service. Port " & llbotPort & " still in use.", vbCritical, "Startup Failed"
        WScript.Quit 1
    End If
End If

' Start LLBot (hidden window)
WshShell.Run Chr(34) & llbotExe & Chr(34), 0, False

' Wait for LLBot port to be ready
Dim waited : waited = 0
Do While waited < maxWait
    WScript.Sleep 1000
    waited = waited + 1
    If IsPortOpen(llbotPort) Then Exit Do
Loop

If Not IsPortOpen(llbotPort) Then
    MsgBox "LLBot startup timed out (waited " & maxWait & " sec)." & vbCrLf & _
        "Please make sure LLBot and QQ are properly configured.", vbCritical, "Startup Failed"
    WScript.Quit 1
End If

' Start tray app (pythonw = no console window)
WshShell.Run "pythonw " & Chr(34) & trayScript & Chr(34), 0, False

WScript.Sleep 2000
MsgBox "Service started!" & vbCrLf & vbCrLf & _
    "Tray icon is now in the notification area." & vbCrLf & _
    "Right-click the icon to manage the service.", vbInformation, "QQ Forward"


' ===== Helper Functions =====

Function IsPortOpen(port)
    On Error Resume Next
    Dim exec, output
    Set exec = WshShell.Exec("netstat -ano")
    output = exec.StdOut.ReadAll()
    IsPortOpen = InStr(output, ":" & port & " ") > 0
    On Error Goto 0
End Function

Function GetPortPid(port)
    On Error Resume Next
    Dim exec, output, lines, line, parts, i
    Set exec = WshShell.Exec("netstat -ano")
    output = exec.StdOut.ReadAll()
    lines = Split(output, vbCrLf)
    For i = 0 To UBound(lines)
        line = Trim(lines(i))
        If InStr(line, ":" & port & " ") > 0 And InStr(line, "LISTENING") > 0 Then
            parts = Split(line, " ")
            GetPortPid = parts(UBound(parts))
            Exit Function
        End If
    Next
    GetPortPid = ""
    On Error Goto 0
End Function
