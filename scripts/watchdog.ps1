# ============================================================================
# E-ZZIO Watchdog — relance uvicorn si /health KO
# Requiert PowerShell 7+ (pwsh). Lance avec : pwsh -File watchdog.ps1
# ============================================================================
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Error "Ce script nécessite PowerShell 7+. Utilise 'pwsh -File', pas 'powershell -File'."
    exit 1
}

$ErrorActionPreference = "Continue"
$BackendPath = "G:\AI\E-zzio"
$PythonExe   = "$BackendPath\.venv\Scripts\python.exe"
$HealthUrl   = "http://127.0.0.1:8001/health"
$CheckEvery  = 15
$MaxFails    = 3

Set-Location $BackendPath
$failCount    = 0
$restartCount = 0

Write-Host "Watchdog démarré — Ctrl+C pour arrêter"
Write-Host "Backend : $BackendPath"
Write-Host "Vérif toutes les ${CheckEvery}s, redémarrage après $MaxFails échecs"

while ($true) {
    try {
        Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5 -ErrorAction Stop | Out-Null
        if ($failCount -gt 0) {
            Write-Host "[OK] Backend de retour (échecs précédents : $failCount)"
        }
        $failCount = 0
    } catch {
        $failCount++
        Write-Host "[WARN] Échec $failCount/$MaxFails"

        if ($failCount -ge $MaxFails) {
            $restartCount++
            Write-Host "[FAIL] Backend KO — redémarrage #$restartCount"

            Get-Process python* -ErrorAction SilentlyContinue |
                Where-Object { $_.Path -like "$BackendPath*" } |
                Stop-Process -Force -ErrorAction SilentlyContinue

            Start-Sleep -Seconds 2

            $log = "$BackendPath\runtime\backend_wd_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
            Start-Process -FilePath $PythonExe `
                -ArgumentList "-m","uvicorn","web_server:app","--host","127.0.0.1","--port","8001","--log-level","warning" `
                -WorkingDirectory $BackendPath `
                -RedirectStandardOutput $log `
                -RedirectStandardError "$log.err" `
                -WindowStyle Hidden | Out-Null

            $ready = $false
            for ($i = 1; $i -le 15; $i++) {
                Start-Sleep -Seconds 2
                try {
                    Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3 -ErrorAction Stop | Out-Null
                    $ready = $true; break
                } catch { }
            }

            if ($ready) {
                Write-Host "[OK] Backend redémarré (restart #$restartCount)"
                $failCount = 0
            } else {
                Write-Host "[FAIL] Backend n'a pas redémarré — nouvelle tentative dans ${CheckEvery}s"
            }
        }
    }
    Start-Sleep -Seconds $CheckEvery
}