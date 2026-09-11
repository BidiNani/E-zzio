param(
    [switch]$IncludeComfy
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Stop-PortOwner {
    param(
        [int]$Port,
        [string]$Name
    )

    $connections = @(
        Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
            Where-Object { $_.State -eq "Listen" }
    )

    if ($connections.Count -eq 0) {
        Write-Host "$Name : aucun process sur port $Port." -ForegroundColor DarkGray
        return
    }

    foreach ($connection in $connections) {
        $ownerProcessId = [int]$connection.OwningProcess

        try {
            $process = Get-Process -Id $ownerProcessId -ErrorAction Stop
            Write-Host "[STOP] $Name port $Port : PID=$ownerProcessId $($process.ProcessName)" -ForegroundColor Yellow
            Stop-Process -Id $ownerProcessId -Force
        }
        catch {
            Write-Warning "Impossible d'arrêter PID=$ownerProcessId : $($_.Exception.Message)"
        }
    }

    Start-Sleep -Seconds 2
}

Stop-PortOwner -Port 8000 -Name "E-ZZIO API"

if ($IncludeComfy) {
    Stop-PortOwner -Port 8188 -Name "ComfyUI"
}
else {
    Write-Host "ComfyUI conservé. Pour l'arrêter aussi : stop_ezzio_all.ps1 -IncludeComfy" -ForegroundColor DarkGray
}

Write-Host "✅ Stop terminé." -ForegroundColor Green
