$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$url = "http://127.0.0.1:8000/ui"

try {
    $status = Invoke-RestMethod "http://127.0.0.1:8000/status" -Method GET -TimeoutSec 5
    Write-Host "E-ZZIO API OK : $($status.version)" -ForegroundColor Green
}
catch {
    Write-Host "API E-ZZIO non joignable. Lance restart_ezzio_all.ps1." -ForegroundColor Red
    throw
}

Write-Host "Ouverture : $url" -ForegroundColor Cyan
Start-Process $url
