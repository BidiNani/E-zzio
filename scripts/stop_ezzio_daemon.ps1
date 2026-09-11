# Script PowerShell pour arreter le Daemon E-ZzIO
[CmdletBinding()]
param()

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $RootDir "data\ezzio_daemon.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "[INFO] Aucun fichier PID trouve. Recherche de processus residuels..." -ForegroundColor Yellow
    Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*ezzio*" } | Stop-Process -Force
    Write-Host "[OK] Processus arretes." -ForegroundColor Green
    exit 0
}

$daemonPid = Get-Content $PidFile
$process = Get-Process -Id $daemonPid -ErrorAction SilentlyContinue

if ($process) {
    Write-Host "[INFO] Arret du Daemon E-ZzIO (PID: $daemonPid)..." -ForegroundColor Yellow
    Stop-Process -Id $daemonPid -Force
    Remove-Item -Path $PidFile -Force
    Write-Host "[OK] Daemon E-ZzIO arrete avec succes." -ForegroundColor Green
} else {
    Write-Host "[INFO] Le processus PID $daemonPid n est plus actif." -ForegroundColor Gray
    Remove-Item -Path $PidFile -Force
}
