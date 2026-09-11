# Script PowerShell pour verifier le statut du Daemon E-ZzIO
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$HostIP = "127.0.0.1"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $RootDir "data\ezzio_daemon.pid"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "           STATUT DU DAEMON E-ZZIO                     " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$baseUrl = "http://" + $HostIP + ":" + $Port

# 1. Test direct de l API
$apiOnline = $false
try {
    $resp = Invoke-RestMethod -Uri ($baseUrl + "/api/health") -TimeoutSec 2 -ErrorAction Stop
    $apiOnline = $true
    Write-Host "[OK] API Repondante sur $baseUrl" -ForegroundColor Green
    Write-Host "  * Ollama LLM   : $($resp.ollama_ok)" -ForegroundColor Gray
    Write-Host "  * VectorStore  : $($resp.vectorstore_ok)" -ForegroundColor Gray
    Write-Host "  * Modeles      : $($resp.models_available.Count) disponibles" -ForegroundColor Gray
} catch {
    $apiOnline = $false
}

# 2. Verification PID
if (Test-Path $PidFile) {
    $daemonPid = Get-Content $PidFile
    $proc = Get-Process -Id $daemonPid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "[OK] Processus Actif : PID $daemonPid (CPU: $($proc.CPU)s, RAM: $([math]::Round($proc.WorkingSet64/1MB, 2)) MB)" -ForegroundColor Green
    } else {
        if (-not $apiOnline) {
            Write-Host "[INFO] Le processus PID $daemonPid n est plus actif. Fichier PID purge." -ForegroundColor Gray
            Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    if (-not $apiOnline) {
        Write-Host "[INFO] Le Daemon E-ZzIO est actuellement inactif." -ForegroundColor Gray
    }
}
