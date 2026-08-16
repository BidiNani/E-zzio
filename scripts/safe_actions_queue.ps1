param(
    [int]$Limit = 30
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/safe-actions/queue?limit=$Limit" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO SAFE ACTIONS QUEUE ===" -ForegroundColor Cyan
Write-Host "Items : $($res.count)"
Write-Host ""

$res.items | ForEach-Object {
    [pscustomobject]@{
        created_at = $_.created_at
        effective_status = $_.effective_status
        executed = $_.executed
        cancelled = $_.cancelled
        id = $_.id
        action = $_.action
        requires_confirmation = $_.requires_confirmation
        run_ok = $_.run_ok
        cancel_reason = $_.cancel_reason
        reason = $_.reason
    }
}

