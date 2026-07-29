$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO SVELTE UI STATUS ===" -ForegroundColor Cyan

$backend = $false
$frontend = $false

try {
    $api = Invoke-RestMethod "http://127.0.0.1:8000/status" -Method GET -TimeoutSec 5
    $backend = $true
}
catch {}

try {
    $ui = Invoke-WebRequest "http://127.0.0.1:5173" -Method GET -TimeoutSec 5
    $frontend = ($ui.StatusCode -eq 200)
}
catch {}

[pscustomobject]@{
    backend_online = $backend
    frontend_online = $frontend
    backend_url = "http://127.0.0.1:8000/status"
    frontend_url = "http://127.0.0.1:5173"
}
