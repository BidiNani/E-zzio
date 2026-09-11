$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$backend = $false
$frontend = $false
$frontendPid = $null

try {
    $api = Invoke-RestMethod "http://127.0.0.1:8001/status" -Method GET -TimeoutSec 5
    $backend = $true
} catch {}

try {
    $ui = Invoke-WebRequest "http://127.0.0.1:5173" -Method GET -TimeoutSec 5
    $frontend = ($ui.StatusCode -eq 200)
} catch {}

try {
    $conn = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        Select-Object -First 1

    if ($conn) {
        $frontendPid = $conn.OwningProcess
    }
} catch {}

Write-Host "=== E-ZZIO SVELTE UI STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    backend_online = $backend
    frontend_online = $frontend
    frontend_pid = $frontendPid
    backend_url = "http://127.0.0.1:8001/status"
    frontend_url = "http://127.0.0.1:5173"
}

