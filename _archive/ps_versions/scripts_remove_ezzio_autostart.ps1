$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$TaskName = "E-ZZIO Local Assistant"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✅ Autostart supprimé : $TaskName" -ForegroundColor Green
}
else {
    Write-Host "Aucune tâche autostart E-ZZIO trouvée." -ForegroundColor Yellow
}
