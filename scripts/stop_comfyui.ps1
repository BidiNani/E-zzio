$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ============================================================
# E-ZZIO - STOP COMFYUI
# Ferme proprement le propriétaire du port 8188.
# ============================================================

$Port = 8188

$connections = @(
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" }
)

if ($connections.Count -eq 0) {
    Write-Host "ComfyUI n'écoute pas sur le port $Port." -ForegroundColor Yellow
    return
}

foreach ($connection in $connections) {
    $ownerProcessId = [int]$connection.OwningProcess

    try {
        $process = Get-Process -Id $ownerProcessId -ErrorAction Stop
        Write-Host "[STOP] ComfyUI/port $Port : PID=$ownerProcessId $($process.ProcessName)" -ForegroundColor Yellow
        Stop-Process -Id $ownerProcessId -Force
    }
    catch {
        Write-Warning "Impossible d'arrêter PID=$ownerProcessId : $($_.Exception.Message)"
    }
}

Start-Sleep -Seconds 2

$remaining = @(
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" }
)

if ($remaining.Count -eq 0) {
    Write-Host "✅ ComfyUI arrêté." -ForegroundColor Green
}
else {
    Write-Warning "Le port $Port semble encore occupé."
}
