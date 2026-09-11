$Vbs = "G:/AI/E-zzio/tools/launch_background.vbs"
$Dest = Join-Path ([Environment]::GetFolderPath("Startup")) "Ezzio_Stack.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$Sc = $Wsh.CreateShortcut($Dest)
$Sc.TargetPath = "wscript.exe"
$Sc.Arguments = "`"$Vbs`""
$Sc.WindowStyle = 0
$Sc.Description = "E-ZZIO Discord stack (silencieux)"
$Sc.Save()
"OK: $Dest"
