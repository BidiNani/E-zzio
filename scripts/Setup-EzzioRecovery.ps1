# ==============================================================================
# E-ZZIO — Initialisation du Registre Anti-Flapping & Couplage Watchdog
# File: G:\AI\E-zzio\scripts\Setup-EzzioRecovery.ps1
# ==============================================================================
$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$StateDir = "$RootPath\runtime\state"
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
$RecoveryStateFile = "$StateDir\recovery_state.json"

if (-not (Test-Path $RecoveryStateFile)) {
    $InitialRecoveryState = @{
        service = "ezzio-api"
        failure_window = @{
            count = 0
            first_failure = $null
            last_failure = $null
        }
        policy = @{
            max_failures = 3
            cooldown_seconds = 300
            escalation_triggered = $false
        }
    }
    $InitialRecoveryState | ConvertTo-Json -Depth 5 | Set-Content $RecoveryStateFile -Encoding UTF8
    Write-Host "[OK] Registre recovery_state.json initialisé." -ForegroundColor Green
} else {
    Write-Host "[*] Registre recovery_state.json déjà existant." -ForegroundColor Yellow
}

Write-Host "`n[*] Exécution du diagnostic multi-signaux..." -ForegroundColor Cyan
& "$RootPath\.venv\Scripts\python.exe" "$RootPath\core\runtime\advanced_watchdog.py"

Write-Host "`n=== ÉTAT COURANT DES MANIFESTES ===" -ForegroundColor Cyan
if (Test-Path "$StateDir\backend\health.json") {
    Get-Content "$StateDir\backend\health.json"
}
Get-Content $RecoveryStateFile
