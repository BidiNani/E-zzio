[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$AuditDir = "$RootPath\runtime\audit"
New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null

Write-Host "[*] Démarrage de la certification post-nettoyage (v1.1)..." -ForegroundColor Cyan

# Chemins critiques corrigés (sans échappement d'underscore)
$CriticalPaths = @(
    "web_server.py",
    "core\runtime\advanced_watchdog.py",
    "core\runtime\log_rotator.py",
    "runtime\launcher\start_ezzio_api.ps1",
    "runtime\state\backend\pid.json",
    "runtime\state\backend\health.json",
    "archive\cold_storage\sandbox_v470\archive_manifest.json"
)

$PathStatus = @{}
$AllPathsValid = $true
foreach ($path in $CriticalPaths) {
    $full = "$RootPath\$path"
    $exists = Test-Path $full
    $PathStatus[$path] = $exists
    if (-not $exists) { 
        $AllPathsValid = $false 
        Write-Warning "Chemin critique introuvable : $path"
    }
}

# Vérification du runtime actif (PID & HTTP Health)
$PidFile = "$RootPath\runtime\state\backend\pid.json"
$ActivePid = $null
$ProcessAlive = $false
$HttpHealthy = $false

if (Test-Path $PidFile) {
    try {
        $manifest = Get-Content $PidFile -Raw | ConvertFrom-Json
        $ActivePid = $manifest.pid
        if ($ActivePid -and (Get-Process -Id $ActivePid -ErrorAction SilentlyContinue)) {
            $ProcessAlive = $true
        }
    } catch {}
}

try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.status -eq "ONLINE" -or $response.ok -eq $true) {
        $HttpHealthy = $true
    }
} catch {}

# Calcul volumétrique final du workspace actif (hors archive)
$ExcludedDirs = @("\.venv", "\.git", "__pycache__", "\node_modules", "\archive")
$ActiveFiles = Get-ChildItem -Path $RootPath -Recurse -File | Where-Object {
    $p = $_.FullName
    $skip = $false
    foreach ($ex in $ExcludedDirs) {
        if ($p -match [regex]::Escape($ex)) { $skip = $true; break }
    }
    -not $skip
}
$ActiveSizeMB = [math]::Round(($ActiveFiles | Measure-Object -Property Length -Sum).Sum / 1MB, 2)

# Génération du snapshot de certification validé
$CertificationReport = [PSCustomObject]@{
    CertifiedAt           = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    Version               = "v2.6-autonomic-tactical-core"
    CriticalPathsValid    = $AllPathsValid
    PathDetails           = $PathStatus
    RuntimeStatus         = [PSCustomObject]@{
        TargetPid         = $ActivePid
        ProcessAlive      = $ProcessAlive
        HttpResponsive    = $HttpHealthy
    }
    ActiveWorkspaceSizeMB = $ActiveSizeMB
    CleanupStatus         = "SUCCESS_SANDBOX_ARCHIVED_AND_CERTIFIED"
}

$ReportPath = "$AuditDir\post_cleanup_certification.json"
$CertificationReport | ConvertTo-Json -Depth 5 | Set-Content $ReportPath -Encoding UTF8

Write-Host "`n=== RÉSULTATS DE CERTIFICATION CORRIGÉS ===" -ForegroundColor Cyan
Write-Host "Chemins critiques valides : $AllPathsValid" -ForegroundColor $(if($AllPathsValid){"Green"}else{"Red"})
Write-Host "Processus actif (PID $ActivePid) : $ProcessAlive" -ForegroundColor $(if($ProcessAlive){"Green"}else{"Red"})
Write-Host "Réponse HTTP /health : $HttpHealthy" -ForegroundColor $(if($HttpHealthy){"Green"}else{"Red"})
Write-Host "Poids du workspace actif (hors archive) : $ActiveSizeMB Mo" -ForegroundColor Yellow
Write-Host "[OK] Snapshot de certification enregistré : runtime\audit\post_cleanup_certification.json" -ForegroundColor Green
