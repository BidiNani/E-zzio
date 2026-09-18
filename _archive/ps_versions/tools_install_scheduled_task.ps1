$TaskName = "Ezzio_Discord_Stack"
$Script = "G:/AI/E-zzio/tools/run_discord_stack.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
        -Settings $Settings -Description "E-ZZIO Discord stack (backend :8001 + bot)" | Out-Null
    "TASK-REGISTERED: $TaskName"
} catch {
    "TASK-FAILED: $($_.Exception.Message)"
}
