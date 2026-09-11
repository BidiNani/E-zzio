param(
    [switch]$Lan,
    [switch]$StartComfy
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$TaskName = "E-ZZIO Local Assistant"
$ScriptPath = "G:\AI\E-zzio\scripts\start_ezzio_all.ps1"

$argsList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$ScriptPath`"")

if ($Lan) { $argsList += "-Lan" }
if ($StartComfy) { $argsList += "-StartComfy" }

$Action = New-ScheduledTaskAction `
    -Execute "pwsh.exe" `
    -Argument ($argsList -join " ")

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Démarre E-ZZIO local au login. CPU/RAM only. No ads." `
    -Force | Out-Null

Write-Host "✅ Autostart installé : $TaskName" -ForegroundColor Green
Write-Host "LAN        : $Lan"
Write-Host "StartComfy : $StartComfy"
