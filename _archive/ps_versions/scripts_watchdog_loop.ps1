$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [int]$EverySeconds = 60
)

Write-Host "E-ZZIO watchdog loop lancé. Ctrl+C pour arrêter." -ForegroundColor Cyan

while ($true) {
    try {
        $res = Invoke-RestMethod "http://127.0.0.1:8001/supervisor/watchdog" -Method GET -TimeoutSec 90
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

        Write-Host ""
        Write-Host "[$stamp] Watchdog OK=$($res.ok)" -ForegroundColor Green
        $res.actions | ForEach-Object { Write-Host "- $_" }
    }
    catch {
        Write-Warning "Watchdog error : $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $EverySeconds
}

