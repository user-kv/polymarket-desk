' Launch a command completely hidden (no console window to close).
' Usage: wscript.exe run_hidden.vbs <exe> <arg1> <arg2> ...
' Output is redirected by the caller inside the command string; here we
' rebuild the full command line and run it through cmd /c hidden.
Dim sh, args, cmd, i
Set sh = CreateObject("WScript.Shell")
cmd = ""
For i = 0 To WScript.Arguments.Count - 1
    If InStr(WScript.Arguments(i), " ") > 0 Then
        cmd = cmd & """" & WScript.Arguments(i) & """ "
    Else
        cmd = cmd & WScript.Arguments(i) & " "
    End If
Next
' 0 = hidden window, False = don't wait (Task Scheduler tracks wscript, not the child;
' the child owns its own lifetime and cannot be killed by a window close)
sh.Run "cmd /c " & cmd, 0, True
