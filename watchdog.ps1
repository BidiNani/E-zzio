# ============================================================
# E-ZZIO Watchdog — relance uvicorn si /health KO
# Usage : powershell -File watchdog.ps1
# ============================================================
$ErrorActionPreference = "Continue"

function W-Info($t) { Write-Host "$(Get-Date -Format 'HH:mm:ss')  $t" -ForegroundColor DarkGray }
function W-Ok($t)   { Write-Host "$(Get-Date -Format 'HH:mm:ss')  OK   $t" -ForegroundColor Green }
function W-Ko($t)   { Write-Host "$(Get-Date -Format 'HH:mm:ss')  FAIL $t" -ForegroundColor Red }
function W-Warn($t) { Write-Host "$(Get-Date -Format 'HH:mm:ss')  WARN $t" -ForegroundColor Yellow }

$BackendPath = "G:\AI\E-zzio"
$PythonExe   = "$BackendPath\.venv\Scripts\python.exe"
$HealthUrl   = "http://127.0.0.1:8001/health"
$CheckEvery  = 15   # secondes
$MaxFails    = 3    # avant restart

Set-Location $BackendPath

$failCount = 0
$restartCount = 0

W-Info "Watchdog démarré — Ctrl+C pour arrêter"
W-Info "Backend : $BackendPath"
W-Info "Vérif toutes les $CheckEvery s, restart après $MaxFails échecs"

while ($true) {
    try {
        $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5 -ErrorAction Stop
        if ($failCount -gt 0) {
            W-Ok "Backend revenu en ligne (fails précédents : $failCount)"
        }
        $failCount = 0
    } catch {
        $failCount++
        W-Warn "Échec $failCount/$MaxFails — $($_.Exception.Message.Split([Environment]::NewLine)[0])"

        if ($failCount -ge $MaxFails) {
            W-Ko "Backend KO — redémarrage"
            $restartCount++

            # Tuer uvicorn
            Get-Process python* -ErrorAction SilentlyContinue |
                Where-Object { $_.Path -like "$BackendPath*" } |
                Stop-Process -Force -ErrorAction SilentlyContinue

            Start-Sleep -Seconds 2

            $log = "$BackendPath\runtime\backend_$((Get-Date -Format 'yyyyMMdd_HHmmss')).log"
            Start-Process -FilePath $PythonExe `
                -ArgumentList "-m","uvicorn","web_server:app","--host","127.0.0.1","--port","8001","--log-level","info" `
                -WorkingDirectory $BackendPath `
                -RedirectStandardOutput $log `
                -RedirectStandardError "$log.err" `
                -WindowStyle Hidden | Out-Null

            # Attendre UP
            $ready = $false
            for ($i = 1; $i -le 15; $i++) {
                Start-Sleep -Seconds 2
                try {
                    Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3 -ErrorAction Stop | Out-Null
                    $ready = $true; break
                } catch { }
            }

            if ($ready) {
                W-Ok "Backend relancé (restart #$restartCount)"
                $failCount = 0
            } else {
                W-Ko "Backend n'a pas redémarré — nouvelle tentative dans $CheckEvery s"
            }
        }
    }

    Start-Sleep -Seconds $CheckEvery
}