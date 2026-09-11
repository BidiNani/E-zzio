# Script PowerShell pour demarrer E-ZzIO en arriere-plan (Daemon)
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$HostIP = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $RootDir "data\ezzio_daemon.pid"
$LogFile = Join-Path $RootDir "data\ezzio_daemon.log"

Set-Location $RootDir

$targetUrl = "http://" + $HostIP + ":" + $Port

# Verifier si deja en cours d execution
if (Test-Path $PidFile) {
    $existingPid = Get-Content $PidFile
    if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
        Write-Host "[WARNING] E-ZzIO tourne deja en tache de fond (PID: $existingPid) sur $targetUrl" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "[INFO] Lancement du Daemon E-ZzIO sur $targetUrl ..." -ForegroundColor Cyan

$process = Start-Process -FilePath "G:\Python312\python.exe" `
    -ArgumentList "main.py api --host $HostIP --port $Port" `
    -WorkingDirectory $RootDir `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError (Join-Path $RootDir "data\ezzio_daemon_err.log") `
    -WindowStyle Hidden `
    -PassThru

$process.Id | Set-Content -Path $PidFile -Force

Start-Sleep -Seconds 2

if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
    Write-Host "[OK] Daemon E-ZzIO demarre avec succes !" -ForegroundColor Green
    Write-Host "  * PID      : $($process.Id)" -ForegroundColor Gray
    Write-Host "  * Web UI   : $targetUrl" -ForegroundColor Cyan
    Write-Host "  * API Docs : $targetUrl/docs" -ForegroundColor Cyan
    Write-Host "  * Logs     : $LogFile" -ForegroundColor Gray
} else {
    Write-Host "[ERROR] Echec du demarrage du Daemon E-ZzIO. Consultez $LogFile" -ForegroundColor Red
}
