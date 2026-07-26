param(
    [int]$Limit = 50
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$status = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/status" -Method GET -TimeoutSec 90
$res = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/queue?limit=$Limit" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO SAFE ACTION LEDGER ===" -ForegroundColor Cyan

[pscustomobject]@{
    queued_count = $status.queued_count
    executed_count = $status.executed_count
    cancelled_count = $status.cancelled_count
    pending_count = $status.pending_count
    pending_confirmation = $status.pending_confirmation_count
    pending_read = $status.pending_read_count
}

Write-Host ""
Write-Host "Détail :" -ForegroundColor Yellow

$res.items | ForEach-Object {
    [pscustomobject]@{
        status = $_.effective_status
        action = $_.action
        id = $_.id
        run_id = $_.run_id
        cancel_id = $_.cancel_id
        run_ok = $_.run_ok
        requires_confirmation = $_.requires_confirmation
    }
}
