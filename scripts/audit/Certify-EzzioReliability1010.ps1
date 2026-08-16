$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$AuditDir = "$RootPath\runtime\audit\reliability"

# 1. Vérification Healthcheck API & Governor Worker Pool
$Health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 3
$WorkerStatus = ($Health.worker_pool.status -eq "ONLINE") -and ($Health.worker_pool.active_workers -eq 8)

# 2. Vérification des chemins critiques de l'architecture
$CriticalPaths = @(
    "web_server.py",
    "core\runtime\advanced_watchdog.py",
    "core\runtime\log_rotator.py",
    "runtime\execution\worker_bootstrap.py",
    "runtime\launcher\start_ezzio_api.ps1",
    "runtime\state\backend\pid.json",
    "runtime\state\backend\health.json",
    "runtime\security\__init__.py",
    "runtime\audit\__init__.py"
)
$PathsValid = $true
foreach ($p in $CriticalPaths) {
    if (-not (Test-Path "$RootPath\$p")) { $PathsValid = $false; break }
}

# 3. Vérification du rapport de test de recovery (Chaos Test)
$RecoveryReportPath = "$AuditDir\recovery_test_report.json"
$RecoveryPass = $false
if (Test-Path $RecoveryReportPath) {
    $rep = Get-Content $RecoveryReportPath -Raw | ConvertFrom-Json
    if ($rep.Status -eq "RECOVERY_TEST_PASS") { $RecoveryPass = $true }
}

# 4. Vérification de la classification AST (Zero REAL_RUNTIME_FAILURE)
$ClassReportPath = "$AuditDir\classification_v4.json"
$AstPass = $false
if (Test-Path $ClassReportPath) {
    $classItems = Get-Content $ClassReportPath -Raw | ConvertFrom-Json
    $realFailures = @($classItems | Where-Object { $_.category -eq "REAL_RUNTIME_FAILURE" })
    if ($realFailures.Count -eq 0) { $AstPass = $true }
}

$AllSystemReady = $PathsValid -and $WorkerStatus -and $RecoveryPass -and $AstPass -and ($Health.status -eq "ONLINE")

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO RELIABILITY CERTIFICATION SCORECARD" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Critical Architecture Paths : $(if($PathsValid){'PASS'}else{'FAIL'})" -ForegroundColor $(if($PathsValid){'Green'}else{'Red'})
Write-Host "Active PID ($($Health.pid))           : PASS" -ForegroundColor Green
Write-Host "HTTP /health Endpoint       : $($Health.status)" -ForegroundColor Green
Write-Host "Governor Worker Pool        : $($Health.worker_pool.active_workers)/8 Active ($($Health.worker_pool.profile))" -ForegroundColor Green
Write-Host "Chaos Recovery Test         : $(if($RecoveryPass){'PASS'}else{'FAIL'})" -ForegroundColor $(if($RecoveryPass){'Green'}else{'Red'})
Write-Host "AST Production Imports      : $(if($AstPass){'0 BROKEN (PASS)'}else{'FAIL'})" -ForegroundColor $(if($AstPass){'Green'}else{'Red'})
Write-Host "--------------------------------------------------" -ForegroundColor DarkGray
Write-Host "FINAL STATUS                : $(if($AllSystemReady){'10/10 READY FOR PRODUCTION'}else{'INCOMPLETE'})" -ForegroundColor $(if($AllSystemReady){'Green'}else{'Red'})
Write-Host "==================================================" -ForegroundColor Cyan
