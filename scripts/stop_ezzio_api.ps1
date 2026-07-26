$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ============================================================
# E-ZZIO - Stop API
# ============================================================

$Port = 8000

Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    ForEach-Object {
        $ownerProcessId = [int]$_.OwningProcess
        try {
            $process = Get-Process -Id $ownerProcessId -ErrorAction Stop
            Write-Host "[STOP] Port $Port : PID=$ownerProcessId $($process.ProcessName)" -ForegroundColor Yellow
            Stop-Process -Id $ownerProcessId -Force
        }
        catch {
            Write-Warning "Impossible d'arrêter PID=$ownerProcessId : $($_.Exception.Message)"
        }
    }

Start-Sleep -Seconds 2
Write-Host "✅ API arrêtée si elle tournait." -ForegroundColor Green
