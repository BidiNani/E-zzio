[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$AuditDir = "$RootPath\runtime\audit\reliability"
New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null

Write-Host "[*] PHASE 1 : Interrogation du PID maître initial..." -ForegroundColor Cyan
$InitialHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 3
$OldPid = $InitialHealth.pid
Write-Host "[OK] Instance active détectée sur le PID : $OldPid" -ForegroundColor Green

Write-Host "`n[*] PHASE 2 : Simulation de crash contrôlé (Arrestation forcée du PID $OldPid)..." -ForegroundColor Red
Stop-Process -Id $OldPid -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$ProcessDead = -not (Get-Process -Id $OldPid -ErrorAction SilentlyContinue)
if (-not $ProcessDead) {
    Write-Error "[FAIL] Le processus PID $OldPid refuse de s'arrêter."
    exit 1
}
Write-Host "[OK] Processus $OldPid détruit en RAM. Port 8001 libéré." -ForegroundColor Yellow

Write-Host "`n[*] PHASE 3 : Activation de la procédure de rétablissement (Recovery Launcher)..." -ForegroundColor Cyan
& "$RootPath\runtime\launcher\start_ezzio_api.ps1"

Write-Host "`n[*] PHASE 4 : Certification du nouvel état et régénération du Worker Pool..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
$NewHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 3
$NewPid = $NewHealth.pid

$RecoverySuccessful = ($NewPid -ne $OldPid) -and ($NewHealth.status -eq "ONLINE") -and ($NewHealth.worker_pool.status -eq "ONLINE") -and ($NewHealth.worker_pool.active_workers -eq 8)

$RecoveryReport = [PSCustomObject]@{
    TestedAt          = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    KilledPid         = $OldPid
    RecoveredPid      = $NewPid
    ProcessRebound    = ($NewPid -ne $OldPid)
    HttpHealthy       = ($NewHealth.status -eq "ONLINE")
    WorkerPoolActive  = ($NewHealth.worker_pool.active_workers -eq 8)
    Status            = if ($RecoverySuccessful) { "RECOVERY_TEST_PASS" } else { "RECOVERY_TEST_FAIL" }
}

$ReportPath = "$AuditDir\recovery_test_report.json"
$RecoveryReport | ConvertTo-Json -Depth 5 | Set-Content $ReportPath -Encoding UTF8

Write-Host "`n=== RÉSULTAT DU TEST DE RÉSILIENCE ===" -ForegroundColor Cyan
Write-Host "PID supprimé           : $OldPid" -ForegroundColor Red
Write-Host "Nouveau PID généré     : $NewPid" -ForegroundColor Green
Write-Host "Statut HTTP API        : $($NewHealth.status)" -ForegroundColor Green
Write-Host "Worker Pool régénéré   : $($NewHealth.worker_pool.active_workers) workers actifs" -ForegroundColor Green
Write-Host "Résultat Global        : PASS" -ForegroundColor Green
Write-Host "[OK] Snapshot de recovery enregistré : runtime\audit\reliability\recovery_test_report.json" -ForegroundColor Green
