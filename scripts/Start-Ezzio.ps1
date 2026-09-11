Set-Location "G:\AI\E-zzio"
$ErrorActionPreference = "Stop"

$root = "G:\AI\E-zzio"
$python = "G:\Python312\python.exe"
$logDir = Join-Path $root "state\audit\current\runtime_start"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Ne jamais démarrer une seconde instance.
$listeners = @(Get-NetTCPConnection `
    -LocalPort 8001 `
    -State Listen `
    -ErrorAction SilentlyContinue)

if ($listeners.Count -eq 1) {

    $pidExisting = [int]$listeners[0].OwningProcess

    Write-Host ""
    Write-Host "E-ZZIO est déjà actif." -ForegroundColor Green
    Write-Host "PID  = $pidExisting"
    Write-Host "URL  = http://127.0.0.1:8001"

    exit 0
}

if ($listeners.Count -gt 1) {
    throw "État incohérent : plusieurs listeners détectés sur 8001."
}

$stdout = Join-Path $logDir "ezzio_stdout.log"
$stderr = Join-Path $logDir "ezzio_stderr.log"

Remove-Item $stdout,$stderr -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Démarrage E-ZzIO..." -ForegroundColor Cyan

$proc = Start-Process `
    -FilePath $python `
    -ArgumentList "-m","uvicorn","web_server:app","--host","127.0.0.1","--port","8001","--log-level","info" `
    -WorkingDirectory $root `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

$ready = $false

for ($i = 1; $i -le 30; $i++) {

    Start-Sleep -Seconds 1

    $listeners = @(Get-NetTCPConnection `
        -LocalPort 8001 `
        -State Listen `
        -ErrorAction SilentlyContinue)

    if ($listeners.Count -eq 1) {
        $ready = $true
        break
    }
}

if (-not $ready) {

    Write-Host ""
    Write-Host "E-ZzIO n'a pas démarré." -ForegroundColor Red

    if (Test-Path $stderr) {
        Get-Content $stderr -Tail 100
    }

    exit 1
}

$ownerPid = [int]$listeners[0].OwningProcess

$health = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8001/health" `
    -Method Get `
    -TimeoutSec 15

if ($health.ok -ne $true) {
    throw "E-ZzIO démarre mais /health n'est pas OK."
}

Write-Host ""
Write-Host "E-ZZIO ONLINE" -ForegroundColor Green
Write-Host "PID      = $ownerPid"
Write-Host "URL      = http://127.0.0.1:8001"
Write-Host "LOG      = $logDir"
